from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable
IST = timezone(timedelta(hours=5, minutes=30), name="IST")
UTC = timezone.utc
COMPLETED_STATUSES = {"resolved", "closed"}
CHANNEL_COST_INR = {"chat": 210, "email": 260, "voice": 520, "social": 240}

# Defined from the supplied README.txt contents and checked against the actual files.
SCHEMAS: dict[str, tuple[str, ...]] = {
    "tickets": (
        "ticket_id", "created_at", "first_response_at", "resolved_at", "status",
        "channel", "customer_id", "order_id", "product_sku", "category", "priority",
        "assigned_team", "agent_id", "transfers", "csat_score", "refund_amount_inr",
        "refund_reason_code", "replacement_issued", "customer_message", "agent_notes",
        "source_system",
    ),
    "agents": ("agent_id", "name", "site", "team", "shift", "tier", "from_date", "to_date"),
    "customers": ("customer_id", "name", "city", "state", "signup_date", "care_plus"),
    "orders": ("order_id", "customer_id", "sku", "order_date", "channel", "qty", "order_value_inr", "lot_code"),
    "products": ("sku", "product_name", "family", "launch_date", "unit_cost_inr", "retail_price_inr", "warranty_months"),
}


class PipelineError(ValueError):
    pass


class QualityReport:
    def __init__(self) -> None:
        self.warnings: dict[str, dict[str, Any]] = {}
        self.counts: dict[str, Any] = {}

    def warn(self, code: str, detail: str, example: str | None = None, increment: int = 1) -> None:
        item = self.warnings.setdefault(code, {"count": 0, "detail": detail, "examples": []})
        item["count"] += increment
        if example and example not in item["examples"] and len(item["examples"]) < 8:
            item["examples"].append(example)

    def as_dict(self) -> dict[str, Any]:
        return {
            "counts": self.counts,
            "warnings": [{"code": code, **value} for code, value in sorted(self.warnings.items())],
        }


