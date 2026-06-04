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

    bare_occupation_words = {
        "farmer",
        "kisan",
        "kisaan",
        "student",
        "unemployed",
        "jobless",
    }

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

    land = (
        normalize_number(lowered)
        if any(word in lowered for word in ["hectare", "acre", "zameen", "land"])
        else None
    )

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

    if "age" in ctx:
        ctx["age"] = normalize_number(ctx.get("age"))

    if "income" in ctx:
        ctx["income"] = normalize_number(ctx.get("income"))

    if "gender" in ctx and ctx.get("gender"):
        ctx["gender"] = str(ctx.get("gender")).strip().lower()

    if "caste" in ctx and ctx.get("caste"):
        ctx["caste"] = normalize_caste(ctx.get("caste"))

    if "marital_status" in ctx and ctx.get("marital_status"):
        ctx["marital_status"] = str(ctx.get("marital_status")).strip().lower()

    if "bpl_status" in ctx:
        ctx["bpl_status"] = normalize_boolish(ctx.get("bpl_status"))

    if "disability_status" in ctx:
        ctx["disability_status"] = normalize_boolish(ctx.get("disability_status"))

    # Sync and normalize land fields
    if "land_owned" in ctx:
        ctx["land_owned"] = normalize_number(ctx.get("land_owned"))
    if "land_owned" in ctx and ctx["land_owned"] is not None:
        ctx["land_hectares"] = ctx["land_owned"]
    elif "land_hectares" in ctx and ctx["land_hectares"] is not None:
        ctx["land_owned"] = ctx["land_hectares"]

    # Sync and normalize Aadhaar fields
    if "aadhaar_linked" in ctx:
        ctx["aadhaar_linked"] = normalize_boolish(ctx.get("aadhaar_linked"))
    if "has_aadhaar" in ctx:
        ctx["has_aadhaar"] = normalize_boolish(ctx.get("has_aadhaar"))
    if "aadhaar_linked" in ctx and ctx["aadhaar_linked"] is not None:
        ctx["has_aadhaar"] = ctx["aadhaar_linked"]
    elif "has_aadhaar" in ctx and ctx["has_aadhaar"] is not None:
        ctx["aadhaar_linked"] = ctx["has_aadhaar"]

    # Sync and normalize bank account fields
    if "bank_account" in ctx:
        ctx["bank_account"] = normalize_boolish(ctx.get("bank_account"))
    if "has_bank_account" in ctx:
        ctx["has_bank_account"] = normalize_boolish(ctx.get("has_bank_account"))
    if "bank_account" in ctx and ctx["bank_account"] is not None:
        ctx["has_bank_account"] = ctx["bank_account"]
    elif "has_bank_account" in ctx and ctx["has_bank_account"] is not None:
        ctx["bank_account"] = ctx["has_bank_account"]

    # Sync and normalize ration card fields
    if "ration_card" in ctx:
        ctx["ration_card"] = normalize_boolish(ctx.get("ration_card"))
    if "has_ration_card" in ctx:
        ctx["has_ration_card"] = normalize_boolish(ctx.get("has_ration_card"))
    if "ration_card" in ctx and ctx["ration_card"] is not None:
        ctx["has_ration_card"] = ctx["ration_card"]
    elif "has_ration_card" in ctx and ctx["has_ration_card"] is not None:
        ctx["ration_card"] = ctx["has_ration_card"]

    if not ctx.get("problem_statement"):
        inferred = infer_problem_statement_from_context(ctx)

        if inferred:
            ctx["problem_statement"] = inferred

    if not ctx.get("problem_category") and ctx.get("problem_statement"):
        ctx["problem_category"] = normalize_problem_category(
            None,
            ctx.get("problem_statement") or "",
        )

    return ctx


def normalize_case_context(context: dict) -> dict:
    ctx = dict(context)

    for key in [
        "case_id",
        "scheme_id",
        "scheme_name",
        "rejection_reason",
        "last_followup_date",
        "next_action",
    ]:
        if key in ctx and ctx.get(key):
            ctx[key] = str(ctx[key]).strip()

    if "application_status" in ctx and ctx.get("application_status"):
        ctx["application_status"] = str(ctx["application_status"]).strip().lower()

    if "missing_documents" in ctx:
        missing_documents = ctx.get("missing_documents")

        if missing_documents is None:
            ctx["missing_documents"] = []

        elif isinstance(missing_documents, list):
            ctx["missing_documents"] = [
                str(x).strip()
                for x in missing_documents
                if str(x).strip()
            ]

        else:
            ctx["missing_documents"] = [str(missing_documents).strip()]

    if "district" in ctx and ctx.get("district"):
        ctx["district"] = str(ctx["district"]).strip().title()

    if "block" in ctx and ctx.get("block"):
        ctx["block"] = str(ctx["block"]).strip().title()

    if "office_type" in ctx and ctx.get("office_type"):
        ctx["office_type"] = str(ctx["office_type"]).strip().lower()

    return ctx


def normalize_caste(caste_str: str | None) -> str:
    if not caste_str:
        return "GENERAL"
    c_clean = str(caste_str).strip().upper()
    if "SCHEDULED CASTE" in c_clean or c_clean == "SC":
        return "SC"
    if "SCHEDULED TRIBE" in c_clean or c_clean == "ST":
        return "ST"
    if "OBC" in c_clean or "OTHER BACKWARD" in c_clean:
        return "OBC"
    if "GEN" in c_clean or "GENERAL" in c_clean:
        return "GENERAL"
    return c_clean
