from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .taxonomy import ISSUE_CATEGORIES


@dataclass(frozen=True)
class ModelRequest:
    task: str
    system_prompt: str
    user_prompt: str
    payload: dict[str, Any]
    schema_name: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    usage: dict[str, Any]
    external_api_call: bool


class Provider(Protocol):
    name: str
    model: str

    def complete(self, request: ModelRequest) -> ProviderResponse: ...


OFFLINE_PATTERNS: list[tuple[str, str]] = [
    ("payment_taken_no_order", r"payment.*(?:deducted|debited|through|success).*(?:no order|nothing shows)|money debited.*order"),
    ("duplicate_payment", r"charged.*(?:twice|two times)|double (?:payment|charge)|same amount twice|two entries"),
    ("refund_pending", r"refund.*(?:pending|not received|not credited|delay|promised)|money.*(?:not|hasn't).*back|return.*amount.*nowhere"),
    ("return_pickup", r"pickup.*(?:not|missed|pending)|nobody came.*pickup|packed.*still here|waiting.*courier"),
    ("missing_delivery_tracking", r"not (?:been )?delivered|haven't received.*order|tracking.*(?:stuck|not updating)|marked.*delivered.*nobody|order status.*shipped"),
    ("coupon_discount_failure", r"coupon|promo code|discount.*(?:not|none|applied)|offer.*vanished"),
    ("firmware_update_failure", r"firmware.*(?:stuck|failed|hang)|update.*(?:stuck|failed|dark|won't turn)|progress bar.*not moved"),
    ("app_crash_failure", r"app.*(?:crash|closes|not opening|won't open|white screen|blank screen|loading screen)"),
    ("repair_warranty_status", r"(?:repair|warranty claim|rma).*(?:status|pending|update)|service centre.*silence|sent.*unit.*heard nothing"),
    ("battery_drain", r"battery.*(?:drain|backup|last)|dies by lunchtime|full to empty|charge it twice a day|barely lasts"),
    ("bluetooth_dropouts", r"disconnect|dropout|keeps losing.*phone|connection drops|sound stutters"),
    ("pairing_device_discovery", r"not pairing|cannot pair|can't pair|pairing.*fail|device.*not.*(?:see|discover)|vanishes from.*device list"),
    ("audio_distortion", r"distort|buzzing|crackl|static|\bhiss\b|frying sound|badly tuned radio"),
    ("one_sided_audio", r"one side|left side.*(?:silent|no audio)|right side.*(?:silent|no audio)|one ear.*mute|earbud.*silent"),
    ("charging_case_failure", r"case.*(?:not charging|won't charge|no light|dead)|plugging.*nothing.*case"),
    ("earbud_charging_failure", r"(?:left|right).*earbud.*not charg|(?:left|right) bud.*(?:0%|paperweight|not charg)"),
    ("microphone_failure", r"\bmic\b|microphone|cannot hear me|can't hear me|useless for meetings"),
    ("wrong_item_variant", r"wrong (?:item|product|variant|colour|color)|got something else|different thing"),
    ("transit_damage", r"arrived damaged|damaged in transit|box.*crushed|parcel.*kicked|crack.*out of the box"),
    ("account_login_otp", r"\botp\b|cannot log.?in|can't log.?in|locked out"),
    ("invoice_request", r"invoice|tax bill|gstin"),
    ("order_cancellation", r"cancel.*order|stop the shipment|change of mind"),
    ("address_change", r"change.*address|wrong.*(?:address|pincode)|moved houses"),
    ("wifi_setup", r"wi.?fi.*(?:connect|setup|fail)|network step"),
    ("watch_strap_failure", r"strap|band snapped|pin fell out"),
    ("watch_touch_failure", r"touch.*(?:not|unresponsive)|display.*ignores.*finger"),
    ("speaker_power_failure", r"speaker.*(?:not power|won't turn)|unit dead"),
    ("product_compatibility_enquiry", r"compatible|work with iphone|talk to.*samsung|survive a shower|connect two"),
]


