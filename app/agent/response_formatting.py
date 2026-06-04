from __future__ import annotations

from app.agent.case_followup import (
    build_case_followup_summary,
    build_case_verification_notes,
    build_spoken_summary,
    is_case_followup,
)
from app.agent.state import AgentState



def _derive_documents(scheme: dict) -> list[str]:
    """Build a document list from structured eligibility fields when documents_required is empty."""
    docs = list(scheme.get("documents_required") or [])
    if docs:
        return docs

    eligibility = scheme.get("eligibility") or {}
    derived: list[str] = []

    if scheme.get("requires_aadhaar") or eligibility.get("requires_aadhaar"):
        derived.append("Aadhaar card")
    if scheme.get("requires_bank_account") or eligibility.get("requires_bank_account"):
        derived.append("Bank passbook / account details")

    castes = eligibility.get("caste") or []
    if castes and any(c.lower() not in ("", "all") for c in castes):
        derived.append("Caste certificate")

    income_cat = eligibility.get("income_category") or ""
    max_income = eligibility.get("max_annual_income")
    if income_cat or max_income:
        derived.append("Income certificate")

    gender = eligibility.get("gender") or ""
    if gender.lower() == "female":
        derived.append("Gender proof (if required)")

    if not derived:
        derived.append("Identity proof + Address proof (confirm at office)")

    return derived


def _derive_steps(scheme: dict, ctx: dict) -> list[str]:
    """Build action steps from application_mode, portal, and context."""
    steps: list[str] = list(scheme.get("action_steps") or [])
    if steps:
        return steps

    mode = (scheme.get("application_mode") or "").lower()
    portal = scheme.get("portal") or ""
    district = ctx.get("district") or ""
    state = ctx.get("state") or ""
    location = district or state

    if mode == "online":
        derived = [f"Apply online at {portal}" if portal else "Apply online via the official portal."]
        derived.append("Keep scanned copies of all documents ready before starting the form.")
        derived.append("Save the acknowledgement number after submission.")
    elif mode == "offline":
        office = f"the nearest block/district office{(' in ' + location) if location else ''}"
        derived = [f"Visit {office} with all required documents."]
        derived.append("Ask for the scheme application form by name at the counter.")
        derived.append("Collect a receipt after submission and note the contact number for follow-up.")
    else:
        derived = [
            f"Check the official portal{(' at ' + portal) if portal else ''} to confirm application mode.",
            f"Visit the nearest CSC or block office{(' in ' + location) if location else ''} for offline guidance.",
        ]

    return derived


def _build_reason(scheme: dict) -> str:
    """Return a concise reason line combining match reason with benefit summary."""
    reason = (scheme.get("reason") or "").strip()
    benefit = (scheme.get("benefit") or "").strip()

    if reason and benefit:
        return f"{reason} — Benefit: {benefit}"
    return reason or benefit or "Potentially relevant to your profile."


def build_verification_notes(scheme: dict, ctx: dict) -> list[str]:
    notes: list[str] = []
    district = ctx.get("district")
    state = ctx.get("state")

    notes.append("Confirm whether the scheme is currently active on the official portal.")
    if state:
        notes.append(f"Verify that the scheme applies in {state}.")
    if district:
        notes.append(f"Verify the correct district/block office or CSC for {district}.")
    notes.append("Check the latest document list and application mode before visiting.")
    return notes[:3]


def _mark_dynamic_response(state: AgentState) -> None:
    state["response_language"] = (
        state.get("preferred_language")
        or state.get("user_language")
        or "en-IN"
    )
    state["response_source_language"] = "en-IN"
    state["should_play_tts"] = True