def load_csv(path: Path, table: str) -> list[dict[str, str]]:
    expected = SCHEMAS[table]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        missing = [column for column in expected if column not in actual]
        if missing:
            raise PipelineError(f"{table}: missing required columns: {', '.join(missing)}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def parse_naive_timestamp(value: str, field: str, ticket_id: str, report: QualityReport) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        report.warn("invalid_timestamp", f"Invalid timestamp values are preserved as blank normalized values ({field}).", ticket_id)
        return None


def parse_date(value: str, field: str, key: str, report: QualityReport) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        report.warn("invalid_date", f"Invalid date values cannot be used ({field}).", key)
        return None


def to_int(value: str, field: str, key: str, report: QualityReport) -> int | None:
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        report.warn("invalid_integer", f"Invalid integer values are retained as blank ({field}).", key)
        return None


def to_float(value: str, field: str, key: str, report: QualityReport) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        report.warn("invalid_number", f"Invalid numeric values are retained as blank ({field}).", key)
        return None


def normalize_ticket(row: dict[str, str], report: QualityReport) -> dict[str, Any]:
    ticket = dict(row)
    key = row["ticket_id"] or "<blank ticket_id>"
    created_raw = parse_naive_timestamp(row["created_at"], "created_at", key, report)
    response_raw = parse_naive_timestamp(row["first_response_at"], "first_response_at", key, report)
    resolved_raw = parse_naive_timestamp(row["resolved_at"], "resolved_at", key, report)

    ticket["created_at_ist"] = created_raw.replace(tzinfo=IST) if created_raw else None
    ticket["first_response_at_ist"] = response_raw.replace(tzinfo=IST) if response_raw else None
    if resolved_raw and row["source_system"] == "legacy_fd":
        ticket["resolved_at_ist"] = resolved_raw.replace(tzinfo=UTC).astimezone(IST)
        ticket["legacy_resolution_timezone_corrected"] = True
    else:
        ticket["resolved_at_ist"] = resolved_raw.replace(tzinfo=IST) if resolved_raw else None
        ticket["legacy_resolution_timezone_corrected"] = False

    ticket["transfers_value"] = to_int(row["transfers"], "transfers", key, report)
    score = to_int(row["csat_score"], "csat_score", key, report)
    # Policy: legacy 0 means no response, just like blank.
    ticket["csat_score_value"] = None if score in (None, 0) else score
    if ticket["csat_score_value"] is not None and ticket["csat_score_value"] not in range(1, 6):
        report.warn("invalid_csat", "CSAT outside 1-5 is excluded from averages.", key)
        ticket["csat_score_value"] = None
    ticket["refund_amount_value"] = to_float(row["refund_amount_inr"], "refund_amount_inr", key, report)
    ticket["support_capacity_cost_inr"] = CHANNEL_COST_INR.get(row["channel"])

    if row["status"] not in {"resolved", "closed", "open", "pending"}:
        report.warn("unknown_status", "Ticket status is outside the supplied schema.", key)
    if row["channel"] not in CHANNEL_COST_INR:
        report.warn("unknown_channel", "Channel has no configured support-capacity rate.", key)
    if row["source_system"] not in {"helpdesk", "legacy_fd"}:
        report.warn("unknown_source_system", "Source system is outside the supplied schema.", key)
    if row["status"] in COMPLETED_STATUSES and not ticket["resolved_at_ist"]:
        report.warn("completed_without_resolution", "Completed ticket has no usable resolution timestamp.", key)
    if row["status"] not in COMPLETED_STATUSES and ticket["resolved_at_ist"]:
        report.warn("noncompleted_with_resolution", "Open or pending ticket has a resolution timestamp.", key)
    if ticket["created_at_ist"] and ticket["first_response_at_ist"] and ticket["first_response_at_ist"] < ticket["created_at_ist"]:
        report.warn("response_before_creation", "First response precedes ticket creation after normalization.", key)
    if ticket["first_response_at_ist"] and ticket["resolved_at_ist"] and ticket["resolved_at_ist"] < ticket["first_response_at_ist"]:
        report.warn("resolution_before_response", "Resolution precedes first response after normalization.", key)
    return ticket


def deduplicate_tickets(rows: list[dict[str, str]], report: QualityReport) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["ticket_id"]].append(row)

    cleaned: list[dict[str, Any]] = []
    duplicate_ids = 0
    duplicate_rows_removed = 0
    for ticket_id, group in groups.items():
        if not ticket_id:
            report.warn("blank_ticket_id", "Rows with blank ticket IDs cannot be safely deduplicated.")
        if len(group) > 1:
            duplicate_ids += 1
            duplicate_rows_removed += len(group) - 1
            fingerprint_columns = ("created_at", "customer_id", "product_sku", "customer_message")
            if any(len({row[column] for row in group}) > 1 for column in fingerprint_columns):
                report.warn("duplicate_ticket_conflict", "Duplicate ticket ID has conflicting identity fields.", ticket_id)
            else:
                report.warn("duplicate_ticket_reimport", "Duplicate ticket ID appears to be a cross-system re-import.", ticket_id)

        # Established investigation rule: prefer the current helpdesk row, then legacy.
        selected = sorted(group, key=lambda row: (0 if row["source_system"] == "helpdesk" else 1))[0]
        ticket = normalize_ticket(selected, report)
        ticket["duplicate_source_row_count"] = len(group)
        ticket["duplicate_sources"] = ",".join(sorted({row["source_system"] for row in group}))
        cleaned.append(ticket)

    report.counts["duplicate_ticket_ids"] = duplicate_ids
    report.counts["duplicate_rows_removed"] = duplicate_rows_removed
    return sorted(cleaned, key=lambda row: ((row["created_at_ist"] or datetime.max.replace(tzinfo=IST)), row["ticket_id"]))


def validate_reference_tables(
    agents: list[dict[str, str]], customers: list[dict[str, str]], orders: list[dict[str, str]],
    products: list[dict[str, str]], report: QualityReport,
) -> None:
    for table, rows, key in (
        ("customers", customers, "customer_id"), ("orders", orders, "order_id"), ("products", products, "sku")
    ):
        counts = Counter(row[key] for row in rows)
        for value, count in counts.items():
            if not value:
                report.warn(f"blank_{table}_key", f"{table} contains a blank primary key.")
            elif count > 1:
                report.warn(f"duplicate_{table}_key", f"{table} contains a duplicate primary key.", value)

    # Agents are one row per dated assignment, so agent_id is intentionally non-unique.
    for row in agents:
        parse_date(row["from_date"], "from_date", row["agent_id"], report)
        parse_date(row["to_date"], "to_date", row["agent_id"], report)


