from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


FOLLOWUP_WORDS = {
    "applied", "application", "rejected", "reject", "pending", "delay", "delayed",
    "status", "not received", "did not receive", "money did not come", "installment",
    "office said", "asked for", "missing document", "missing documents", "complaint",
}

CASE_STATUS_KEYWORDS = {
    "rejected": {"rejected", "reject", "denied", "cancelled", "canceled"},
    "pending": {"pending", "delay", "delayed", "stuck", "under process", "not received", "did not receive"},
    "submitted": {"applied", "submitted", "application done", "form filled"},
}

ROUTING_DATA_PATH = Path(__file__).resolve().parents[1] / "knowledge_base" / "office_routing.json"


@lru_cache(maxsize=1)
def load_office_routing() -> dict[str, dict[str, Any]]:
    with ROUTING_DATA_PATH.open("r", encoding="utf-8") as routing_file:
        data = json.load(routing_file)
    if not isinstance(data, dict) or "default" not in data:
        raise ValueError(f"Invalid office routing data: {ROUTING_DATA_PATH}")
    return data


def infer_case_context_from_text(text: str) -> dict[str, Any]:
    lowered = (text or "").strip().lower()
    if not lowered:
        return {}

    case: dict[str, Any] = {}
    if any(word in lowered for word in FOLLOWUP_WORDS):
        case["next_action"] = "follow_up"

    for status, keywords in CASE_STATUS_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            case["application_status"] = status
            break

    scheme_patterns = [
        r"\b(pm[-\s]?kisan|mgnrega|nrega|ayushman|ration card|scholarship|pension|awas|ujjwala)\b",
        r"\b(?:for|under)\s+([a-z][a-z0-9\s-]{2,40}?)(?:\s+application|\s+scheme|\s+was|\s+is|,|$)",
    ]
    for pattern in scheme_patterns:
        match = re.search(pattern, lowered)
        if match:
            case["scheme_name"] = match.group(1).strip().upper() if match.group(1).startswith("pm") else match.group(1).strip().title()
            break

    reason_match = re.search(
        r"(?:because|reason is|due to|office said|asked for)\s+(.+?)(?:\.|,|$)",
        text,
        flags=re.IGNORECASE,
    )
    if reason_match:
        reason = reason_match.group(1).strip()
        if reason:
            case["rejection_reason"] = reason

    document_words = [
        "aadhaar", "bank", "passbook", "income certificate", "caste certificate",
        "land record", "khasra", "khatauni", "ration card", "residence proof",
        "photo", "marksheet",
    ]
    missing_documents = [doc for doc in document_words if doc in lowered]
    if missing_documents and any(word in lowered for word in ["missing", "asked", "need", "asked for"]):
        case["missing_documents"] = missing_documents

    return {key: value for key, value in case.items() if value}


def is_case_followup(case_ctx: dict, user_text: str = "") -> bool:
    lowered = (user_text or "").lower()
    return bool(
        case_ctx.get("application_status")
        or case_ctx.get("rejection_reason")
        or case_ctx.get("missing_documents")
        or case_ctx.get("next_action") == "follow_up"
        or any(word in lowered for word in FOLLOWUP_WORDS)
    )


def get_office_route(ctx: dict, case_ctx: dict) -> dict[str, Any]:
    category = (ctx.get("problem_category") or "").strip().lower()
    scheme_name = (case_ctx.get("scheme_name") or "").strip().lower()
    if not category:
        if any(name in scheme_name for name in ["mgnrega", "nrega"]):
            category = "employment"
        elif "kisan" in scheme_name:
            category = "agriculture"
        elif "scholarship" in scheme_name:
            category = "education"
        elif "ration" in scheme_name:
            category = "ration"
        elif "pension" in scheme_name:
            category = "pension"
    routing = load_office_routing()
    route = dict(routing.get(category) or routing["default"])
    district = ctx.get("district") or case_ctx.get("district")
    block = ctx.get("block") or case_ctx.get("block")

    place_parts = []
    if block:
        place_parts.append(f"{block} block")
    if district:
        place_parts.append(f"{district} district")
    route["place"] = ", ".join(place_parts) if place_parts else "your block or district"
    route["office_type"] = route["office"]
    return route


