from __future__ import annotations

import json
import os
import re
from datetime import datetime, date
from typing import Any, Optional

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from app.agent.state import AgentState
from app.agent.models import SchemeCandidate, SchemeMatch
from app.knowledge_base.scheme_loader import load_schemes

load_dotenv()
<<<<<<< HEAD

_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        _groq_client = Groq(api_key=api_key)
    return _groq_client
# Normalization maps — deterministic, no LLM needed
OCCUPATION_MAP = {
    "kisan": "farmer",
    "farmer": "farmer",
    "kisaan": "farmer",
    "student": "student",
    "vyapari": "small business owner",
    "vendor": "vendor",
    "mazdoor": "daily wage worker",
    "worker": "daily wage worker",
=======
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

QUESTIONS_MAP = {
    "problem_statement": "What problem are you facing?",
    "occupation": "What is your occupation?",
    "state": "Which state do you live in?",
    "district": "Which district do you live in?",
    "block": "Which block do you live in?",
    "residence": "Do you live in a rural area or urban area?",
    "application_status": "Has your application been submitted, rejected, or is it still pending?",
    "rejection_reason": "What reason was given for the rejection?",
    "missing_documents": "Which documents are missing?",
>>>>>>> 00e86c5 (Fix port binding, lazy client init, occupation loop fix, multilingual improvements)
}

STATE_PREFIXES_TO_STRIP = [
    "main ", "mein ", "i am from ", "i live in ",
    "from ", "in ", "i'm from ", "located in ",
]

LANGUAGE_CHOICES = {
    "hindi": "hi-IN",
    "हिंदी": "hi-IN",
    "english": "en-IN",
    "अंग्रेजी": "en-IN",
    "angrezi": "en-IN",
}

RURAL_WORDS = {"rural", "village", "gaon", "gram", "gramin"}
URBAN_WORDS = {"urban", "city", "town", "nagar", "metro"}

PROBLEM_CATEGORY_KEYWORDS = {
    "agriculture": [
        "crop", "farming", "farmer", "seed", "irrigation", "fertilizer", "paddy",
        "wheat", "rice", "harvest", "agri", "agriculture", "land", "soil",
        "livestock", "cow", "buffalo", "goat", "poultry", "fish", "fisher",
        "fisherman", "animal husbandry", "rain", "flood", "drought",
    ],
    "education": ["scholarship", "school", "college", "fees", "admission", "student", "exam"],
    "employment": [
        "job", "employment", "unemployed", "jobless", "berozgar",
        "training", "skill", "startup", "business", "work", "income", "livelihood"
    ],
    "health": ["health", "hospital", "medicine", "treatment", "doctor", "medical"],
    "housing": ["house", "home", "roof", "shelter", "housing", "toilet", "sanitation"],
    "ration": ["ration", "food security", "pds", "card", "subsidized food"],
    "women_child": ["pregnant", "child", "girl", "women", "mother", "anganwadi"],
    "pension": ["pension", "old age", "widow", "disability pension"],
    "disability": ["disability", "disabled", "pwd", "handicapped"],
    "documents": ["aadhaar", "bank account", "ration card", "document", "certificate", "duplicate", "update"],
    "water": ["water", "drinking water", "pipeline", "well", "pump"],
    "fisheries": ["fish", "fisherman", "fisher", "boat", "net", "marine"],
    "debt": ["loan", "debt", "installment", "rejected", "pending", "delayed"],
}


def safe_json_loads(raw: str) -> Any:
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    return json.loads(text)


def _dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


def _normalize_boolish(value: Any) -> Optional[bool]:
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


def _normalize_number(value: Any) -> Optional[float]:
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
    s = value.strip().lower()
    for prefix in STATE_PREFIXES_TO_STRIP:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    s = re.sub(r"^\b(in|at|of)\b\s+", "", s).strip()
    if not s:
        return None
    return s.title()


def normalize_residence(value: str | None) -> str | None:
    if not value:
        return None
    res = value.strip().lower()
    if any(word in res for word in RURAL_WORDS):
        return "rural"
    if any(word in res for word in URBAN_WORDS):
        return "urban"
    return res


def normalize_problem_category(value: str | None, blob: str = "") -> str | None:
    if value:
        v = value.strip().lower()
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
        if v in canonical:
            return canonical[v]
        for k, mapped in canonical.items():
            if k in v:
                return mapped

    low = blob.lower()
    for category, keywords in PROBLEM_CATEGORY_KEYWORDS.items():
        if any(keyword in low for keyword in keywords):
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


def normalize_user_context(context: dict) -> dict:
    ctx = dict(context)

    if "problem_statement" in ctx and ctx.get("problem_statement"):
        ctx["problem_statement"] = str(ctx["problem_statement"]).strip()

    if "problem_category" in ctx:
        ctx["problem_category"] = normalize_problem_category(ctx.get("problem_category"), ctx.get("problem_statement", "") or "")

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
        ctx["land_hectares"] = _normalize_number(ctx.get("land_hectares"))
    if "family_size" in ctx:
        fs = _normalize_number(ctx.get("family_size"))
        ctx["family_size"] = int(fs) if fs is not None else None
    if "has_aadhaar" in ctx:
        ctx["has_aadhaar"] = _normalize_boolish(ctx.get("has_aadhaar"))
    if "has_bank_account" in ctx:
        ctx["has_bank_account"] = _normalize_boolish(ctx.get("has_bank_account"))
    if "has_ration_card" in ctx:
        ctx["has_ration_card"] = _normalize_boolish(ctx.get("has_ration_card"))

    if not ctx.get("problem_statement"):
        inferred = infer_problem_statement_from_context(ctx)
        if inferred:
            ctx["problem_statement"] = inferred

    if not ctx.get("problem_category") and ctx.get("problem_statement"):
        ctx["problem_category"] = normalize_problem_category(None, ctx.get("problem_statement") or "")

    return ctx


def normalize_case_context(context: dict) -> dict:
    ctx = dict(context)

    if "case_id" in ctx and ctx.get("case_id"):
        ctx["case_id"] = str(ctx["case_id"]).strip()

    if "scheme_id" in ctx and ctx.get("scheme_id"):
        ctx["scheme_id"] = str(ctx["scheme_id"]).strip()

    if "scheme_name" in ctx and ctx.get("scheme_name"):
        ctx["scheme_name"] = str(ctx["scheme_name"]).strip()

    if "application_status" in ctx and ctx.get("application_status"):
        ctx["application_status"] = str(ctx["application_status"]).strip().lower()

    if "rejection_reason" in ctx and ctx.get("rejection_reason"):
        ctx["rejection_reason"] = str(ctx["rejection_reason"]).strip()

    if "missing_documents" in ctx:
        md = ctx.get("missing_documents")
        if md is None:
            ctx["missing_documents"] = []
        elif isinstance(md, list):
            ctx["missing_documents"] = [str(x).strip() for x in md if str(x).strip()]
        else:
            ctx["missing_documents"] = [str(md).strip()]

    if "last_followup_date" in ctx and ctx.get("last_followup_date"):
        ctx["last_followup_date"] = str(ctx["last_followup_date"]).strip()

    if "next_action" in ctx and ctx.get("next_action"):
        ctx["next_action"] = str(ctx["next_action"]).strip()

    if "district" in ctx and ctx.get("district"):
        ctx["district"] = str(ctx["district"]).strip().title()

    if "block" in ctx and ctx.get("block"):
        ctx["block"] = str(ctx["block"]).strip().title()

    if "office_type" in ctx and ctx.get("office_type"):
        ctx["office_type"] = str(ctx["office_type"]).strip().lower()

    return ctx


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


def to_match(raw: dict) -> SchemeMatch | None:
    try:
        return SchemeMatch(
            scheme_id=raw.get("scheme_id") or raw.get("id", ""),
            scheme_name=raw.get("scheme_name") or raw.get("name", "Unknown Scheme"),
            confidence=raw.get("confidence", "NEEDS_VERIFICATION"),
            reason=raw.get("reason", ""),
            documents_required=raw.get("documents_required", []) or [],
            action_steps=raw.get("action_steps", []) or [],
            portal=raw.get("portal"),
            helpline=raw.get("helpline"),
        )
    except ValidationError:
        return None


def parse_language_choice(text: str) -> Optional[str]:
    low = text.strip().lower()
    for token, code in LANGUAGE_CHOICES.items():
        if token in low:
            return code
    return None


def detect_user_language(state: AgentState) -> AgentState:
    user_input = state.get("user_input", "")
    preferred = state.get("preferred_language")

    if preferred:
        state["user_language"] = preferred
        state["translate_response"] = preferred != "en-IN"
        state["language_selected"] = True
        state["awaiting_language_selection"] = False
        state["stop_after_language_gate"] = False
        return state

    chosen = parse_language_choice(user_input)
    if chosen:
        state["preferred_language"] = chosen
        state["user_language"] = chosen
        state["translate_response"] = chosen != "en-IN"
        state["language_selected"] = True
        state["awaiting_language_selection"] = False
        state["stop_after_language_gate"] = True
        state["response_to_user"] = "Thanks. Tell me what problem you are facing."
        state["response_tts_text"] = state["response_to_user"]
        state["should_play_tts"] = True
        return state

    state["awaiting_language_selection"] = True
    state["language_selected"] = False
    state["translate_response"] = False
    state["stop_after_language_gate"] = True
    state["response_to_user"] = "Hindi mein baat karein ya English mein? Please reply with Hindi or English."
    state["response_tts_text"] = state["response_to_user"]
    state["should_play_tts"] = True
    return state


def extract_context(state: AgentState) -> AgentState:
    last_field = state.get("last_question_field")
    user_input = (state.get("user_input") or "").strip()
    user_existing = dict(state.get("user_context", {}))
    case_existing = dict(state.get("case_context", {}))
    is_short = len(user_input.split()) <= 4

    user_context_fields = {
        "problem_statement",
        "problem_category",
        "specific_problem",
        "occupation",
        "state",
        "district",
        "block",
        "residence",
        "land_hectares",
        "income_category",
        "family_size",
        "has_aadhaar",
        "has_bank_account",
        "has_ration_card",
    }

    case_context_fields = {
        "case_id",
        "scheme_id",
        "scheme_name",
        "application_status",
        "rejection_reason",
        "missing_documents",
        "last_followup_date",
        "next_action",
        "district",
        "block",
        "office_type",
    }

    # Fast path for short replies to a specific question
    if last_field and is_short:
        if last_field in user_context_fields:
            if last_field == "problem_statement":
                user_existing["problem_statement"] = user_input
                user_existing["problem_category"] = normalize_problem_category(None, user_input)
            elif last_field in {"occupation", "state", "district", "block", "residence"}:
                user_existing[last_field] = user_input
            elif last_field in {"has_aadhaar", "has_bank_account", "has_ration_card"}:
                user_existing[last_field] = _normalize_boolish(user_input)
            elif last_field in {"land_hectares", "family_size"}:
                user_existing[last_field] = _normalize_number(user_input)
            else:
                user_existing[last_field] = user_input

        elif last_field in case_context_fields:
            if last_field == "missing_documents":
                case_existing["missing_documents"] = [user_input]
            else:
                case_existing[last_field] = user_input

        state["user_context"] = normalize_user_context(user_existing)
        state["case_context"] = normalize_case_context(case_existing)
        return state

    prompt = f"""
You are extracting structured information from a user's message for a government-scheme assistant.

The assistant is problem-first:
- capture the main problem first
- then extract any useful profile details only if present
- do not force fields that are not mentioned

Important:
- If the user describes their situation (for example: "I am unemployed", "I am a farmer", "I am poor"), treat that as a problem_statement.
- If the user is describing a pending/rejected application, capture that in case_context.

Message:
{user_input!r}

Return ONLY valid JSON with exactly this structure:
{{
  "user_context": {{
    "problem_statement": null,
    "problem_category": null,
    "specific_problem": null,
    "occupation": null,
    "state": null,
    "district": null,
    "block": null,
    "residence": null,
    "land_hectares": null,
    "income_category": null,
    "family_size": null,
    "has_aadhaar": null,
    "has_bank_account": null,
    "has_ration_card": null
  }},
  "case_context": {{
    "case_id": null,
    "scheme_id": null,
    "scheme_name": null,
    "application_status": null,
    "rejection_reason": null,
    "missing_documents": [],
    "last_followup_date": null,
    "next_action": null,
    "district": null,
    "block": null,
    "office_type": null
  }}
}}

Rules:
- problem_statement should be a short plain-English summary.
- problem_category must be one of:
  agriculture, education, employment, health, housing, ration, women_child, pension, disability, documents, water, fisheries, debt, other
- Normalize occupation, state, and residence if obvious.
- If the message is about a rejected/pending application, capture it in case_context.
- If you are not sure, use null.
"""
<<<<<<< HEAD
    response = get_groq_client().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0
=======

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        extracted = safe_json_loads(raw)
        if not isinstance(extracted, dict):
            extracted = {}
    except Exception:
        extracted = {}

    user_partial = extracted.get("user_context", {}) if isinstance(extracted.get("user_context", {}), dict) else {}
    case_partial = extracted.get("case_context", {}) if isinstance(extracted.get("case_context", {}), dict) else {}

    for key, value in user_partial.items():
        if value is not None:
            user_existing[key] = value

    for key, value in case_partial.items():
        if value is not None:
            case_existing[key] = value

    user_existing["problem_category"] = normalize_problem_category(
        user_existing.get("problem_category"),
        " ".join(
            str(user_existing.get(k, "") or "")
            for k in ["problem_statement", "specific_problem"]
        ),
>>>>>>> 00e86c5 (Fix port binding, lazy client init, occupation loop fix, multilingual improvements)
    )

    state["user_context"] = normalize_user_context(user_existing)
    state["case_context"] = normalize_case_context(case_existing)
    return state


def check_completeness(state: AgentState) -> AgentState:
    ctx = state.get("user_context", {})
    history = state.get("conversation_history", [])

    problem = (ctx.get("problem_statement") or ctx.get("specific_problem") or "").strip()

    # If the user is repeating the same statement and we are stuck, break the loop.
    last_user_inputs = [
        str(h.get("content", "")).strip().lower()
        for h in history[-4:]
        if h.get("role") == "user"
    ]
    if last_user_inputs and len(set(last_user_inputs)) == 1 and len(last_user_inputs) >= 2:
        inferred = infer_problem_statement_from_context(ctx)
        if inferred and not problem:
            ctx["problem_statement"] = inferred
            ctx["problem_category"] = normalize_problem_category(ctx.get("problem_category"), inferred)
            state["user_context"] = normalize_user_context(ctx)
            problem = inferred

    # Problem-first flow: the only hard requirement is a usable problem statement.
    if not problem:
        inferred = infer_problem_statement_from_context(ctx)
        if inferred:
            ctx["problem_statement"] = inferred
            ctx["problem_category"] = normalize_problem_category(ctx.get("problem_category"), inferred)
            state["user_context"] = normalize_user_context(ctx)
            problem = inferred

    if not problem:
        state["context_complete"] = False
        state["missing_fields"] = ["problem_statement"]
        state["followup_question"] = "What kind of help do you need — job, scholarship, ration, loan, health, or something else?"
        state["last_question_field"] = "problem_statement"
        return state

    # If the problem statement is very short but still clearly meaningful, accept it.
    if len(problem.split()) < 2 and not ctx.get("problem_category"):
        category = infer_problem_statement_from_context(ctx)
        if category:
            ctx["problem_statement"] = category
            state["user_context"] = normalize_user_context(ctx)
        else:
            state["context_complete"] = False
            state["missing_fields"] = ["problem_statement"]
            state["followup_question"] = "What kind of help do you need — job, scholarship, ration, loan, health, or something else?"
            state["last_question_field"] = "problem_statement"
            return state

    state["context_complete"] = True
    state["missing_fields"] = []
    state["followup_question"] = None
    state["last_question_field"] = None
    return state


def _scheme_text(scheme: dict) -> str:
    parts = [
        scheme.get("scheme_name", ""),
        scheme.get("brief_description", ""),
        scheme.get("description", ""),
        " ".join(scheme.get("tags", []) or []),
        " ".join(scheme.get("category", []) or []),
        " ".join(scheme.get("state", []) or []),
        " ".join(scheme.get("documents_required", []) or []),
    ]
    return " ".join(str(p) for p in parts if p)


def _is_closed_scheme(scheme: dict) -> bool:
    close_date = scheme.get("close_date")
    if not close_date:
        return False
    try:
        if isinstance(close_date, str):
            return datetime.strptime(close_date[:10], "%Y-%m-%d").date() < date.today()
    except Exception:
        return False
    return False


def _score_scheme(scheme: dict, ctx: dict, case_ctx: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    text = _scheme_text(scheme).lower()
    eligibility = scheme.get("eligibility", {}) or {}

    problem_blob = " ".join(
        str(ctx.get(k, "") or "") for k in [
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

    scheme_states = [str(s).lower().strip() for s in (scheme.get("state") or [])]
    eligibility_states = [str(s).lower().strip() for s in (eligibility.get("state") or []) if s]

    if user_state and (scheme_states or eligibility_states):
        allowed_states = scheme_states or eligibility_states
        if not any(
            st == "all" or user_state == st or user_state in st or st in user_state
            for st in allowed_states
        ):
            return -999, ["state mismatch"]
        score += 4
        reasons.append(f"available in {ctx.get('state')}")
    elif scheme_states or eligibility_states:
        score += 1

    scheme_occ = [str(o).lower().strip() for o in (eligibility.get("occupation") or []) if o]
    if occupation and scheme_occ:
        if any(occupation == o or occupation in o or o in occupation for o in scheme_occ):
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
        if any(k in text or k in problem_blob or k in category_text or k in tags_text for k in category_keywords[category]):
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


def _confidence_from_score(score: int) -> str:
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "LIKELY"
    return "NEEDS_VERIFICATION"


def _make_action_steps(scheme: dict, ctx: dict, case_ctx: dict) -> list[str]:
    steps: list[str] = []

    app_mode = (scheme.get("application_mode") or "").lower().strip()
    district = ctx.get("district")
    state = ctx.get("state")

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


def _build_verification_notes(scheme: dict, ctx: dict) -> list[str]:
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


def _filter_candidates(all_schemes: list[dict]) -> list[SchemeCandidate]:
    candidates: list[SchemeCandidate] = []
    for scheme in all_schemes:
        if _is_closed_scheme(scheme):
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

    candidates = _filter_candidates(all_schemes)

    scored: list[tuple[int, dict, list[str]]] = []
    for candidate in candidates:
        raw = _dump_model(candidate)
        score, reasons = _score_scheme(raw, ctx, case_ctx)
        if score > 0:
            scored.append((score, raw, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:8]

    matches: list[SchemeMatch] = []
    for score, raw, reasons in top:
        match = SchemeMatch(
            scheme_id=raw.get("scheme_id", ""),
            scheme_name=raw.get("scheme_name", "Unknown Scheme"),
            confidence=_confidence_from_score(score),
            reason="; ".join(reasons) if reasons else "This scheme appears relevant based on the available details.",
            documents_required=raw.get("documents_required", []) or [],
            action_steps=_make_action_steps(raw, ctx, case_ctx),
            portal=raw.get("portal") or None,
            helpline=raw.get("helpline") or None,
        )
        matches.append(match)

    if not matches:
        fallback = []
        for candidate in candidates[:5]:
            raw = _dump_model(candidate)
            fallback.append(
                SchemeMatch(
                    scheme_id=raw.get("scheme_id", ""),
                    scheme_name=raw.get("scheme_name", "Unknown Scheme"),
                    confidence="NEEDS_VERIFICATION",
                    reason="I could not confirm a strong match yet. Share your state or more details so I can narrow it down.",
                    documents_required=raw.get("documents_required", []) or [],
                    action_steps=_make_action_steps(raw, ctx, case_ctx),
                    portal=raw.get("portal") or None,
                    helpline=raw.get("helpline") or None,
                )
            )
        matches = fallback

<<<<<<< HEAD
        # Occupation filter — include if scheme lists no occupation OR matches
        scheme_occupations = [o.lower() for o in (e.get("occupation") or [])]
        if scheme_occupations and occupation:
            occ_match = any(
                occupation in o or o in occupation
                for o in scheme_occupations
            )
            if not occ_match:
                return False

        # Residence filter
        scheme_residence = (e.get("residence") or "").lower()
        if scheme_residence and residence:
            if scheme_residence not in ("both", "") and scheme_residence != residence:
                return False

        return True

    filtered = [s for s in all_schemes if is_relevant(s)]

    # Cap at 30 schemes — enough for good coverage, fits in context window
   # Cap at 15 schemes
    filtered = filtered[:15]

    if not filtered:
        filtered = [s for s in all_schemes
                   if not s.get("eligibility", {}).get("state")][:10]

    # Trim each scheme to only what the LLM needs for reasoning
    # Removes verbose description fields that bloat the prompt
    def trim_scheme(s: dict) -> dict:
        return {
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "category": s.get("category", ""),
            "eligibility": s.get("eligibility", {}),
            "benefit": (s.get("benefit") or "")[:120],
            "documents_required": s.get("documents_required", [])[:6],
            "portal": s.get("portal", ""),
            "helpline": s.get("helpline", ""),
        }

    trimmed = [trim_scheme(s) for s in filtered]

    prompt = f"""
You are an expert on Indian government welfare schemes.

User profile:
{json.dumps(ctx, indent=2)}

Schemes to evaluate:
{json.dumps(trimmed, indent=2)}

Return a JSON array of matches where this user is genuinely eligible.
Each match must have: scheme_id, scheme_name, confidence (HIGH/LIKELY/NEEDS_VERIFICATION),
reason (one sentence), documents_required (list), action_steps (2-3 steps), portal, helpline.
Return ONLY valid JSON array.
"""

    response = get_groq_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    matched = json.loads(raw)
    state["matched_schemes"] = matched
=======
    state["matched_schemes"] = [_dump_model(m) for m in matches]
>>>>>>> 00e86c5 (Fix port binding, lazy client init, occupation loop fix, multilingual improvements)
    return state


def ask_followup(state: AgentState) -> AgentState:
    state["response_to_user"] = state.get("followup_question") or "What kind of help do you need — job, scholarship, ration, loan, health, or something else?"
    state["response_tts_text"] = state["response_to_user"]
    state["should_play_tts"] = True
    return state


def format_results(state: AgentState) -> AgentState:
    ctx = state.get("user_context", {})
    case_ctx = state.get("case_context", {})
    schemes = state.get("matched_schemes", [])

    application_status = (case_ctx.get("application_status") or "").strip().lower()
    rejection_reason = (case_ctx.get("rejection_reason") or "").strip()

    if not schemes:
        if not ctx.get("state"):
            state["response_to_user"] = (
                "I understand the problem, but I still need your state to narrow down the correct scheme. "
                "Please tell me which state you are in."
            )
        else:
            state["response_to_user"] = (
                "I could not find a strong match from the available scheme data. "
                "Please share one more detail, such as your district, occupation, or the exact document/application issue."
            )

        if application_status or rejection_reason:
            extra = []
            if application_status:
                extra.append(f"Application status: {application_status}.")
            if rejection_reason:
                extra.append(f"Rejection reason: {rejection_reason}.")
            state["response_to_user"] += "\n\n" + " ".join(extra)

        state["response_tts_text"] = state["response_to_user"]
        state["should_play_tts"] = True
        return state

    lines = [f"I found {len(schemes)} scheme(s) that may fit your situation:\n"]

    if application_status or rejection_reason:
        lines.append("This looks like a follow-up on an existing application.")
        if application_status:
            lines.append(f"Current status: {application_status}")
        if rejection_reason:
            lines.append(f"Rejection reason: {rejection_reason}")
        if case_ctx.get("missing_documents"):
            lines.append(f"Missing documents: {', '.join(case_ctx.get('missing_documents', []))}")
        lines.append("Next step: verify the exact missing requirement, then re-apply or escalate through the correct office.\n")

    for i, s in enumerate(schemes, 1):
        scheme_name = s.get("scheme_name") or s.get("name") or "Unknown Scheme"
        confidence = s.get("confidence", "NEEDS_VERIFICATION")
        reason = s.get("reason", "No reason provided.")
        documents = s.get("documents_required", []) or []
        steps = s.get("action_steps", []) or []
        portal = s.get("portal") or "Not available"
        helpline = s.get("helpline") or "Not available"

        lines.append("=" * 50)
        lines.append(f"{i}. {scheme_name}")
        lines.append(f"   Confidence: {confidence}")
        lines.append(f"   Why you qualify: {reason}")

        lines.append("\n   Documents needed:")
        if documents:
            for doc in documents:
                lines.append(f"   - {doc}")
        else:
            lines.append("   - Not specified")

        lines.append("\n   What to do now:")
        if steps:
            for step in steps:
                lines.append(f"   → {step}")
        else:
            lines.append("   → Check the official portal and verify eligibility with the department or CSC.")

        if confidence == "NEEDS_VERIFICATION":
            lines.append("\n   What to verify:")
            for note in _build_verification_notes(s, ctx):
                lines.append(f"   → {note}")

        lines.append(f"\n   Portal: {portal}")
        lines.append(f"   Helpline: {helpline}\n")

    if not ctx.get("district"):
        lines.append("If you share your district next, I can narrow down the local office path more precisely.")

    state["response_to_user"] = "\n".join(lines)
    state["response_tts_text"] = state["response_to_user"]
    state["should_play_tts"] = True
    return state


def translate_response(state: AgentState) -> AgentState:
    from app.language.sarvam import translate_to_user_language

    if not state.get("translate_response", False):
        return state
    if not state.get("response_to_user"):
        return state

    lang = state.get("user_language") or state.get("preferred_language") or "hi-IN"

    try:
        state["response_to_user"] = translate_to_user_language(
            state["response_to_user"],
            target_language_code=lang,
        )
        if state.get("response_tts_text"):
            state["response_tts_text"] = translate_to_user_language(
                state["response_tts_text"],
                target_language_code=lang,
            )
    except Exception:
        pass

    return state