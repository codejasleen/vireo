from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .cache import ResultCache
from .models import (
    PAIR_JSON_SCHEMA,
    TICKET_JSON_SCHEMA,
    ModelResponseError,
    PairClassification,
    TicketClassification,
)
from .providers import ModelRequest, Provider
from .taxonomy import taxonomy_text


PROMPT_VERSION = "vireo-support-v1"
DEFAULT_CONFIDENCE_THRESHOLD = 0.85
T = TypeVar("T", TicketClassification, PairClassification)


def redact_message(value: str, limit: int = 3000) -> str:
    value = re.sub(r"\bVR\d+\b", "[ORDER_ID]", value, flags=re.IGNORECASE)
    value = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", value)
    value = re.sub(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{9}(?!\d)", "[PHONE]", value)
    return value[:limit]


SYSTEM_PROMPT = f"""You classify customer-support complaints for Vireo Audio.
Use the customer's opening message as the primary evidence. Do not trust an existing intake category.
Choose exactly one controlled category. Use other when the actual complaint is unclear or does not fit.
Evidence must be a short exact excerpt from the supplied message. Confidence is a number from 0 to 1.
Return only JSON matching the supplied schema.

Controlled taxonomy:
{taxonomy_text()}"""


PAIR_SYSTEM_PROMPT = f"""You compare two customer-support opening messages for Vireo Audio.
Decide whether they concern the same underlying customer problem, not merely the same customer or product.
Different stages may be different issues: for example, missing delivery and refund pending are not automatically the same complaint.
If the text is vague, conflicting, or insufficient, set uncertain=true and same_issue=null. Never force a decision.
Evidence fields must be short exact excerpts from their respective messages.
Choose one controlled category that best describes the return complaint; use other when unclear.
Return only JSON matching the supplied schema.

Controlled taxonomy:
{taxonomy_text()}"""


@dataclass
class UsageLog:
    logical_requests: int = 0
    provider_calls: int = 0
    external_api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add_usage(self, usage: dict[str, Any]) -> None:
        self.input_tokens += int(usage.get("input_tokens", 0) or 0)
        self.output_tokens += int(usage.get("output_tokens", 0) or 0)
        self.total_tokens += int(usage.get("total_tokens", 0) or 0)
        self.estimated_cost_usd += float(usage.get("estimated_cost_usd", 0) or 0)

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
        }


def _cache_key(provider: Provider, request: ModelRequest) -> str:
    canonical = json.dumps({
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "task": request.task,
        "payload": request.payload,
        "schema": request.schema,
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_evidence(request: ModelRequest, result: TicketClassification | PairClassification) -> None:
    def contains(message: str, evidence: str) -> bool:
        canonical_message = " ".join(message.lower().split())
        canonical_evidence = " ".join(evidence.lower().split())
        return canonical_evidence in canonical_message

    if isinstance(result, TicketClassification):
        if not contains(request.payload["customer_message"], result.evidence):
            raise ModelResponseError("ticket evidence is not an exact excerpt from the supplied message")
        return
    if not contains(request.payload["first_message"], result.evidence_from_first):
        raise ModelResponseError("first-pair evidence is not an exact excerpt from the first message")
    if not contains(request.payload["return_message"], result.evidence_from_return):
        raise ModelResponseError("return-pair evidence is not an exact excerpt from the return message")


class AIClassifier:
    def __init__(self, provider: Provider, cache: ResultCache) -> None:
        self.provider = provider
        self.cache = cache
        self.usage = UsageLog()

    def classify_ticket(self, ticket_id: str, customer_message: str) -> TicketClassification:
        message = redact_message(customer_message)
        request = ModelRequest(
            task="ticket",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps({"ticket_id": ticket_id, "customer_message": message}, ensure_ascii=False),
            payload={"ticket_id": ticket_id, "customer_message": message},
            schema_name="ticket_classification",
            schema=TICKET_JSON_SCHEMA,
        )
        return self._run(request, TicketClassification)

    def classify_pair(
        self, first_ticket_id: str, return_ticket_id: str, first_message: str, return_message: str,
    ) -> PairClassification:
        payload = {
            "first_ticket_id": first_ticket_id,
            "return_ticket_id": return_ticket_id,
            "first_message": redact_message(first_message),
            "return_message": redact_message(return_message),
        }
        request = ModelRequest(
            task="pair",
            system_prompt=PAIR_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            payload=payload,
            schema_name="pair_classification",
            schema=PAIR_JSON_SCHEMA,
        )
        return self._run(request, PairClassification)

    def _run(self, request: ModelRequest, result_type: type[T]) -> T:
        self.usage.logical_requests += 1
        key = _cache_key(self.provider, request)
        cached = self.cache.get(key)
        if cached is not None:
            self.usage.cache_hits += 1
            if cached["error"]:
                raise ModelResponseError(cached["error"])
            result = result_type.from_dict(cached["parsed"])
            _validate_evidence(request, result)
            return result

        self.usage.cache_misses += 1
        response = self.provider.complete(request)
        self.usage.provider_calls += 1
        self.usage.external_api_calls += int(response.external_api_call)
        self.usage.add_usage(response.usage)
        parsed: dict[str, Any] | None = None
        error: str | None = None
        try:
            decoded = json.loads(response.content)
            result = result_type.from_dict(decoded)
            _validate_evidence(request, result)
            parsed = result.as_dict()
        except (json.JSONDecodeError, ModelResponseError) as exc:
            error = str(exc)
            self.cache.put(key, self.provider.name, self.provider.model, request.task, response.content, None, response.usage, error)
            raise ModelResponseError(error) from exc
        self.cache.put(key, self.provider.name, self.provider.model, request.task, response.content, parsed, response.usage, None)
        return result


def decide_pair(
    classification: PairClassification,
    deterministic_evidence_pass: bool,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> str:
    """Deterministic gate; AI output alone never establishes a counted repeat."""
    if not deterministic_evidence_pass:
        return "excluded_deterministic_evidence"
    if classification.uncertain or classification.same_issue is None:
        return "uncertain"
    if classification.confidence < confidence_threshold:
        return "below_confidence_threshold"
    if classification.same_issue is not True:
        return "different_issue"
    return "high_confidence_repeat"