def build_case_followup_steps(ctx: dict, case_ctx: dict) -> list[str]:
    route = get_office_route(ctx, case_ctx)
    status = (case_ctx.get("application_status") or "").lower()
    reason = case_ctx.get("rejection_reason")
    missing_docs = case_ctx.get("missing_documents") or []

    steps = []
    if status == "rejected":
        steps.append("Ask for the rejection reason in writing or as a portal screenshot.")
    elif status == "pending":
        steps.append("Ask where the application is stuck: CSC, block, district, bank, or department verification.")
    elif status == "submitted":
        steps.append("Keep the application ID/receipt ready and check the official status before visiting.")
    else:
        steps.append("First confirm the application ID and current status.")

    if reason:
        steps.append(f"Verify this reason: {reason}.")
    elif missing_docs:
        steps.append(f"Carry or correct these documents: {', '.join(missing_docs)}.")
    else:
        steps.append("Ask exactly which document or eligibility point is blocking the application.")

    steps.append(f"Go to {route['office']} in {route['place']} and ask for {route['ask']}.")
    return steps


def build_case_followup_summary(ctx: dict, case_ctx: dict) -> str:
    route = get_office_route(ctx, case_ctx)
    status = case_ctx.get("application_status")
    scheme = case_ctx.get("scheme_name")
    reason = case_ctx.get("rejection_reason")
    missing_docs = case_ctx.get("missing_documents") or []
    carry_docs = route.get("documents", [])

    lines = ["This looks like an application follow-up, not a fresh scheme search."]
    if scheme:
        lines.append(f"Scheme/application: {scheme}")
    if status:
        lines.append(f"Current status: {status}")
    if reason:
        lines.append(f"Reason to verify: {reason}")
    if missing_docs:
        lines.append(f"Documents mentioned: {', '.join(missing_docs)}")

    lines.append("")
    lines.append(f"Where to go: {route['office']} in {route['place']}.")
    lines.append(f"What to ask: {route['ask']}.")
    lines.append(f"What to carry: {', '.join(carry_docs)}.")
    lines.append("")
    lines.append("Do this next:")
    for step in build_case_followup_steps(ctx, case_ctx):
        lines.append(f"- {step}")

    if not (ctx.get("district") or case_ctx.get("district")):
        lines.append("- Share the district next so I can make the office guidance more local.")

    return "\n".join(lines)


def build_case_verification_notes(ctx: dict, case_ctx: dict) -> list[str]:
    route = get_office_route(ctx, case_ctx)
    notes = [
        "Verify the application ID or receipt number before visiting.",
        "Verify whether the problem is with documents, eligibility, bank/Aadhaar seeding, or department approval.",
        f"Verify the status at {route['office']} in {route['place']} if the portal/CSC answer is unclear.",
    ]
    if not (ctx.get("district") or case_ctx.get("district")):
        notes.append("Share the district to identify the nearest office path.")
    return notes[:3]


def build_spoken_summary(
    ctx: dict,
    case_ctx: dict,
    schemes: list[dict],
    case_followup: bool,
    fallback_text: str,
) -> str:
    if case_followup:
        route = get_office_route(ctx, case_ctx)
        steps = build_case_followup_steps(ctx, case_ctx)
        scheme = case_ctx.get("scheme_name")
        status = case_ctx.get("application_status")

        parts = ["This is an application follow-up."]
        if scheme:
            parts.append(f"For {scheme}.")
        if status:
            parts.append(f"The current status is {status}.")
        parts.append(f"Go to {route['office']} in {route['place']}.")
        parts.append(f"Ask for {route['ask']}.")
        if steps:
            parts.append(f"First step: {steps[0]}")
        if not (ctx.get("district") or case_ctx.get("district")):
            parts.append("Share the district to make this office guidance more local.")
        return " ".join(parts)

    if schemes:
        first = schemes[0]
        scheme_name = first.get("scheme_name") or first.get("name") or "the first scheme"
        steps = first.get("action_steps") or []

        match_word = "match" if len(schemes) == 1 else "matches"
        parts = [f"I found {len(schemes)} possible scheme {match_word}."]
        parts.append(f"The first option is {scheme_name}.")
        if steps:
            parts.append(f"Next step: {steps[0]}")
        elif ctx.get("district"):
            parts.append(f"Use the local CSC or department office in {ctx.get('district')} for help.")
        else:
            parts.append("Share your district next so I can tell you the local office path.")

        if first.get("confidence") == "NEEDS_VERIFICATION":
            parts.append("Before applying, verify eligibility, documents, and whether the scheme is active.")
        return " ".join(parts)

    return " ".join(str(fallback_text or "").split())[:700]
