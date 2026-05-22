from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from app.agent.case_followup import build_case_followup_steps, is_case_followup
from app.agent.models import SchemeCandidate, SchemeMatch
from app.agent.state import AgentState
from app.knowledge_base.scheme_loader import load_schemes


def dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


def to_candidate(raw: dict) -> SchemeCandidate:
    return SchemeCandidate(
        scheme_id=raw.get("scheme_id") or raw.get("id", ""),
        scheme_name=raw.get("scheme_name") or raw.get("name", "Unknown Scheme"),
        category=raw.get("category", []) or [],
        eligibility=raw.get("eligibility", {}) or {},
        benefit=raw.get("benefit", "") or "",
        documents_required=raw.get("documents_required", []) or [],
        portal=raw.get("portal", "") or "",
        helpline=raw.get("helpline", "") or "",
        application_mode=raw.get("application_mode", "") or "",
        state=raw.get("state", []) or [],
        tags=raw.get("tags", []) or [],
        brief_description=raw.get("brief_description", "") or raw.get("description", "") or "",
        close_date=raw.get("close_date"),
    )


def scheme_text(scheme: dict) -> str:
    parts = [
        scheme.get("scheme_name", ""),
        scheme.get("brief_description", ""),
        scheme.get("description", ""),
        " ".join(scheme.get("tags", []) or []),
        " ".join(scheme.get("category", []) or []),
        " ".join(scheme.get("state", []) or []),
        " ".join(scheme.get("documents_required", []) or []),
    ]
    return " ".join(str(part) for part in parts if part)


def is_closed_scheme(scheme: dict) -> bool:
    close_date = scheme.get("close_date")
    if not close_date:
        return False
    try:
        if isinstance(close_date, str):
            return datetime.strptime(close_date[:10], "%Y-%m-%d").date() < date.today()
    except Exception:
        return False
    return False


