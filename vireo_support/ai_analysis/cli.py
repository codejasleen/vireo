from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .cache import ResultCache
from .candidates import generate_candidate_pairs, load_clean_tickets
from .evaluation import write_human_label_templates
from .providers import provider_from_env
from .service import AIClassifier, DEFAULT_CONFIDENCE_THRESHOLD, PROMPT_VERSION, decide_pair


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Run a bounded Vireo AI-classification sample.")
    value.add_argument("--clean-tickets", required=True, type=Path)
    value.add_argument("--output-dir", required=True, type=Path)
    value.add_argument("--cache", type=Path)
    value.add_argument("--ticket-limit", type=int, default=12)
    value.add_argument("--pair-limit", type=int, default=8)
    value.add_argument("--confidence-threshold", type=float, default=float(os.getenv("VIREO_AI_CONFIDENCE_THRESHOLD", str(DEFAULT_CONFIDENCE_THRESHOLD))))
    return value


def stable_sample(rows: list[dict[str, Any]], key_fields: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    if limit < 0:
        raise ValueError("sample limits cannot be negative")
    return sorted(
        rows,
        key=lambda row: hashlib.sha256("|".join(str(row[field]) for field in key_fields).encode("utf-8")).hexdigest(),
    )[:limit]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 0 <= args.confidence_threshold <= 1:
        raise SystemExit("confidence threshold must be between 0 and 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.cache or (args.output_dir / "ai_cache.sqlite3")
    tickets = load_clean_tickets(args.clean_tickets)
    pairs = generate_candidate_pairs(tickets)
    ticket_sample = stable_sample(tickets, ("ticket_id",), args.ticket_limit)
    pair_sample = stable_sample(pairs, ("first_ticket_id", "return_ticket_id"), args.pair_limit)
    provider = provider_from_env()
    ticket_results: list[dict[str, Any]] = []
    pair_results: list[dict[str, Any]] = []

    with ResultCache(cache_path) as cache:
        classifier = AIClassifier(provider, cache)
        for ticket in ticket_sample:
            result = classifier.classify_ticket(ticket["ticket_id"], ticket["customer_message"])
            ticket_results.append({
                "ticket_id": ticket["ticket_id"],
                "customer_message": ticket["customer_message"],
                "classification": result.as_dict(),
            })
        for pair in pair_sample:
            result = classifier.classify_pair(
                pair["first_ticket_id"], pair["return_ticket_id"], pair["first_message"], pair["return_message"]
            )
            pair_results.append({
                **pair,
                "classification": result.as_dict(),
                "decision": decide_pair(result, pair["deterministic_evidence_pass"], args.confidence_threshold),
            })
        usage = classifier.usage.as_dict()

    usage.update({
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "confidence_threshold": args.confidence_threshold,
        "ticket_sample_size": len(ticket_results),
        "pair_sample_size": len(pair_results),
        "candidate_pair_count_available": len(pairs),
        "full_dataset_processed_by_model": False,
    })
    write_jsonl(args.output_dir / "ticket_classifications.jsonl", ticket_results)
    write_jsonl(args.output_dir / "pair_classifications.jsonl", pair_results)
    write_human_label_templates(args.output_dir, ticket_results, pair_results)
    with (args.output_dir / "usage.json").open("w", encoding="utf-8") as handle:
        json.dump(usage, handle, indent=2)
        handle.write("\n")
    print(json.dumps(usage, indent=2))
    return 0