def format_results(state: AgentState) -> AgentState:
    ctx = state.get("user_context", {})
    case_ctx = state.get("case_context", {})
    schemes = state.get("matched_schemes", [])

    if state.get("is_low_confidence"):
        clarification_text = (
            "I'm not completely sure what you are looking for. Please tap one of the options below to clarify:\n\n"
            "[CLARIFICATION_CHIPS]: farming or crop support | employment or self-employment | education or scholarship | livestock or dairy | pension or elderly support | women-specific schemes"
        )
        state["response_to_user"] = clarification_text
        state["response_tts_text"] = "I am not completely sure what you are looking for. Please choose one of the options below to clarify."
        _mark_dynamic_response(state)
        return state

    application_status = (case_ctx.get("application_status") or "").strip().lower()
    rejection_reason = (case_ctx.get("rejection_reason") or "").strip()
    case_followup = is_case_followup(case_ctx, state.get("user_input", ""))

    if not schemes:
        if case_followup:
            state["response_to_user"] = build_case_followup_summary(ctx, case_ctx)
        elif not ctx.get("state"):
            state["response_to_user"] = (
                "I understand the problem, but I still need your state to narrow down the correct scheme. "
                "Please tell me which state you are in."
            )
        else:
            state["response_to_user"] = (
                "I could not find a strong match from the available scheme data. "
                "Please share one more detail, such as your district, occupation, or the exact document/application issue."
            )

        if not case_followup and (application_status or rejection_reason):
            extra = []
            if application_status:
                extra.append(f"Application status: {application_status}.")
            if rejection_reason:
                extra.append(f"Rejection reason: {rejection_reason}.")
            state["response_to_user"] += "\n\n" + " ".join(extra)

        state["response_tts_text"] = build_spoken_summary(
            ctx,
            case_ctx,
            [],
            case_followup,
            state["response_to_user"],
        )
        _mark_dynamic_response(state)
        return state

    if case_followup:
        lines = [
            build_case_followup_summary(ctx, case_ctx),
            "",
            f"Relevant scheme context ({len(schemes)} possible match(es)):\n",
        ]
    else:
        lines = [f"I found {len(schemes)} scheme(s) that may fit your situation:\n"]

        if not case_followup and (application_status or rejection_reason):
            lines.append("This looks like a follow-up on an existing application.")
            if application_status:
                lines.append(f"Current status: {application_status}")
            if rejection_reason:
                lines.append(f"Rejection reason: {rejection_reason}")
            if case_ctx.get("missing_documents"):
                lines.append(f"Missing documents: {', '.join(case_ctx.get('missing_documents', []))}")
            lines.append("Next step: verify the exact missing requirement, then re-apply or escalate through the correct office.\n")

    for index, scheme in enumerate(schemes, 1):
        scheme_name = scheme.get("scheme_name") or scheme.get("name") or "Unknown Scheme"
        confidence = scheme.get("confidence", "NEEDS_VERIFICATION")
        reason = _build_reason(scheme)
        
        # --- NEW: Extracting the Audit Data ---
        passed_criteria = scheme.get("passed_criteria", [])
        failed_criteria = scheme.get("failed_criteria", [])
        missing_data = scheme.get("missing_data", [])
        # --------------------------------------

        documents = _derive_documents(scheme)
        steps = _derive_steps(scheme, ctx)
        portal = scheme.get("portal") or "Not available"
        helpline = scheme.get("helpline") or "Not available"

        lines.append("=" * 50)
        scheme_id = scheme.get("scheme_id") or ""
        if scheme_id:
            lines.append(f"   ID: {scheme_id}")
        lines.append(f"{index}. {scheme_name}")
        lines.append(f"   Reason: {reason}")
        
        # --- NEW: Formatting the Audit Data for the Frontend Parser ---
        if passed_criteria:
            lines.append("\n   Passed:")
            for p in passed_criteria:
                lines.append(f"   + {p}")
                
        if failed_criteria:
            lines.append("\n   Failed:")
            for f in failed_criteria:
                lines.append(f"   - {f}")
                
        if missing_data:
            lines.append("\n   Missing:")
            for m in missing_data:
                lines.append(f"   > {m}")
        # --------------------------------------------------------------

        lines.append("\n   Documents needed:")
        if documents:
            for document in documents:
                lines.append(f"   - {document}")
        else:
            lines.append("   - Not specified")

        lines.append("\n   What to do now:")
        if steps:
            for step in steps:
                lines.append(f"   -> {step}")
        else:
            lines.append("   -> Check the official portal and verify eligibility with the department or CSC.")

        if case_followup:
            lines.append("\n   What to verify:")
            for note in build_case_verification_notes(ctx, case_ctx):
                lines.append(f"   -> {note}")
        elif confidence == "NEEDS_VERIFICATION":
            lines.append("\n   What to verify:")
            for note in build_verification_notes(scheme, ctx):
                lines.append(f"   -> {note}")

        lines.append(f"\n   Portal: {portal}")
        lines.append(f"   Helpline: {helpline}\n")

    if not ctx.get("district") and not case_followup:
        lines.append("If you share your district next, I can narrow down the local office path more precisely.")

    if state.get("training_centre_clarification"):
        lines.append("")
        lines.append(state["training_centre_clarification"])

    state["response_to_user"] = "\n".join(lines)
    state["response_tts_text"] = build_spoken_summary(
        ctx,
        case_ctx,
        schemes,
        case_followup,
        state["response_to_user"],
    )
    _mark_dynamic_response(state)
    return state