def add_order_matches(
    tickets: list[dict[str, Any]], orders: list[dict[str, str]], report: QualityReport,
) -> None:
    by_id: dict[str, dict[str, Any]] = {}
    by_customer_sku: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in orders:
        parsed = dict(row)
        parsed["order_date_value"] = parse_date(row["order_date"], "order_date", row["order_id"], report)
        if row["order_id"] and row["order_id"] not in by_id:
            by_id[row["order_id"]] = parsed
        by_customer_sku[(row["customer_id"], row["sku"])].append(parsed)

    for ticket in tickets:
        key = ticket["ticket_id"]
        created_date = ticket["created_at_ist"].date() if ticket["created_at_ist"] else None
        quoted_ids = sorted(set(re.findall(r"\bVR\d+\b", ticket["customer_message"].upper())))
        explicit_ids = set(quoted_ids)
        if ticket["order_id"]:
            explicit_ids.add(ticket["order_id"])
        explicit_id = next(iter(explicit_ids)) if len(explicit_ids) == 1 else ""
        ticket["quoted_order_ids"] = ",".join(quoted_ids)
        if ticket["order_id"] and quoted_ids and explicit_ids == {ticket["order_id"]}:
            ticket["order_id_source"] = "column_and_message"
        elif ticket["order_id"]:
            ticket["order_id_source"] = "column"
        elif quoted_ids:
            ticket["order_id_source"] = "customer_message"
        else:
            ticket["order_id_source"] = "fallback"
        ticket["matched_order_id"] = ""
        if len(explicit_ids) > 1:
            status = "explicit_conflict"
        elif explicit_id:
            order = by_id.get(explicit_id)
            if not order:
                status = "explicit_not_found"
            elif order["customer_id"] != ticket["customer_id"] or order["sku"] != ticket["product_sku"]:
                status = "explicit_mismatch"
            elif created_date and order["order_date_value"] and order["order_date_value"] > created_date:
                status = "explicit_future_order"
            else:
                status = "explicit_valid"
                ticket["matched_order_id"] = explicit_id
        else:
            candidates = []
            for order in by_customer_sku.get((ticket["customer_id"], ticket["product_sku"]), []):
                if not created_date or not order["order_date_value"] or order["order_date_value"] <= created_date:
                    candidates.append(order)
            if len(candidates) == 1:
                status = "fallback_unique"
                ticket["matched_order_id"] = candidates[0]["order_id"]
            elif len(candidates) == 0:
                status = "fallback_none"
            else:
                status = "fallback_ambiguous"
        ticket["order_match_status"] = status
        if status not in {"explicit_valid", "fallback_unique"}:
            report.warn(f"order_{status}", "Ticket order could not be linked unambiguously; matched_order_id is blank.", key)


def assign_roster(
    tickets: list[dict[str, Any]], agents: list[dict[str, str]], report: QualityReport,
) -> None:
    assignments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in agents:
        parsed = dict(row)
        parsed["from_date_value"] = parse_date(row["from_date"], "from_date", row["agent_id"], report)
        parsed["to_date_value"] = parse_date(row["to_date"], "to_date", row["agent_id"], report)
        assignments[row["agent_id"]].append(parsed)

    for ticket in tickets:
        when = ticket["resolved_at_ist"].date() if ticket["resolved_at_ist"] else None
        matches = []
        if when:
            for assignment in assignments.get(ticket["agent_id"], []):
                start, end = assignment["from_date_value"], assignment["to_date_value"]
                if start and start <= when and (end is None or when <= end):
                    matches.append(assignment)
        ticket["roster_match_status"] = "matched" if len(matches) == 1 else ("missing" if not matches else "ambiguous")
        for field in ("name", "site", "team", "shift", "tier"):
            ticket[f"agent_{field}"] = matches[0][field] if len(matches) == 1 else ""
        if ticket["status"] in COMPLETED_STATUSES and len(matches) != 1:
            report.warn(f"roster_{ticket['roster_match_status']}", "Completed ticket has no single active roster assignment.", ticket["ticket_id"])


