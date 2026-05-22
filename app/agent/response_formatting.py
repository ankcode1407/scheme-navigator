from __future__ import annotations

from app.agent.case_followup import (
    build_case_followup_summary,
    build_case_verification_notes,
    build_spoken_summary,
    is_case_followup,
)
from app.agent.state import AgentState


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


def format_results(state: AgentState) -> AgentState:
    ctx = state.get("user_context", {})
    case_ctx = state.get("case_context", {})
    schemes = state.get("matched_schemes", [])

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
        state["should_play_tts"] = True
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
        reason = scheme.get("reason", "No reason provided.")
        documents = scheme.get("documents_required", []) or []
        steps = scheme.get("action_steps", []) or []
        portal = scheme.get("portal") or "Not available"
        helpline = scheme.get("helpline") or "Not available"

        lines.append("=" * 50)
        lines.append(f"{index}. {scheme_name}")
        lines.append(f"   Confidence: {confidence}")
        lines.append(f"   Why you qualify: {reason}")

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

    state["response_to_user"] = "\n".join(lines)
    state["response_tts_text"] = build_spoken_summary(
        ctx,
        case_ctx,
        schemes,
        case_followup,
        state["response_to_user"],
    )
    state["should_play_tts"] = True
    return state
