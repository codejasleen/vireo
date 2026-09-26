from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from vireo_support.pipeline import (
    CHANNEL_COST_INR,
    IST,
    PipelineError,
    QualityReport,
    SCHEMAS,
    add_maturity,
    add_order_matches,
    deduplicate_tickets,
    load_csv,
    observation_boundary,
    weekly_agent_metrics,
    weekly_ticket_metrics,
)


def ticket(**updates: str) -> dict[str, str]:
    row = {column: "" for column in SCHEMAS["tickets"]}
    row.update({
        "ticket_id": "T1", "created_at": "2026-05-01 10:00", "first_response_at": "2026-05-01 10:05",
        "resolved_at": "2026-05-01 11:00", "status": "resolved", "channel": "chat",
        "customer_id": "C1", "product_sku": "P1", "category": "Other", "priority": "Normal",
        "assigned_team": "Chat Frontline", "agent_id": "A1", "transfers": "0", "csat_score": "5",
        "replacement_issued": "N", "customer_message": "help", "agent_notes": "done",
        "source_system": "helpdesk",
    })
    row.update(updates)
    return row


def enrich_for_metrics(row: dict, **updates) -> dict:
    row = dict(row)
    row.update({
        "completed": row["status"] in {"resolved", "closed"},
        "repeat_observation_eligible": False,
        "support_capacity_cost_inr": CHANNEL_COST_INR[row["channel"]],
        "agent_name": "Agent One", "agent_site": "Indore", "agent_team": "Chat Frontline",
        "agent_shift": "Day", "agent_tier": "1", "roster_match_status": "matched",
    })
    row.update(updates)
    return row


