from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .taxonomy import ISSUE_CATEGORIES


class ModelResponseError(ValueError):
    pass


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelResponseError("model response must be a JSON object")
    return value


def _exact_fields(data: dict[str, Any], fields: set[str]) -> None:
    missing = fields - set(data)
    extra = set(data) - fields
    if missing or extra:
        raise ModelResponseError(f"response fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")


def _string(data: dict[str, Any], field: str, allow_empty: bool = False) -> str:
    value = data.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ModelResponseError(f"{field} must be a non-empty string")
    return value.strip()


def _confidence(data: dict[str, Any]) -> float:
    value = data.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelResponseError("confidence must be a number")
    value = float(value)
    if not 0 <= value <= 1:
        raise ModelResponseError("confidence must be between 0 and 1")
    return value


def _category(data: dict[str, Any]) -> str:
    value = _string(data, "issue_category")
    if value not in ISSUE_CATEGORIES:
        raise ModelResponseError(f"unknown issue_category: {value}")
    return value


@dataclass(frozen=True)
class TicketClassification:
    issue_category: str
    confidence: float
    evidence: str

    @classmethod
    def from_dict(cls, value: Any) -> "TicketClassification":
        data = _object(value)
        _exact_fields(data, {"issue_category", "confidence", "evidence"})
        return cls(_category(data), _confidence(data), _string(data, "evidence"))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PairClassification:
    same_issue: bool | None
    issue_category: str
    confidence: float
    evidence_from_first: str
    evidence_from_return: str
    reason: str
    uncertain: bool

    @classmethod
    def from_dict(cls, value: Any) -> "PairClassification":
        data = _object(value)
        _exact_fields(data, {"same_issue", "issue_category", "confidence", "evidence_from_first", "evidence_from_return", "reason", "uncertain"})
        same_issue = data.get("same_issue")
        if same_issue is not None and not isinstance(same_issue, bool):
            raise ModelResponseError("same_issue must be true, false, or null")
        uncertain = data.get("uncertain")
        if not isinstance(uncertain, bool):
            raise ModelResponseError("uncertain must be a boolean")
        if uncertain and same_issue is not None:
            raise ModelResponseError("an uncertain result must set same_issue=null")
        if not uncertain and same_issue is None:
            raise ModelResponseError("a non-uncertain result must decide same_issue")
        return cls(
            same_issue=same_issue,
            issue_category=_category(data),
            confidence=_confidence(data),
            evidence_from_first=_string(data, "evidence_from_first"),
            evidence_from_return=_string(data, "evidence_from_return"),
            reason=_string(data, "reason"),
            uncertain=uncertain,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


TICKET_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["issue_category", "confidence", "evidence"],
    "properties": {
        "issue_category": {"type": "string", "enum": sorted(ISSUE_CATEGORIES)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence": {"type": "string", "minLength": 1},
    },
}

PAIR_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["same_issue", "issue_category", "confidence", "evidence_from_first", "evidence_from_return", "reason", "uncertain"],
    "properties": {
        "same_issue": {"type": ["boolean", "null"]},
        "issue_category": {"type": "string", "enum": sorted(ISSUE_CATEGORIES)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence_from_first": {"type": "string", "minLength": 1},
        "evidence_from_return": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "minLength": 1},
        "uncertain": {"type": "boolean"},
    },
}
