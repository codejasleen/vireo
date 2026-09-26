from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from vireo_support.ai_analysis.cache import ResultCache
from vireo_support.ai_analysis.candidates import generate_candidate_pairs
from vireo_support.ai_analysis.models import ModelResponseError, PairClassification, TicketClassification
from vireo_support.ai_analysis.providers import ModelRequest, OfflineProvider, ProviderResponse, provider_from_env
from vireo_support.ai_analysis.review_eval import calculate_metrics
from vireo_support.ai_analysis.service import AIClassifier, decide_pair


class FakeProvider:
    name = "fake"
    model = "fake-v1"

    def __init__(self, content: str) -> None:
        self.content = content
        self.call_count = 0

    def complete(self, request: ModelRequest) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(self.content, {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "estimated_cost_usd": 0.001}, True)


def valid_pair(**updates):
    value = {
        "same_issue": True,
        "issue_category": "missing_delivery_tracking",
        "confidence": 0.91,
        "evidence_from_first": "order not delivered",
        "evidence_from_return": "tracking still stuck",
        "reason": "Both messages describe the same undelivered order.",
        "uncertain": False,
    }
    value.update(updates)
    return value


class AIAnalysisTests(unittest.TestCase):
    def test_review_metrics(self):
        metrics = calculate_metrics([
            {"human_same_issue": True, "predicted_positive": True},
            {"human_same_issue": True, "predicted_positive": False},
            {"human_same_issue": False, "predicted_positive": True},
            {"human_same_issue": False, "predicted_positive": False},
        ])
        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 1)
        self.assertEqual(metrics["f1"], 0.5)

    def test_offline_provider_keeps_its_default_model(self):
        with patch.dict("os.environ", {"VIREO_AI_PROVIDER": "offline"}, clear=True):
            provider = provider_from_env()
        self.assertIsInstance(provider, OfflineProvider)
        self.assertEqual(provider.model, "offline-rules-v1")

    def test_openai_compatible_provider_requires_model(self):
        with patch.dict(
            "os.environ",
            {"VIREO_AI_PROVIDER": "openai_compatible", "VIREO_AI_API_KEY": "test"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "VIREO_AI_MODEL"):
                provider_from_env()

    def test_valid_ticket_response(self):
        result = TicketClassification.from_dict({
            "issue_category": "refund_pending", "confidence": 0.94, "evidence": "refund not received"
        })
        self.assertEqual(result.issue_category, "refund_pending")

    def test_malformed_response_is_rejected_and_cached(self):
        provider = FakeProvider("not json")
        with tempfile.TemporaryDirectory() as directory, ResultCache(Path(directory) / "cache.sqlite3") as cache:
            classifier = AIClassifier(provider, cache)
            with self.assertRaises(ModelResponseError):
                classifier.classify_ticket("T1", "refund not received")
            with self.assertRaises(ModelResponseError):
                classifier.classify_ticket("T1", "refund not received")
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(classifier.usage.cache_hits, 1)

    def test_valid_response_is_reused_from_cache(self):
        provider = FakeProvider(json.dumps({
            "issue_category": "pairing_device_discovery", "confidence": 0.9, "evidence": "cannot pair"
        }))
        with tempfile.TemporaryDirectory() as directory, ResultCache(Path(directory) / "cache.sqlite3") as cache:
            classifier = AIClassifier(provider, cache)
            first = classifier.classify_ticket("T1", "cannot pair")
            second = classifier.classify_ticket("T1", "cannot pair")
            self.assertEqual(first, second)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(classifier.usage.cache_hits, 1)
            self.assertEqual(classifier.usage.provider_calls, 1)

    def test_uncertain_pair_cannot_be_counted(self):
        result = PairClassification.from_dict(valid_pair(
            same_issue=None, confidence=0.4, uncertain=True,
            reason="The first message is too vague.", issue_category="other",
        ))
        self.assertEqual(decide_pair(result, True, 0.85), "uncertain")

    def test_threshold_is_inclusive(self):
        at_threshold = PairClassification.from_dict(valid_pair(confidence=0.85))
        below = PairClassification.from_dict(valid_pair(confidence=0.849))
        self.assertEqual(decide_pair(at_threshold, True, 0.85), "high_confidence_repeat")
        self.assertEqual(decide_pair(below, True, 0.85), "below_confidence_threshold")

    def test_deterministic_evidence_overrides_high_model_confidence(self):
        result = PairClassification.from_dict(valid_pair(confidence=0.99))
        self.assertEqual(decide_pair(result, False, 0.85), "excluded_deterministic_evidence")

    def test_model_different_issue_is_not_counted(self):
        result = PairClassification.from_dict(valid_pair(same_issue=False, confidence=0.98))
        self.assertEqual(decide_pair(result, True, 0.85), "different_issue")

    def test_uncertain_cannot_assert_same_issue(self):
        with self.assertRaises(ModelResponseError):
            PairClassification.from_dict(valid_pair(uncertain=True, same_issue=True))

    def test_hallucinated_evidence_is_rejected(self):
        provider = FakeProvider(json.dumps({
            "issue_category": "refund_pending", "confidence": 0.95, "evidence": "customer asked about a refund"
        }))
        with tempfile.TemporaryDirectory() as directory, ResultCache(Path(directory) / "cache.sqlite3") as cache:
            classifier = AIClassifier(provider, cache)
            with self.assertRaises(ModelResponseError):
                classifier.classify_ticket("T1", "My money has not come back.")

    def test_candidate_pairs_require_time_window_and_same_matched_order_for_gate(self):
        rows = [
            {
                "ticket_id": "T1", "customer_id": "C1", "product_sku": "P1", "status": "resolved",
                "created_at_ist": "2026-01-01T10:00+05:30", "resolved_at_ist": "2026-01-01T11:00+05:30",
                "matched_order_id": "O1", "customer_message": "first",
            },
            {
                "ticket_id": "T2", "customer_id": "C1", "product_sku": "P1", "status": "resolved",
                "created_at_ist": "2026-01-10T10:00+05:30", "resolved_at_ist": "2026-01-10T11:00+05:30",
                "matched_order_id": "O1", "customer_message": "return",
            },
            {
                "ticket_id": "T3", "customer_id": "C1", "product_sku": "P1", "status": "resolved",
                "created_at_ist": "2026-02-20T10:00+05:30", "resolved_at_ist": "2026-02-20T11:00+05:30",
                "matched_order_id": "O2", "customer_message": "late",
            },
        ]
        for row in rows:
            row["created_value"] = datetime.fromisoformat(row["created_at_ist"])
            row["resolved_value"] = datetime.fromisoformat(row["resolved_at_ist"])
        pairs = generate_candidate_pairs(rows)
        self.assertEqual([(row["first_ticket_id"], row["return_ticket_id"]) for row in pairs], [("T1", "T2")])
        self.assertTrue(pairs[0]["deterministic_evidence_pass"])


if __name__ == "__main__":
    unittest.main()
