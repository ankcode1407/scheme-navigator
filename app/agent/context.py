from __future__ import annotations

import re
from typing import Any, Optional

from app.agent.constants import (
    PROBLEM_CATEGORY_KEYWORDS,
    RURAL_WORDS,
    STATE_PREFIXES_TO_STRIP,
    URBAN_WORDS,
)


def normalize_boolish(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "y", "haan", "ha"}:
        return True
    if text in {"no", "false", "0", "n", "nahin", "na"}:
        return False
    return None


def normalize_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def normalize_occupation(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().lower()
    occupation_map = {
        "farmer": "farmer",
        "agriculture": "farmer",
        "kisan": "farmer",
        "kisaan": "farmer",
        "krishak": "farmer",
        "student": "student",
        "studying": "student",
        "worker": "daily wage worker",
        "labourer": "daily wage worker",
        "labor": "daily wage worker",
        "labour": "daily wage worker",
        "mazdoor": "daily wage worker",
        "majdoor": "daily wage worker",
        "vendor": "vendor",
        "hawker": "vendor",
        "rehri": "vendor",
        "shopkeeper": "vendor",
        "business": "small business owner",
        "businessman": "small business owner",
        "vyapari": "small business owner",
        "trader": "small business owner",
        "self employed": "self-employed",
        "selfemployed": "self-employed",
        "unemployed": "unemployed",
        "jobless": "unemployed",
        "berozgar": "unemployed",
        "fisherman": "fisherman",
        "fisher": "fisherman",
        "machhua": "fisherman",
        "machera": "fisherman",
        "artisan": "artisan",
        "karigar": "artisan",
        "craftsman": "artisan",
        "teacher": "teacher",
        "doctor": "doctor",
        "nurse": "nurse",
        "engineer": "engineer",
        "driver": "driver",
    }
    if text in occupation_map:
        return occupation_map[text]
    for k, v in occupation_map.items():
        if k in text:
            return v
    return value.strip().lower()


def normalize_state(value: str | None) -> str | None:
    if not value:
        return None
    state = value.strip().lower()
    for prefix in STATE_PREFIXES_TO_STRIP:
        if state.startswith(prefix):
            state = state[len(prefix):].strip()
    state = re.sub(r"^\b(in|at|of)\b\s+", "", state).strip()
    if not state:
        return None
    return state.title()


def normalize_residence(value: str | None) -> str | None:
    if not value:
        return None
    residence = value.strip().lower()
    if any(word in residence for word in RURAL_WORDS):
        return "rural"
    if any(word in residence for word in URBAN_WORDS):
        return "urban"
    return residence


def normalize_problem_category(value: str | None, blob: str = "") -> str | None:
    if value:
        normalized = value.strip().lower()
        canonical = {
            "agriculture": "agriculture",
            "agri": "agriculture",
            "farming": "agriculture",
            "education": "education",
            "employment": "employment",
            "job": "employment",
            "health": "health",
            "housing": "housing",
            "ration": "ration",
            "women": "women_child",
            "child": "women_child",
            "pension": "pension",
            "disability": "disability",
            "documents": "documents",
            "water": "water",
            "fisheries": "fisheries",
            "debt": "debt",
            "loan": "debt",
        }
        if normalized in canonical:
            return canonical[normalized]
        for key, mapped in canonical.items():
            if key in normalized:
                return mapped

  lowered = (blob or "").lower()
    for category, keywords in PROBLEM_CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def infer_problem_statement_from_context(ctx: dict) -> Optional[str]:
    problem_category = (ctx.get("problem_category") or "").lower()
    occupation = (ctx.get("occupation") or "").lower()

    if occupation == "unemployed" or problem_category == "employment":
        return "Looking for employment or livelihood support"
    if occupation == "student" or problem_category == "education":
        return "Need education or scholarship support"
    if occupation == "farmer" or problem_category == "agriculture":
        return "Need agriculture or farming support"
    if problem_category == "ration":
        return "Need ration or food support"
    if problem_category == "health":
        return "Need health support"
    if problem_category == "housing":
        return "Need housing or shelter support"
    if problem_category == "pension":
        return "Need pension support"
    if problem_category == "documents":
        return "Need help with documents or verification"
    if problem_category == "debt":
        return "Need help with loan or debt support"
    return None


def infer_user_context_from_text(text: str) -> dict[str, Any]:
    lowered = (text or "").strip().lower()
    if not lowered:
        return {}

    inferred: dict[str, Any] = {}
    bare_occupation_words = {"farmer", "kisan", "kisaan", "student", "unemployed", "jobless"}
    occupation = normalize_occupation(lowered)
    category = normalize_problem_category(None, lowered)

    if occupation and occupation != lowered:
        inferred["occupation"] = occupation
    elif lowered in bare_occupation_words:
        inferred["occupation"] = normalize_occupation(lowered)

    if category:
        inferred["problem_category"] = category

    if any(word in lowered for word in ["reject", "pending", "delay", "application", "status"]):
        inferred["problem_statement"] = text.strip()
    elif category and lowered not in bare_occupation_words:
        inferred["problem_statement"] = text.strip()
    elif inferred.get("occupation"):
        inferred["problem_statement"] = infer_problem_statement_from_context(inferred)

    state_match = re.search(
        r"\b(?:from|in|main|mein|live in)\s+([a-z][a-z\s]+?)(?:\s+mein|\s+me|\s+i|\s+with|,|$)",
        lowered,
    )
    if state_match:
        maybe_state = normalize_state(state_match.group(1))
        if maybe_state and len(maybe_state) <= 40:
            inferred["state"] = maybe_state

    if any(word in lowered for word in RURAL_WORDS | URBAN_WORDS):
        inferred["residence"] = normalize_residence(lowered)

    land = normalize_number(lowered) if any(word in lowered for word in ["hectare", "acre", "zameen", "land"]) else None
    if land is not None:
        inferred["land_hectares"] = land

    return {key: value for key, value in inferred.items() if value is not None}


def normalize_user_context(context: dict) -> dict:
    ctx = dict(context)

    if "problem_statement" in ctx and ctx.get("problem_statement"):
        ctx["problem_statement"] = str(ctx["problem_statement"]).strip()

    if "problem_category" in ctx:
        ctx["problem_category"] = normalize_problem_category(
            ctx.get("problem_category"),
            ctx.get("problem_statement", "") or "",
        )

    if "specific_problem" in ctx and ctx.get("specific_problem"):
        ctx["specific_problem"] = str(ctx["specific_problem"]).strip()

    if "occupation" in ctx:
        ctx["occupation"] = normalize_occupation(ctx.get("occupation"))
    if "state" in ctx:
        ctx["state"] = normalize_state(ctx.get("state"))
    if "district" in ctx and ctx.get("district"):
        ctx["district"] = str(ctx["district"]).strip().title()
    if "block" in ctx and ctx.get("block"):
        ctx["block"] = str(ctx["block"]).strip().title()
    if "residence" in ctx:
        ctx["residence"] = normalize_residence(ctx.get("residence"))
    if "land_hectares" in ctx:
        ctx["land_hectares"] = normalize_number(ctx.get("land_hectares"))
    if "family_size" in ctx:
        family_size = normalize_number(ctx.get("family_size"))
        ctx["family_size"] = int(family_size) if family_size is not None else None
    if "has_aadhaar" in ctx:
        ctx["has_aadhaar"] = normalize_boolish(ctx.get("has_aadhaar"))
    if "has_bank_account" in ctx:
        ctx["has_bank_account"] = normalize_boolish(ctx.get("has_bank_account"))
    if "has_ration_card" in ctx:
        ctx["has_ration_card"] = normalize_boolish(ctx.get("has_ration_card"))

    if not ctx.get("problem_statement"):
        inferred = infer_problem_statement_from_context(ctx)
        if inferred:
            ctx["problem_statement"] = inferred

    if not ctx.get("problem_category") and ctx.get("problem_statement"):
        ctx["problem_category"] = normalize_problem_category(None, ctx.get("problem_statement") or "")

    return ctx


def normalize_case_context(context: dict) -> dict:
    ctx = dict(context)

    for key in ["case_id", "scheme_id", "scheme_name", "rejection_reason", "last_followup_date", "next_action"]:
        if key in ctx and ctx.get(key):
            ctx[key] = str(ctx[key]).strip()

    if "application_status" in ctx and ctx.get("application_status"):
        ctx["application_status"] = str(ctx["application_status"]).strip().lower()

    if "missing_documents" in ctx:
        missing_documents = ctx.get("missing_documents")
        if missing_documents is None:
            ctx["missing_documents"] = []
        elif isinstance(missing_documents, list):
            ctx["missing_documents"] = [str(x).strip() for x in missing_documents if str(x).strip()]
        else:
            ctx["missing_documents"] = [str(missing_documents).strip()]

    if "district" in ctx and ctx.get("district"):
        ctx["district"] = str(ctx["district"]).strip().title()
    if "block" in ctx and ctx.get("block"):
        ctx["block"] = str(ctx["block"]).strip().title()
    if "office_type" in ctx and ctx.get("office_type"):
        ctx["office_type"] = str(ctx["office_type"]).strip().lower()

    return ctx