def observation_boundary(tickets: list[dict[str, Any]]) -> datetime:
    created = [ticket["created_at_ist"] for ticket in tickets if ticket["created_at_ist"]]
    if not created:
        raise PipelineError("tickets: no valid creation timestamps; observation boundary cannot be derived")
    last_date = max(created).date()
    return datetime.combine(last_date + timedelta(days=1), time.min, tzinfo=IST)


def add_maturity(tickets: list[dict[str, Any]], boundary: datetime) -> None:
    for ticket in tickets:
        resolved = ticket["resolved_at_ist"]
        ticket["completed"] = ticket["status"] in COMPLETED_STATUSES
        ticket["repeat_observation_eligible"] = bool(
            ticket["completed"] and resolved and resolved + timedelta(days=30) <= boundary
        )


def monday(value: datetime) -> str:
    return (value.date() - timedelta(days=value.weekday())).isoformat()


def weekly_ticket_metrics(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}

    def row_for(week: str) -> dict[str, Any]:
        return metrics.setdefault(week, {
            "week_start": week, "tickets_created": 0, "created_chat": 0, "created_email": 0,
            "created_voice": 0, "created_social": 0, "created_support_capacity_inr": 0,
            "tickets_completed": 0, "resolved_count": 0, "auto_closed_count": 0,
            "mature_for_repeat_measurement": 0, "csat_response_count": 0, "csat_score_sum": 0.0,
            "created_transfer_count": 0,
        })

    for ticket in tickets:
        if ticket["created_at_ist"]:
            row = row_for(monday(ticket["created_at_ist"]))
            row["tickets_created"] += 1
            if ticket["channel"] in CHANNEL_COST_INR:
                row[f"created_{ticket['channel']}"] += 1
                row["created_support_capacity_inr"] += CHANNEL_COST_INR[ticket["channel"]]
            row["created_transfer_count"] += ticket["transfers_value"] or 0
        if ticket["completed"] and ticket["resolved_at_ist"]:
            row = row_for(monday(ticket["resolved_at_ist"]))
            row["tickets_completed"] += 1
            row["resolved_count"] += int(ticket["status"] == "resolved")
            row["auto_closed_count"] += int(ticket["status"] == "closed")
            row["mature_for_repeat_measurement"] += int(ticket["repeat_observation_eligible"])
            if ticket["csat_score_value"] is not None:
                row["csat_response_count"] += 1
                row["csat_score_sum"] += ticket["csat_score_value"]

    result = []
    for week in sorted(metrics):
        row = metrics[week]
        count = row.pop("csat_response_count")
        score_sum = row.pop("csat_score_sum")
        row["csat_response_count"] = count
        row["average_csat"] = round(score_sum / count, 3) if count else ""
        result.append(row)
    return result


def weekly_agent_metrics(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for ticket in tickets:
        if ticket["completed"] and ticket["resolved_at_ist"]:
            groups[(monday(ticket["resolved_at_ist"]), ticket["agent_id"])].append(ticket)

    result = []
    for (week, agent_id), rows in sorted(groups.items()):
        scores = [row["csat_score_value"] for row in rows if row["csat_score_value"] is not None]
        roster_matches = [row for row in rows if row["roster_match_status"] == "matched"]
        representative = roster_matches[0] if roster_matches else rows[0]
        result.append({
            "week_start": week,
            "agent_id": agent_id,
            "agent_name": representative["agent_name"],
            "site": representative["agent_site"],
            "roster_team": representative["agent_team"],
            "shift": representative["agent_shift"],
            "tier": representative["agent_tier"],
            "completed_count": len(rows),
            "resolved_count": sum(row["status"] == "resolved" for row in rows),
            "auto_closed_count": sum(row["status"] == "closed" for row in rows),
            "chat_count": sum(row["channel"] == "chat" for row in rows),
            "email_count": sum(row["channel"] == "email" for row in rows),
            "voice_count": sum(row["channel"] == "voice" for row in rows),
            "social_count": sum(row["channel"] == "social" for row in rows),
            "support_capacity_inr": sum(row["support_capacity_cost_inr"] or 0 for row in rows),
            "mature_for_repeat_measurement": sum(row["repeat_observation_eligible"] for row in rows),
            "csat_response_count": len(scores),
            "average_csat": round(fmean(scores), 3) if scores else "",
        })
    return result


def serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "Y" if value else "N"
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(fields or (rows[0].keys() if rows else []))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialise(row.get(key)) for key in fieldnames})


