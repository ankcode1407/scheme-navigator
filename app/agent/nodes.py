import os
import json
from dotenv import load_dotenv
from groq import Groq
from app.agent.state import AgentState
from app.knowledge_base.scheme_loader import load_schemes

load_dotenv()

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
}

STATE_PREFIXES_TO_STRIP = ["main ", "mein ", "i am from ", "i live in ", "from "]

def normalize_context(context: dict) -> dict:
    # Normalize occupation
    if context.get("occupation"):
        occ = context["occupation"].lower().strip()
        context["occupation"] = OCCUPATION_MAP.get(occ, occ)

    # Normalize state — strip common Hindi/English prefixes
    if context.get("state"):
        state = context["state"].lower().strip()
        for prefix in STATE_PREFIXES_TO_STRIP:
            if state.startswith(prefix):
                state = state[len(prefix):]
        context["state"] = state.strip().title()

    # Normalize residence
    # Normalize residence
    if context.get("residence"):
        res = context["residence"].lower().strip()
        if any(w in res for w in ["rural", "village", "gaon", "gram",
                                "goan", "gramin", "देहात", "गाँव",
                                "गांव", "ग्रामीण", "gramin"]):
            context["residence"] = "rural"
        elif any(w in res for w in ["urban", "city", "town", "shahar",
                                    "sheher", "nagar", "शहर", "नगर",
                                    "शेहर"]):
            context["residence"] = "urban"

    return context

def detect_user_language(state: AgentState) -> AgentState:
    from app.language.sarvam import detect_language

    text = state["user_input"]
    lang = detect_language(text)

    state["user_language"] = lang
    state["translate_response"] = lang != "en-IN"

    return state
# ── NODE 1 ──────────────────────────────────────────────────────────────────
# Takes raw user input and extracts structured facts about who they are
def extract_context(state: AgentState) -> AgentState:
    prompt = f"""
You are a helpful assistant extracting structured information from a user's message.

Extract whatever you can from this message and return ONLY valid JSON.
If a field is not mentioned, set it to null.

Message: "{state['user_input']}"

Return this exact JSON structure:
{{
    "occupation": null,
    "state": null,
    "land_hectares": null,
    "income_category": null,
    "residence": null,
    "family_size": null,
    "has_aadhaar": null,
    "has_bank_account": null,
    "has_ration_card": null,
    "specific_problem": null
}}
"""
    response = get_groq_client().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0
    )

    raw = response.choices[0].message.content.strip()

    # Clean JSON if wrapped in markdown
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    extracted = json.loads(raw)

    # Merge with existing context — don't overwrite known fields with null
    existing = state.get("user_context", {})
    for key, value in extracted.items():
        if value is not None:
            existing[key] = value

    state["user_context"] = normalize_context(existing)
    return state
    


# ── NODE 2 ──────────────────────────────────────────────────────────────────
# Checks what we still don't know and decides whether to ask or proceed
def check_completeness(state: AgentState) -> AgentState:
    ctx = state.get("user_context", {})

    # Minimum fields needed before we can reason about schemes
    required = ["occupation", "state", "residence"]
    missing = [f for f in required if not ctx.get(f)]

    state["missing_fields"] = missing

    if missing:
        state["context_complete"] = False
        field = missing[0]
        questions = {
            "occupation": "What is your occupation? For example: farmer, student, small business owner, or daily wage worker?",
            "state":      "Which state do you live in?",
            "residence":  "Do you live in a rural area (village) or urban area (city/town)?"
        }
        state["followup_question"] = questions.get(field, f"Can you tell me your {field}?")
    else:
        state["context_complete"] = True
        state["followup_question"] = None

    return state


# ── NODE 3 ──────────────────────────────────────────────────────────────────
# Matches user context against scheme eligibility rules and scores each match
def match_schemes(state: AgentState) -> AgentState:
    all_schemes = load_schemes()
    ctx = state["user_context"]

    # ── Pre-filter in Python — no LLM needed ──────────────────────────────
    occupation = (ctx.get("occupation") or "").lower()
    user_state = (ctx.get("state") or "").lower()
    residence = (ctx.get("residence") or "").lower()

    def is_relevant(scheme: dict) -> bool:
        e = scheme.get("eligibility", {})

        # State filter — include if scheme is national OR matches user state
        scheme_states = [s.lower() for s in (e.get("state") or [])]
        if scheme_states:
            state_match = any(
                user_state in s or s in user_state or s == "all"
                for s in scheme_states
            )
            if not state_match:
                return False

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
    return state

# ── NODE 5 ──────────────────────────────────────────────────────────────────
# Runs AFTER format_results — translates response if user wrote in non-English
def translate_response(state: AgentState) -> AgentState:
    from app.language.sarvam import translate_to_user_language

    if not state.get("translate_response", False):
        return state  # English user — skip translation

    if not state.get("response_to_user"):
        return state  # Nothing to translate

    lang = state.get("user_language", "hi-IN")
    state["response_to_user"] = translate_to_user_language(
        state["response_to_user"],
        target_language_code=lang
    )

    return state