def offline_issue(message: str) -> tuple[str, float, str]:
    text = " ".join(message.lower().split())
    for category, pattern in OFFLINE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            start = max(0, match.start() - 35)
            end = min(len(text), match.end() + 35)
            return category, 0.90, text[start:end]
    return "other", 0.35, text[:120] or "No complaint text supplied."


class OfflineProvider:
    """Free deterministic stand-in that exercises prompts, validation, caching and output flow."""

    name = "offline"

    def __init__(self, model: str = "offline-rules-v1") -> None:
        self.model = model
        self.call_count = 0

    def complete(self, request: ModelRequest) -> ProviderResponse:
        self.call_count += 1
        if request.task == "ticket":
            category, confidence, evidence = offline_issue(request.payload["customer_message"])
            result = {"issue_category": category, "confidence": confidence, "evidence": evidence}
        elif request.task == "pair":
            first_category, first_confidence, first_evidence = offline_issue(request.payload["first_message"])
            return_category, return_confidence, return_evidence = offline_issue(request.payload["return_message"])
            if "other" in {first_category, return_category}:
                result = {
                    "same_issue": None, "issue_category": return_category if return_category != "other" else first_category,
                    "confidence": min(first_confidence, return_confidence),
                    "evidence_from_first": first_evidence, "evidence_from_return": return_evidence,
                    "reason": "Offline mode cannot confidently compare one or both messages.", "uncertain": True,
                }
            else:
                same = first_category == return_category
                result = {
                    "same_issue": same, "issue_category": return_category, "confidence": min(first_confidence, return_confidence),
                    "evidence_from_first": first_evidence, "evidence_from_return": return_evidence,
                    "reason": "Offline development rules produced matching categories." if same else "Offline development rules produced different categories.",
                    "uncertain": False,
                }
        else:
            raise ValueError(f"unsupported task: {request.task}")
        return ProviderResponse(json.dumps(result, ensure_ascii=False), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0}, False)


class OpenAICompatibleProvider:
    """Minimal JSON-schema client for OpenAI-compatible chat-completions APIs."""

    name = "openai_compatible"

    def __init__(self, model: str, api_key: str, base_url: str, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise ValueError("VIREO_AI_API_KEY is required for the openai_compatible provider")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def complete(self, request: ModelRequest) -> ProviderResponse:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": request.schema_name, "strict": True, "schema": request.schema},
            },
        }
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"model API returned HTTP {exc.code}: {detail}") from exc
        content = payload["choices"][0]["message"]["content"]
        raw_usage = payload.get("usage") or {}
        input_tokens = int(raw_usage.get("prompt_tokens", raw_usage.get("input_tokens", 0)) or 0)
        output_tokens = int(raw_usage.get("completion_tokens", raw_usage.get("output_tokens", 0)) or 0)
        input_price = float(os.getenv("VIREO_AI_INPUT_USD_PER_MILLION", "0"))
        output_price = float(os.getenv("VIREO_AI_OUTPUT_USD_PER_MILLION", "0"))
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": int(raw_usage.get("total_tokens", input_tokens + output_tokens) or 0),
            "estimated_cost_usd": (input_tokens * input_price + output_tokens * output_price) / 1_000_000,
        }
        return ProviderResponse(content, usage, True)


def provider_from_env() -> Provider:
    name = os.getenv("VIREO_AI_PROVIDER", "offline").strip().lower()
    if name == "offline":
        return OfflineProvider(os.getenv("VIREO_AI_MODEL", "offline-rules-v1").strip() or "offline-rules-v1")
    if name == "openai_compatible":
        model = os.getenv("VIREO_AI_MODEL", "").strip()
        if not model:
            raise ValueError("VIREO_AI_MODEL is required for the openai_compatible provider")
        return OpenAICompatibleProvider(
            model=model,
            api_key=os.getenv("VIREO_AI_API_KEY", ""),
            base_url=os.getenv("VIREO_AI_BASE_URL", "https://api.openai.com/v1"),
            timeout_seconds=float(os.getenv("VIREO_AI_TIMEOUT_SECONDS", "60")),
        )
    raise ValueError(f"unsupported VIREO_AI_PROVIDER: {name}")
