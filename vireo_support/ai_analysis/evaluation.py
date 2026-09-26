from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


TICKET_LABEL_FIELDS = [
    "ticket_id", "customer_message", "model_issue_category", "model_confidence", "model_evidence",
    "human_issue_category", "human_notes",
]

PAIR_LABEL_FIELDS = [
    "first_ticket_id", "return_ticket_id", "first_message", "return_message",
    "deterministic_evidence_pass", "model_same_issue", "model_issue_category", "model_confidence",
    "model_uncertain", "model_reason", "human_same_issue", "human_issue_category",
    "human_uncertain", "human_notes",
]


def write_human_label_templates(
    output_dir: Path, ticket_results: list[dict[str, Any]], pair_results: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ticket_rows = [{
        "ticket_id": row["ticket_id"],
        "customer_message": row["customer_message"],
        "model_issue_category": row["classification"]["issue_category"],
        "model_confidence": row["classification"]["confidence"],
        "model_evidence": row["classification"]["evidence"],
        "human_issue_category": "",
        "human_notes": "",
    } for row in ticket_results]
    pair_rows = [{
        "first_ticket_id": row["first_ticket_id"],
        "return_ticket_id": row["return_ticket_id"],
        "first_message": row["first_message"],
        "return_message": row["return_message"],
        "deterministic_evidence_pass": row["deterministic_evidence_pass"],
        "model_same_issue": row["classification"]["same_issue"],
        "model_issue_category": row["classification"]["issue_category"],
        "model_confidence": row["classification"]["confidence"],
        "model_uncertain": row["classification"]["uncertain"],
        "model_reason": row["classification"]["reason"],
        "human_same_issue": "",
        "human_issue_category": "",
        "human_uncertain": "",
        "human_notes": "",
    } for row in pair_results]
    _write_csv(output_dir / "human_ticket_labels.csv", TICKET_LABEL_FIELDS, ticket_rows)
    _write_csv(output_dir / "human_pair_labels.csv", PAIR_LABEL_FIELDS, pair_rows)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

