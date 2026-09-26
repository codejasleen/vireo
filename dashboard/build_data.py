"""Build the dashboard data bundle from saved Vireo outputs.

This script is intentionally standard-library only. It reads the preserved
pipeline and investigation artifacts and writes a browser-ready JavaScript
bundle; it never calls an external service.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "outputs" / "pipeline"

ISSUE_LABELS = {
    "delivery_missing": "Missing delivery / tracking",
    "missing_delivery": "Missing delivery / tracking",
    "missing_delivery_tracking": "Missing delivery / tracking",
    "pairing": "Pairing / device discovery",
    "pairing_device_discovery": "Pairing / device discovery",
    "refund_pending": "Refund pending",
    "return_pickup": "Return pickup",
    "payment_no_order": "Payment taken / no order",
    "battery_drain": "Battery drain",
    "bluetooth_dropout": "Bluetooth dropouts",
    "bluetooth_dropouts": "Bluetooth dropouts",
    "audio_distortion": "Audio distortion",
    "coupon_discount": "Coupon / discount failure",
    "coupon_discount_failure": "Coupon / discount failure",
    "app_crash": "App crash / failure to open",
    "app_crash_failure": "App crash / failure to open",
    "repair_status": "Repair / warranty status",
    "repair_warranty_status": "Repair / warranty status",
    "firmware_update": "Firmware update failure",
    "firmware_update_failure": "Firmware update failure",
    "enquiry_compatibility": "Product compatibility",
    "cancel_order": "Order cancellation",
    "transit_damage": "Transit damage",
    "wrong_item": "Wrong item / variant",
    "invoice": "Invoice request",
    "login_otp": "Login / OTP",
    "address_change": "Delivery address change",
    "one_side_audio": "One-sided audio",
    "duplicate_payment": "Duplicate payment",
    "left_bud_charging": "Earbud charging failure",
    "case_charging": "Charging-case failure",
    "microphone": "Microphone quality",
    "enquiry_multi_device": "Multi-device compatibility",
    "watch_strap": "Watch strap issue",
    "enquiry_water": "Water resistance enquiry",
    "watch_touch": "Watch touchscreen issue",
    "wifi_setup": "Wi-Fi setup",
    "speaker_power": "Speaker power issue",
}

# These are the reviewed findings saved in outputs/repeat-contact-investigation.md
# and outputs/baseline-and-pilot.md. They are held here as presentation data so
# the dashboard cannot silently substitute the rejected offline classifier.
REPEAT_CATEGORIES = [
    ("Missing delivery / tracking", 188, 46_930),
    ("Pairing / device discovery", 93, 24_500),
    ("Refund pending", 79, 21_470),
    ("Return pickup", 70, 19_420),
    ("Payment taken / no order", 66, 16_000),
    ("Battery drain", 58, 15_810),
    ("Bluetooth dropouts", 50, 12_340),
    ("App crash / failure to open", 48, 11_090),
    ("Audio distortion", 46, 11_620),
    ("Coupon / discount failure", 43, 11_120),
    ("Repair / warranty status", 43, 10_180),
    ("Firmware update failure", 41, 10_200),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    weekly = read_csv(PIPELINE / "weekly_ticket_metrics.csv")
    agents = read_csv(PIPELINE / "weekly_agent_metrics.csv")
    clean_tickets = read_csv(PIPELINE / "clean_tickets.csv")

    observation_end = max(
        datetime.fromisoformat(row["created_at_ist"]).date() for row in clean_tickets
    )
    complete_weeks = [
        row
        for row in weekly
        if date.fromisoformat(row["week_start"]) + timedelta(days=6) <= observation_end
        and int(row["tickets_created"]) > 0
    ]
    latest = complete_weeks[-1]
    previous = complete_weeks[-2]
    issue_by_week: dict[str, Counter[str]] = defaultdict(Counter)
    clean_ticket_ids = {row["ticket_id"] for row in clean_tickets}
    seen_ticket_ids: set[str] = set()
    with (ROOT / "work" / "labeled_tickets.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            ticket = json.loads(line)
            if ticket["ticket_id"] not in clean_ticket_ids or ticket["ticket_id"] in seen_ticket_ids:
                continue
            seen_ticket_ids.add(ticket["ticket_id"])
            week = (
                datetime.fromisoformat(ticket["created_at"]).date()
                - timedelta(days=datetime.fromisoformat(ticket["created_at"]).date().weekday())
            ).isoformat()
            labels = ticket.get("customer_labels", [])
            if labels:
                issue = ISSUE_LABELS.get(labels[0], labels[0].replace("_", " ").title())
            else:
                issue = "Other / unclear"
            issue_by_week[week][issue] += 1

    agent_weeks: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in agents:
        if int(row["completed_count"]) <= 0:
            continue
        agent_weeks[row["week_start"]].append(
            {
                "name": row["agent_name"],
                "team": row["roster_team"],
                "site": row["site"],
                "closed": int(row["completed_count"]),
            }
        )
    for rows in agent_weeks.values():
        rows.sort(key=lambda row: (-int(row["closed"]), str(row["name"])))

    overview_weeks = [row["week_start"] for row in complete_weeks]
    overview_by_week = {
        row["week_start"]: {
            "tickets_handled": int(row["tickets_completed"]),
            "tickets_created": int(row["tickets_created"]),
            "resolved": int(row["resolved_count"]),
            "auto_closed": int(row["auto_closed_count"]),
            "chat": int(row["created_chat"]),
            "email": int(row["created_email"]),
            "voice": int(row["created_voice"]),
            "social": int(row["created_social"]),
            "average_csat": float(row["average_csat"]) if row["average_csat"] else None,
            "csat_responses": int(row["csat_response_count"]),
            "issues": dict(issue_by_week[row["week_start"]]),
        }
        for row in complete_weeks
    }

    data = {
        "meta": {
            "title": "Vireo Support Weekly Digest",
            "observation_end": observation_end.isoformat(),
            "generated_from": "Saved deterministic pipeline and reviewed investigation outputs",
        },
        "overview": {
            "default_week": latest["week_start"],
            "weeks": overview_weeks,
            "by_week": overview_by_week,
        },
        "repeat_contacts": {
            "overall_rate": 9.61,
            "overall_numerator": 1_008,
            "overall_denominator": 10_485,
            "delivery_rate": 14.34,
            "delivery_numerator": 186,
            "delivery_denominator": 1_297,
            "pilot_target": 10.76,
            "relative_reduction": 25,
            "avoided_contacts": 37,
            "capacity_value_inr": 9_350,
            "categories": [
                {"name": name, "contacts": contacts, "capacity_inr": capacity}
                for name, contacts, capacity in REPEAT_CATEGORIES
            ],
            "validation": {
                "reviewed_pairs": 68,
                "reviewed_high_confidence": 67,
                "observed_high_confidence_errors": 0,
                "rule_of_three_upper_bound_pct": 4.5,
            },
        },
        "leaderboard": {
            "default_week": latest["week_start"],
            "weeks": [row["week_start"] for row in reversed(complete_weeks)],
            "by_week": agent_weeks,
        },
    }

    destination = Path(__file__).with_name("data.js")
    destination.write_text(
        "window.VIREO_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(
        f"Built {destination.name}: {len(complete_weeks)} complete weeks, "
        f"{len(agent_weeks)} leaderboard weeks, latest {latest['week_start']}"
    )


if __name__ == "__main__":
    main()
