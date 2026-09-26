from __future__ import annotations


TAXONOMY: dict[str, str] = {
    "missing_delivery_tracking": "Order not received, falsely marked delivered, or tracking stalled.",
    "pairing_device_discovery": "Device cannot pair or is not visible for pairing.",
    "refund_pending": "A promised or processed refund has not reached the customer.",
    "return_pickup": "Return or reverse pickup was missed, delayed, or not scheduled.",
    "payment_taken_no_order": "Payment succeeded but no order was created or confirmed.",
    "battery_drain": "Battery drains unusually quickly or runtime is far below expectation.",
    "bluetooth_dropouts": "An established Bluetooth connection repeatedly drops or stutters.",
    "audio_distortion": "Buzzing, crackling, static, hiss, or distorted audio.",
    "coupon_discount_failure": "Coupon, promotion, or promised discount was not applied.",
    "app_crash_failure": "Vireo app crashes, closes, shows a blank screen, or will not open.",
    "repair_warranty_status": "Customer asks for progress on an RMA, repair, or warranty claim.",
    "firmware_update_failure": "Firmware update is stuck, failed, or left the device unusable.",
    "wrong_item_variant": "Customer received the wrong item, model, colour, or variant.",
    "transit_damage": "Product or package arrived physically damaged.",
    "one_sided_audio": "Audio is absent from one side or one earbud.",
    "charging_case_failure": "Charging case does not charge, light up, or retain charge.",
    "earbud_charging_failure": "One earbud does not charge in the case.",
    "duplicate_payment": "Customer was charged twice for one purchase.",
    "microphone_failure": "Microphone is inaudible, quiet, or unusable on calls.",
    "account_login_otp": "Login, account access, or OTP delivery problem.",
    "invoice_request": "Invoice, tax invoice, or GST document request.",
    "order_cancellation": "Request to cancel an order before fulfilment.",
    "address_change": "Request to correct or change delivery address or postcode.",
    "product_compatibility_enquiry": "Question about compatibility, specifications, or intended use.",
    "watch_strap_failure": "Watch or band strap, clasp, or pin failure.",
    "watch_touch_failure": "Watch display or touch input is unresponsive.",
    "wifi_setup": "Smart speaker cannot connect to Wi-Fi or complete network setup.",
    "speaker_power_failure": "Speaker does not power on.",
    "other": "Complaint is unclear or does not fit another controlled category.",
}

ISSUE_CATEGORIES = frozenset(TAXONOMY)


def taxonomy_text() -> str:
    return "\n".join(f"- {key}: {description}" for key, description in TAXONOMY.items())

