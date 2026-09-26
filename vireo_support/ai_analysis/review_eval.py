from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from .cache import ResultCache
from .candidates import generate_candidate_pairs, load_clean_tickets
from .providers import provider_from_env
from .service import AIClassifier, DEFAULT_CONFIDENCE_THRESHOLD, PROMPT_VERSION, decide_pair


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Evaluate one provider on a fixed, human-labelled pair sample.")
    value.add_argument("--clean-tickets", required=True, type=Path)
    value.add_argument("--sample", required=True, type=Path)
    value.add_argument("--output-dir", required=True, type=Path)
    value.add_argument("--cache", type=Path)
    value.add_argument(
        "--confidence-threshold",
        type=float,
        default=float(os.getenv("VIREO_AI_CONFIDENCE_THRESHOLD", str(DEFAULT_CONFIDENCE_THRESHOLD))),
    )
    return value


def parse_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "y", "yes"}:
        return True
    if normalized in {"false", "0", "n", "no"}:
        return False
    raise ValueError(f"{field} must be true or false")


def calculate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(row["human_same_issue"] and row["predicted_positive"] for row in rows)
    fp = sum(not row["human_same_issue"] and row["predicted_positive"] for row in rows)
    fn = sum(row["human_same_issue"] and not row["predicted_positive"] for row in rows)
    tn = sum(not row["human_same_issue"] and not row["predicted_positive"] for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def load_sample(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"first_ticket_id", "return_ticket_id", "human_same_issue", "human_issue_category"}
    missing = required - set(rows[0] if rows else ())
    if missing:
        raise ValueError(f"evaluation sample missing columns: {', '.join(sorted(missing))}")
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 0 <= args.confidence_threshold <= 1:
        raise SystemExit("confidence threshold must be between 0 and 1")

    tickets = load_clean_tickets(args.clean_tickets)
    pairs = {
        (row["first_ticket_id"], row["return_ticket_id"]): row
        for row in generate_candidate_pairs(tickets)
    }
    sample = load_sample(args.sample)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.cache or args.output_dir / "ai_cache.sqlite3"
    provider = provider_from_env()
    results: list[dict[str, Any]] = []

    with ResultCache(cache_path) as cache:
        classifier = AIClassifier(provider, cache)
        for label in sample:
            key = (label["first_ticket_id"], label["return_ticket_id"])
            if key not in pairs:
                raise ValueError(f"evaluation pair is absent from deterministic candidates: {key[0]} -> {key[1]}")
            pair = pairs[key]
            classification = classifier.classify_pair(
                pair["first_ticket_id"], pair["return_ticket_id"], pair["first_message"], pair["return_message"]
            )
            decision = decide_pair(classification, pair["deterministic_evidence_pass"], args.confidence_threshold)
            results.append({
                **pair,
                "human_same_issue": parse_bool(label["human_same_issue"], "human_same_issue"),
                "human_issue_category": label["human_issue_category"],
                "review_tier": label.get("review_tier", ""),
                "classification": classification.as_dict(),
                "decision": decision,
                "predicted_positive": decision == "high_confidence_repeat",
            })
        usage = classifier.usage.as_dict()

    metrics = calculate_metrics(results)
    metrics.update({
        "sample_size": len(results),
        "positive_labels": sum(row["human_same_issue"] for row in results),
        "negative_labels": sum(not row["human_same_issue"] for row in results),
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "confidence_threshold": args.confidence_threshold,
        "usage": usage,
        "pricing_configured": bool(
            os.getenv("VIREO_AI_INPUT_USD_PER_MILLION") and os.getenv("VIREO_AI_OUTPUT_USD_PER_MILLION")
        ),
    })
    write_jsonl(args.output_dir / "pair_results.jsonl", results)
    with (args.output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