def score_scheme(scheme: dict, ctx: dict, case_ctx: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    text = scheme_text(scheme).lower()
    eligibility = scheme.get("eligibility", {}) or {}

    problem_blob = " ".join(
        str(ctx.get(key, "") or "") for key in [
            "problem_statement",
            "specific_problem",
            "problem_category",
        ]
    ).lower()

    occupation = (ctx.get("occupation") or "").lower().strip()
    user_state = (ctx.get("state") or ctx.get("district_state") or "").lower().strip()
    residence = (ctx.get("residence") or "").lower().strip()
    category = (ctx.get("problem_category") or "").lower().strip()

    case_status = (case_ctx.get("application_status") or "").lower().strip()
    rejection_reason = (case_ctx.get("rejection_reason") or "").lower().strip()

    if case_status or rejection_reason:
        if any(word in problem_blob for word in ["reject", "pending", "delay", "application", "status"]):
            score += 2
            reasons.append("matches your application follow-up issue")

    scheme_states = [str(state).lower().strip() for state in (scheme.get("state") or [])]
    eligibility_states = [str(state).lower().strip() for state in (eligibility.get("state") or []) if state]

    if user_state and (scheme_states or eligibility_states):
        allowed_states = scheme_states or eligibility_states
        if not any(
            state == "all" or user_state == state or user_state in state or state in user_state
            for state in allowed_states
        ):
            return -999, ["state mismatch"]
        score += 4
        reasons.append(f"available in {ctx.get('state')}")
    elif scheme_states or eligibility_states:
        score += 1

    scheme_occ = [str(occ).lower().strip() for occ in (eligibility.get("occupation") or []) if occ]
    if occupation and scheme_occ:
        if any(occupation == occ or occupation in occ or occ in occupation for occ in scheme_occ):
            score += 4
            reasons.append(f"fits your role as {ctx.get('occupation')}")
        else:
            if len(scheme_occ) <= 2:
                return -999, ["occupation mismatch"]

    scheme_res = str(eligibility.get("residence") or "").lower().strip()
    if residence and scheme_res:
        if scheme_res in {"both", ""}:
            score += 1
        elif scheme_res == residence:
            score += 2
            reasons.append(f"matches {residence} residence")
        else:
            return -999, ["residence mismatch"]

    if eligibility.get("requires_aadhaar") is True and ctx.get("has_aadhaar") is False:
        return -999, ["aadhaar required but missing"]

    if eligibility.get("requires_bank_account") is True and ctx.get("has_bank_account") is False:
        return -999, ["bank account required but missing"]

    category_text = " ".join((scheme.get("category") or []) or []).lower()
    tags_text = " ".join((scheme.get("tags") or []) or []).lower()

    category_keywords = {
        "agriculture": ["agriculture", "farm", "farmer", "seed", "crop", "livestock", "fisher", "fish"],
        "education": ["education", "student", "scholarship", "school", "college"],
        "employment": ["employment", "skill", "job", "startup", "business"],
        "health": ["health", "medical", "hospital"],
        "housing": ["housing", "shelter", "sanitation", "toilet"],
        "ration": ["ration", "food"],
        "women_child": ["women", "child", "girl", "mother"],
        "pension": ["pension", "old age", "widow"],
        "disability": ["disability", "pwd", "disabled"],
        "documents": ["aadhaar", "bank", "ration card", "document"],
        "water": ["water", "irrigation", "pump", "well"],
        "fisheries": ["fish", "fisher", "boat", "net"],
        "debt": ["loan", "finance", "credit", "subsidy"],
    }

    if category and category in category_keywords:
        if any(
            keyword in text or keyword in problem_blob or keyword in category_text or keyword in tags_text
            for keyword in category_keywords[category]
        ):
            score += 4
            reasons.append(f"aligned with your {category.replace('_', ' ')} problem")

    overlap_words = set(problem_blob.split()) & set((tags_text + " " + category_text + " " + text).split())
    if overlap_words:
        score += min(3, len(overlap_words))
        reasons.append("shares keywords with your problem")

    if not reasons and problem_blob:
        if any(word in text for word in problem_blob.split()[:4]):
            score += 1

    return score, reasons


def confidence_from_score(score: int) -> str:
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "LIKELY"
    return "NEEDS_VERIFICATION"


def make_action_steps(scheme: dict, ctx: dict, case_ctx: dict) -> list[str]:
    steps: list[str] = []

    app_mode = (scheme.get("application_mode") or "").lower().strip()
    district = ctx.get("district")
    state = ctx.get("state")

    if is_case_followup(case_ctx):
        return build_case_followup_steps(ctx, case_ctx)
    if case_ctx.get("application_status") in {"rejected", "pending"}:
        steps.append("Check the rejection or pending reason and compare it with the official eligibility rules.")
    elif app_mode == "offline":
        steps.append("Visit the nearest CSC, block office, or department office for offline submission.")
    elif app_mode == "online":
        steps.append("Apply through the official portal.")
    elif app_mode == "csc":
        steps.append("Use your nearest CSC for application support.")
    else:
        steps.append("Check the official portal or local office for the application process.")

    if district:
        steps.append(f"Use your district-level office or CSC in {district} for local help.")
    elif state:
        steps.append(f"Keep proof of residence in {state} ready if the scheme is state-specific.")
    else:
        steps.append("Share your state next so I can narrow down the correct local office.")

    if ctx.get("problem_category") == "documents":
        steps.append("Verify Aadhaar, bank account, and ration card details first.")

    return steps[:3]


def filter_candidates(all_schemes: list[dict]) -> list[SchemeCandidate]:
    candidates: list[SchemeCandidate] = []
    for scheme in all_schemes:
        if is_closed_scheme(scheme):
            continue
        try:
            candidates.append(to_candidate(scheme))
        except ValidationError:
            continue
    return candidates


def match_schemes(state: AgentState) -> AgentState:
    all_schemes = load_schemes()
    ctx = state.get("user_context", {})
    case_ctx = state.get("case_context", {})

    candidates = filter_candidates(all_schemes)

    scored: list[tuple[int, dict, list[str]]] = []
    for candidate in candidates:
        raw = dump_model(candidate)
        score, reasons = score_scheme(raw, ctx, case_ctx)
        if score > 0:
            scored.append((score, raw, reasons))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:8]

    matches: list[SchemeMatch] = []
    for score, raw, reasons in top:
        match = SchemeMatch(
            scheme_id=raw.get("scheme_id", ""),
            scheme_name=raw.get("scheme_name", "Unknown Scheme"),
            confidence=confidence_from_score(score),
            reason="; ".join(reasons) if reasons else "This scheme appears relevant based on the available details.",
            documents_required=raw.get("documents_required", []) or [],
            action_steps=make_action_steps(raw, ctx, case_ctx),
            portal=raw.get("portal") or None,
            helpline=raw.get("helpline") or None,
        )
        matches.append(match)

    if not matches:
        fallback = []
        for candidate in candidates[:5]:
            raw = dump_model(candidate)
            fallback.append(
                SchemeMatch(
                    scheme_id=raw.get("scheme_id", ""),
                    scheme_name=raw.get("scheme_name", "Unknown Scheme"),
                    confidence="NEEDS_VERIFICATION",
                    reason="I could not confirm a strong match yet. Share your state or more details so I can narrow it down.",
                    documents_required=raw.get("documents_required", []) or [],
                    action_steps=make_action_steps(raw, ctx, case_ctx),
                    portal=raw.get("portal") or None,
                    helpline=raw.get("helpline") or None,
                )
            )
        matches = fallback

    state["matched_schemes"] = [dump_model(match) for match in matches]
    return state
