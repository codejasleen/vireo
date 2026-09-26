from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _timestamp(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def load_clean_tickets(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["created_value"] = _timestamp(row["created_at_ist"])
        row["resolved_value"] = _timestamp(row["resolved_at_ist"])
    return rows


def generate_candidate_pairs(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same customer/product, opened within 30 days after a completed ticket resolved."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for ticket in tickets:
        groups[(ticket["customer_id"], ticket["product_sku"])].append(ticket)

    pairs: list[dict[str, Any]] = []
    for group in groups.values():
        group.sort(key=lambda row: (row["created_at_ist"] or "9999-12-31T23:59+05:30", row["ticket_id"]))
        previous: list[dict[str, Any]] = []
        for current in group:
            created = current["created_value"]
            if not created:
                continue
            for prior in previous:
                resolved = prior["resolved_value"]
                if prior["status"] not in {"resolved", "closed"} or not resolved:
                    continue
                if resolved <= created <= resolved + timedelta(days=30):
                    same_order = bool(
                        prior["matched_order_id"] and current["matched_order_id"]
                        and prior["matched_order_id"] == current["matched_order_id"]
                    )
                    pairs.append({
                        "first_ticket_id": prior["ticket_id"],
                        "return_ticket_id": current["ticket_id"],
                        "customer_id": current["customer_id"],
                        "product_sku": current["product_sku"],
                        "first_message": prior["customer_message"],
                        "return_message": current["customer_message"],
                        "gap_days": round((created - resolved).total_seconds() / 86400, 6),
                        "first_order_id": prior["matched_order_id"],
                        "return_order_id": current["matched_order_id"],
                        "same_order": same_order,
                        "deterministic_evidence_pass": same_order,
                    })
            previous.append(current)
    return sorted(pairs, key=lambda row: (row["return_ticket_id"], row["first_ticket_id"]))