class PipelineTests(unittest.TestCase):
    def test_schema_validation_rejects_missing_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["ticket_id"])
                writer.writeheader()
            with self.assertRaises(PipelineError):
                load_csv(path, "tickets")

    def test_deduplication_prefers_helpdesk_and_corrects_legacy_resolution(self):
        report = QualityReport()
        duplicate = ticket(ticket_id="D1", source_system="legacy_fd", resolved_at="2025-01-01 06:19")
        preferred = ticket(ticket_id="D1", source_system="helpdesk", resolved_at="2025-01-01 11:49", csat_score="4")
        legacy_only = ticket(ticket_id="L1", source_system="legacy_fd", resolved_at="2025-01-02 06:19")
        rows = deduplicate_tickets([duplicate, preferred, legacy_only], report)
        by_id = {row["ticket_id"]: row for row in rows}
        self.assertEqual(len(rows), 2)
        self.assertEqual(by_id["D1"]["source_system"], "helpdesk")
        self.assertEqual(by_id["D1"]["resolved_at_ist"].strftime("%Y-%m-%d %H:%M %z"), "2025-01-01 11:49 +0530")
        self.assertEqual(by_id["L1"]["resolved_at_ist"].strftime("%Y-%m-%d %H:%M %z"), "2025-01-02 11:49 +0530")
        self.assertEqual(report.counts["duplicate_rows_removed"], 1)

    def test_maturity_requires_full_thirty_day_window(self):
        boundary = datetime(2026, 7, 1, tzinfo=IST)
        eligible = enrich_for_metrics(deduplicate_tickets([ticket(resolved_at="2026-05-31 23:59")], QualityReport())[0])
        ineligible = enrich_for_metrics(deduplicate_tickets([ticket(ticket_id="T2", resolved_at="2026-06-01 00:01")], QualityReport())[0])
        add_maturity([eligible, ineligible], boundary)
        self.assertTrue(eligible["repeat_observation_eligible"])
        self.assertFalse(ineligible["repeat_observation_eligible"])

    def test_observation_boundary_is_midnight_after_last_created_date(self):
        rows = deduplicate_tickets([
            ticket(ticket_id="T1", created_at="2026-06-30 23:29"),
            ticket(ticket_id="T2", created_at="2026-06-29 09:00"),
        ], QualityReport())
        self.assertEqual(observation_boundary(rows), datetime(2026, 7, 1, tzinfo=IST))

    def test_order_matching_never_selects_ambiguous_fallback(self):
        report = QualityReport()
        rows = deduplicate_tickets([
            ticket(ticket_id="T1", order_id=""),
            ticket(ticket_id="T2", order_id="VR3"),
        ], report)
        orders = [
            {"order_id": "VR1", "customer_id": "C1", "sku": "P1", "order_date": "2026-01-01", "channel": "site", "qty": "1", "order_value_inr": "100", "lot_code": "L1"},
            {"order_id": "VR2", "customer_id": "C1", "sku": "P1", "order_date": "2026-02-01", "channel": "site", "qty": "1", "order_value_inr": "100", "lot_code": "L2"},
            {"order_id": "VR3", "customer_id": "OTHER", "sku": "P1", "order_date": "2026-01-01", "channel": "site", "qty": "1", "order_value_inr": "100", "lot_code": "L3"},
        ]
        add_order_matches(rows, orders, report)
        by_id = {row["ticket_id"]: row for row in rows}
        self.assertEqual(by_id["T1"]["order_match_status"], "fallback_ambiguous")
        self.assertEqual(by_id["T1"]["matched_order_id"], "")
        self.assertEqual(by_id["T2"]["order_match_status"], "explicit_mismatch")
        self.assertEqual(by_id["T2"]["matched_order_id"], "")

    def test_order_id_can_be_extracted_from_message_but_conflicts_are_not_selected(self):
        report = QualityReport()
        rows = deduplicate_tickets([
            ticket(ticket_id="T1", order_id="", customer_message="Please check VR1"),
            ticket(ticket_id="T2", order_id="VR1", customer_message="I meant VR2"),
        ], report)
        orders = [
            {"order_id": "VR1", "customer_id": "C1", "sku": "P1", "order_date": "2026-01-01", "channel": "site", "qty": "1", "order_value_inr": "100", "lot_code": "L1"},
            {"order_id": "VR2", "customer_id": "C1", "sku": "P1", "order_date": "2026-01-01", "channel": "site", "qty": "1", "order_value_inr": "100", "lot_code": "L2"},
        ]
        add_order_matches(rows, orders, report)
        by_id = {row["ticket_id"]: row for row in rows}
        self.assertEqual(by_id["T1"]["order_match_status"], "explicit_valid")
        self.assertEqual(by_id["T1"]["matched_order_id"], "VR1")
        self.assertEqual(by_id["T1"]["order_id_source"], "customer_message")
        self.assertEqual(by_id["T2"]["order_match_status"], "explicit_conflict")
        self.assertEqual(by_id["T2"]["matched_order_id"], "")

    def test_weekly_ticket_metrics_use_created_and_resolution_weeks(self):
        report = QualityReport()
        first = deduplicate_tickets([ticket(ticket_id="T1", channel="chat", transfers="1")], report)[0]
        second = deduplicate_tickets([ticket(
            ticket_id="T2", created_at="2026-05-03 09:00", first_response_at="2026-05-03 09:10",
            resolved_at="2026-05-04 10:00", status="closed", channel="voice", transfers="2", csat_score="0",
        )], report)[0]
        for row in (first, second):
            row.update({"completed": True, "repeat_observation_eligible": True})
        output = weekly_ticket_metrics([first, second])
        by_week = {row["week_start"]: row for row in output}
        created_week = by_week["2026-04-27"]
        self.assertEqual(created_week["tickets_created"], 2)
        self.assertEqual(created_week["created_support_capacity_inr"], 730)
        self.assertEqual(created_week["created_transfer_count"], 3)
        self.assertEqual(created_week["tickets_completed"], 1)
        resolution_week = by_week["2026-05-04"]
        self.assertEqual(resolution_week["auto_closed_count"], 1)

    def test_weekly_agent_metrics_separate_resolved_and_auto_closed(self):
        report = QualityReport()
        first = enrich_for_metrics(deduplicate_tickets([ticket(ticket_id="T1", channel="chat")], report)[0], repeat_observation_eligible=True)
        second = enrich_for_metrics(deduplicate_tickets([ticket(ticket_id="T2", status="closed", channel="voice", csat_score="")], report)[0])
        rows = weekly_agent_metrics([first, second])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["completed_count"], 2)
        self.assertEqual(rows[0]["resolved_count"], 1)
        self.assertEqual(rows[0]["auto_closed_count"], 1)
        self.assertEqual(rows[0]["support_capacity_inr"], 730)
        self.assertEqual(rows[0]["csat_response_count"], 1)


if __name__ == "__main__":
    unittest.main()
