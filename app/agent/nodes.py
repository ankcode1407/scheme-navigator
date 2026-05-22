from __future__ import annotations

import json
import os
from typing import Any, Optional

from dotenv import load_dotenv
from groq import Groq

from app.agent.case_followup import infer_case_context_from_text
from app.agent.constants import LANGUAGE_CHOICES, PROBLEM_FIRST_QUESTION
from app.agent.context import (
    infer_problem_statement_from_context,
    infer_user_context_from_text,
    normalize_boolish,
    normalize_case_context,
    normalize_number,
    normalize_problem_category,
    normalize_user_context,
)
from app.agent.response_formatting import format_results
from app.agent.scheme_matching import match_schemes
from app.agent.state import AgentState

load_dotenv()

_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def safe_json_loads(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def parse_language_choice(text: str) -> Optional[dict[str, str]]:
    normalized = text.strip().lower()
    if not normalized:
        return None

    for choice in LANGUAGE_CHOICES:
        tokens = [choice["code"], choice["name"], choice["english_name"], *choice["tokens"]]
        if any(normalized == token.lower() for token in tokens):
            return choice
        if any(token.lower() in normalized for token in tokens if len(token) >= 3):
            return choice
    return None


def detect_user_language(state: AgentState) -> AgentState:
    preferred_language = state.get("preferred_language") or state.get("user_language")
    if preferred_language:
        state["preferred_language"] = preferred_language
        state["user_language"] = preferred_language
        state["translate_response"] = preferred_language != "en"
        state["language_selected"] = True
        state["awaiting_language_selection"] = False
        state["stop_after_language_gate"] = False
        return state

    selected = parse_language_choice(state.get("user_input", ""))
    if selected:
        code = selected["code"]
        opening = "Thanks. Tell me what problem you are facing."
        state["preferred_language"] = code
        state["user_language"] = code
        state["translate_response"] = code != "en"
        state["language_selected"] = True
        state["awaiting_language_selection"] = False
        state["stop_after_language_gate"] = True
        state["response_to_user"] = opening
        state["response_tts_text"] = opening
        state["should_play_tts"] = True
        return state

    prompt = (
        "Please choose your language first. You can pick Hindi, English, Bengali, "
        "Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, or Odia."
    )
    state["user_language"] = "en"
    state["translate_response"] = False
    state["language_selected"] = False
    state["awaiting_language_selection"] = True
    state["stop_after_language_gate"] = True
    state["response_to_user"] = prompt
    state["response_tts_text"] = prompt
    state["should_play_tts"] = True
    return state


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if value in (None, "", [], {}):
            continue
        if target.get(key) in (None, "", [], {}):
            target[key] = value


def _set_short_answer_field(state: AgentState, field: str, text: str) -> None:
    user_context = state.setdefault("user_context", {})
    case_context = state.setdefault("case_context", {})

    if field == "problem_statement":
        user_context["problem_statement"] = text.strip()
        category = normalize_problem_category(None, text)
        if category:
            user_context["problem_category"] = category
    elif field == "occupation":
        user_context["occupation"] = text.strip()
    elif field in {"state", "district", "block", "residence"}:
        user_context[field] = text.strip()
    elif field in {"age", "income", "land_owned"}:
        user_context[field] = normalize_number(text) or text.strip()
    elif field in {
        "caste",
        "gender",
        "marital_status",
        "disability_status",
        "aadhaar_linked",
        "bank_account",
        "ration_card",
        "bpl_status",
    }:
        bool_value = normalize_boolish(text)
        user_context[field] = bool_value if bool_value is not None else text.strip()
    elif field in {"scheme_name", "application_status", "office_visited", "last_update"}:
        case_context[field] = text.strip()
    elif field == "missing_documents":
        case_context[field] = [part.strip() for part in text.split(",") if part.strip()]


def extract_context(state: AgentState) -> AgentState:
    user_input = state.get("user_input", "").strip()
    if not user_input:
        return state

    user_context = dict(state.get("user_context") or {})
    case_context = dict(state.get("case_context") or {})
    state["user_context"] = user_context
    state["case_context"] = case_context

    rule_based_user = infer_user_context_from_text(user_input)
    rule_based_case = infer_case_context_from_text(user_input)
    last_field = state.get("last_question_field")

    if last_field:
        _set_short_answer_field(state, last_field, user_input)
        _merge_missing(user_context, rule_based_user)
        _merge_missing(case_context, rule_based_case)
        user_context["problem_category"] = normalize_problem_category(
            user_context.get("problem_category"),
            user_context.get("problem_statement"),
        )
        state["user_context"] = normalize_user_context(user_context)
        state["case_context"] = normalize_case_context(case_context)
        return state

    prompt = f"""
You extract citizen context for an Indian government scheme helper.

The conversation must be problem-first. Do not assume the user knows official
eligibility terms. If the user says "crop failed", "need money", "scholarship",
"toilet", "payment not received", or similar, capture that as problem_statement
and infer only fields that are clearly present.

Return JSON only with this shape:
{{
  "user_context": {{
    "problem_statement": string or null,
    "problem_category": one of ["agriculture", "education", "housing", "health", "employment", "pension", "business", "documents", "sanitation", "benefit_delay", "other"] or null,
    "occupation": string or null,
    "state": string or null,
    "district": string or null,
    "block": string or null,
    "residence": "rural" or "urban" or null,
    "age": number or null,
    "gender": string or null,
    "caste": string or null,
    "income": number or null,
    "land_owned": number or null,
    "aadhaar_linked": boolean or null,
    "bank_account": boolean or null,
    "ration_card": boolean or null,
    "bpl_status": boolean or null,
    "disability_status": boolean or null,
    "marital_status": string or null
  }},
  "case_context": {{
    "scheme_name": string or null,
    "application_status": string or null,
    "office_visited": string or null,
    "missing_documents": list of strings,
    "last_update": string or null
  }}
}}

User message: {user_input}
"""

    extracted: dict[str, Any] = {}
    try:
        completion = get_groq_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured JSON. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=500,
        )
        raw = completion.choices[0].message.content or "{}"
        extracted = safe_json_loads(raw)
    except Exception:
        extracted = {}

    _merge_missing(user_context, extracted.get("user_context") or {})
    _merge_missing(case_context, extracted.get("case_context") or {})
    _merge_missing(user_context, rule_based_user)
    _merge_missing(case_context, rule_based_case)

    user_context["problem_category"] = normalize_problem_category(
        user_context.get("problem_category"),
        user_context.get("problem_statement"),
    )
    state["user_context"] = normalize_user_context(user_context)
    state["case_context"] = normalize_case_context(case_context)
    return state