def run_pipeline(paths: dict[str, Path], output_dir: Path) -> dict[str, Any]:
    report = QualityReport()
    raw = {table: load_csv(paths[table], table) for table in SCHEMAS}
    report.counts["input_rows"] = {table: len(rows) for table, rows in raw.items()}
    validate_reference_tables(raw["agents"], raw["customers"], raw["orders"], raw["products"], report)
    tickets = deduplicate_tickets(raw["tickets"], report)

    customer_ids = {row["customer_id"] for row in raw["customers"]}
    product_ids = {row["sku"] for row in raw["products"]}
    agent_ids = {row["agent_id"] for row in raw["agents"]}
    for ticket in tickets:
        if ticket["customer_id"] not in customer_ids:
            report.warn("ticket_customer_not_found", "Ticket customer_id is absent from customers.csv.", ticket["ticket_id"])
        if ticket["product_sku"] not in product_ids:
            report.warn("ticket_product_not_found", "Ticket product_sku is absent from products.csv.", ticket["ticket_id"])
        if ticket["agent_id"] not in agent_ids:
            report.warn("ticket_agent_not_found", "Ticket agent_id is absent from agents.csv.", ticket["ticket_id"])

    add_order_matches(tickets, raw["orders"], report)
    assign_roster(tickets, raw["agents"], report)
    boundary = observation_boundary(tickets)
    add_maturity(tickets, boundary)
    ticket_weeks = weekly_ticket_metrics(tickets)
    agent_weeks = weekly_agent_metrics(tickets)

    clean_fields = list(SCHEMAS["tickets"]) + [
        "created_at_ist", "first_response_at_ist", "resolved_at_ist",
        "legacy_resolution_timezone_corrected", "duplicate_source_row_count", "duplicate_sources",
        "quoted_order_ids", "order_id_source", "matched_order_id", "order_match_status",
        "completed", "repeat_observation_eligible",
        "support_capacity_cost_inr", "agent_name", "agent_site", "agent_team", "agent_shift",
        "agent_tier", "roster_match_status",
    ]
    write_csv(output_dir / "clean_tickets.csv", tickets, clean_fields)
    write_csv(output_dir / "weekly_ticket_metrics.csv", ticket_weeks)
    write_csv(output_dir / "weekly_agent_metrics.csv", agent_weeks)

    report.counts.update({
        "clean_ticket_rows": len(tickets),
        "completed_tickets": sum(ticket["completed"] for ticket in tickets),
        "resolved_tickets": sum(ticket["status"] == "resolved" for ticket in tickets),
        "auto_closed_tickets": sum(ticket["status"] == "closed" for ticket in tickets),
        "repeat_observation_eligible_tickets": sum(ticket["repeat_observation_eligible"] for ticket in tickets),
        "legacy_resolution_timestamps_corrected": sum(ticket["legacy_resolution_timezone_corrected"] for ticket in tickets),
        "order_match_status": dict(sorted(Counter(ticket["order_match_status"] for ticket in tickets).items())),
        "weekly_ticket_metric_rows": len(ticket_weeks),
        "weekly_agent_metric_rows": len(agent_weeks),
        "observation_boundary_ist": boundary.isoformat(timespec="minutes"),
        "created_support_capacity_inr": sum(ticket["support_capacity_cost_inr"] or 0 for ticket in tickets),
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "data_quality_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report.as_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report.as_dict()