def check_completeness(state: AgentState) -> AgentState:
    user_context = dict(state.get("user_context") or {})
    history = state.get("conversation_history") or []

    problem = user_context.get("problem_statement")
    if not problem:
        problem = infer_problem_statement_from_context(user_context, history)
        if problem:
            user_context["problem_statement"] = problem

    if user_context.get("problem_statement"):
        user_context["problem_category"] = normalize_problem_category(
            user_context.get("problem_category"),
            user_context.get("problem_statement"),
        )
        state["user_context"] = normalize_user_context(user_context)
        state["context_complete"] = True
        state["missing_fields"] = []
        state["followup_question"] = None
        state["last_question_field"] = None
        return state

    state["user_context"] = normalize_user_context(user_context)
    state["context_complete"] = False
    state["missing_fields"] = ["problem_statement"]
    state["followup_question"] = PROBLEM_FIRST_QUESTION
    state["last_question_field"] = "problem_statement"
    return state


def ask_followup(state: AgentState) -> AgentState:
    question = state.get("followup_question") or PROBLEM_FIRST_QUESTION
    state["response_to_user"] = question
    state["response_tts_text"] = question
    state["should_play_tts"] = True
    return state


def translate_response(state: AgentState) -> AgentState:
    response = state.get("response_to_user")
    user_language = state.get("user_language") or state.get("preferred_language") or "en"
    if not response or user_language == "en":
        return state

    try:
        from app.language.translation import translate_to_user_language

        translated = translate_to_user_language(response, user_language)
        if translated:
            state["response_to_user"] = translated
    except Exception:
        pass
    return state
