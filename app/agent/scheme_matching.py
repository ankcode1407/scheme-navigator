from __future__ import annotations

import hashlib
import os
os.environ["HF_HUB_OFFLINE"] = "1"

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import ValidationError

from app.agent.case_followup import build_case_followup_steps, is_case_followup
from app.agent.context import normalize_caste
from app.agent.models import SchemeCandidate, SchemeMatch
from app.agent.state import AgentState
from app.knowledge_base.scheme_loader import load_schemes

# Embedding File Paths
SCHEMES_DIR = Path(__file__).parent.parent / "schemes"
NPY_PATH = SCHEMES_DIR / "scheme_embeddings.npy"
META_PATH = SCHEMES_DIR / "scheme_embeddings.meta.json"
SCHEMES_JSON_PATH = SCHEMES_DIR / "schemes_full.json"

# Global Singletons
_MODEL: Any = None
_EMBEDDINGS: np.ndarray | None = None
SEMANTIC_DISABLED = False


def compute_common_scheme_words(schemes, threshold=0.10):
    from collections import Counter
    total = len(schemes)
    word_counts = Counter()
    for scheme in schemes:
        words = set(
            scheme["name"].lower().split()
        )
        word_counts.update(words)
    return {
        w for w, c in word_counts.items()
        if c / total >= threshold
    }

COMMON_SCHEME_WORDS = compute_common_scheme_words(load_schemes())
print(f"COMMON_SCHEME_WORDS count: {len(COMMON_SCHEME_WORDS)}")
print(f"COMMON_SCHEME_WORDS: {sorted(list(COMMON_SCHEME_WORDS))}")


def get_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def init_matcher(eager_warm: bool = False):
    """
    Initializes the embedding model and loads precomputed vectors.
    Uses try/except circuit breakers to disable semantics gracefully if loading fails.
    Checks SHA-256 hashes to verify scheme file matches precomputed embeddings.
    """
    global _MODEL, _EMBEDDINGS, SEMANTIC_DISABLED
    if SEMANTIC_DISABLED:
        return
    if _EMBEDDINGS is not None:
        return
        
    # 1. Load Precomputed Embeddings
    try:
        if not NPY_PATH.exists() or not META_PATH.exists() or not SCHEMES_JSON_PATH.exists():
            print("WARNING: Precomputed embeddings or metadata not found. Disabling semantic matching.")
            SEMANTIC_DISABLED = True
            return
            
        # Check SHA-256 hash match to avoid stale embeddings
        current_hash = get_sha256(SCHEMES_JSON_PATH)
        with META_PATH.open("r", encoding="utf-8") as f:
            meta = json.load(f)
            
        if meta.get("sha256") != current_hash:
            print(f"WARNING: schemes_full.json hash mismatch (computed: {current_hash[:8]}, cached: {meta.get('sha256')[:8]}). "
                  "Precomputed embeddings are stale! Please run `python scripts/build_embeddings.py` to regenerate. "
                  "Semantic matching is disabled.")
            SEMANTIC_DISABLED = True
            return
            
        _EMBEDDINGS = np.load(NPY_PATH)
        print(f"SUCCESS: Loaded precomputed scheme embeddings matrix of shape {_EMBEDDINGS.shape} in <10ms.")
    except Exception as e:
        print(f"CRITICAL: Failed to load precomputed embeddings. Fallback to keyword-only matching. Error: {e}", file=sys.stderr)
        SEMANTIC_DISABLED = True
        return

    # 2. Load the Embedding Model for User Queries
    try:
        from sentence_transformers import SentenceTransformer
        if eager_warm and _MODEL is None:
            print("Eager-loading SentenceTransformer('all-MiniLM-L6-v2')...")
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            # Run a quick warm-up query
            _MODEL.encode("warmup query")
            print("SentenceTransformer successfully loaded and warmed up.")
    except Exception as e:
        print(f"CRITICAL: Failed to load SentenceTransformer library or model. Fallback to keyword-only matching. Error: {e}", file=sys.stderr)
        SEMANTIC_DISABLED = True


def get_query_embedding(query: str) -> np.ndarray | None:
    """
    Encodes the query into a normalized vector. Lazy-loads the model if not eager-loaded.
    """
    global _MODEL, SEMANTIC_DISABLED
    if SEMANTIC_DISABLED:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        if _MODEL is None:
            print("Lazy-loading SentenceTransformer('all-MiniLM-L6-v2')...")
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        return _MODEL.encode(query, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as e:
        print(f"WARNING: Error encoding user query. Disabling semantic matching for this request. Error: {e}", file=sys.stderr)
        return None


def dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


def to_candidate(raw: dict) -> SchemeCandidate:
    # Safely wrap string fields to lists to prevent Pydantic string-to-list-of-chars conversion
    category = raw.get("category")
    if isinstance(category, str):
        category = [category]
    elif not isinstance(category, list):
        category = []

    state = raw.get("state") or raw.get("eligibility", {}).get("state") or []
    if isinstance(state, str):
        state = [state]
    elif not isinstance(state, list):
        state = []

    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = []

    return SchemeCandidate(
        scheme_id=raw.get("scheme_id") or raw.get("id", ""),
        scheme_name=raw.get("scheme_name") or raw.get("name", "Unknown Scheme"),
        category=category,
        eligibility=raw.get("eligibility", {}) or {},
        benefit=raw.get("benefit", "") or "",
        documents_required=raw.get("documents_required", []) or [],
        portal=raw.get("portal", "") or "",
        helpline=raw.get("helpline", "") or "",
        application_mode=raw.get("application_mode", "") or "",
        state=state,
        tags=tags,
        brief_description=raw.get("brief_description", "") or raw.get("description", "") or "",
        close_date=raw.get("close_date"),
        clarification_group=raw.get("clarification_group"),
        clarification_question=raw.get("clarification_question"),
    )


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


# --- Deterministic Rules Engine (Policy-as-Code) ---
def audit_eligibility(eligibility_rules: dict, ctx: dict) -> dict[str, list[str]]:
    """
    Evaluates hard constraints (Policy-as-Code) rather than fuzzy keyword matching.
    """
    audit = {"passed": [], "failed": [], "missing": []}
    
    # 1. Age Check
    min_age = eligibility_rules.get("age_min") if eligibility_rules.get("age_min") is not None else eligibility_rules.get("min_age")
    max_age = eligibility_rules.get("age_max") if eligibility_rules.get("age_max") is not None else eligibility_rules.get("max_age")
    if min_age is not None or max_age is not None:
        user_age = ctx.get("age")
        if user_age is not None:
            if (min_age and user_age < min_age) or (max_age and user_age > max_age):
                audit["failed"].append(f"Age {user_age} outside allowed range ({min_age or 0}-{max_age or 'any'}).")
            else:
                audit["passed"].append("Age requirement met.")
        else:
            audit["missing"].append("Age")

    # 2. Income Check
    max_income = eligibility_rules.get("max_annual_income") if eligibility_rules.get("max_annual_income") is not None else eligibility_rules.get("max_income")
    if max_income is not None:
        user_income = ctx.get("income")
        if user_income is not None:
            if user_income > max_income:
                audit["failed"].append(f"Income ₹{user_income} exceeds limit of ₹{max_income}.")
            else:
                audit["passed"].append("Income requirement met.")
        else:
            audit["missing"].append("Annual Income")

    # 3. Gender Check
    target_gender = eligibility_rules.get("gender")
    if target_gender:
        if isinstance(target_gender, str):
            genders = [target_gender.lower().strip()]
        elif isinstance(target_gender, list):
            genders = [str(g).lower().strip() for g in target_gender]
        else:
            genders = []

        restricted_genders = [g for g in genders if g not in ("", "all", "any", "both", "both genders")]
        if restricted_genders:
            user_gender = str(ctx.get("gender") or "").lower().strip()
            if user_gender:
                if not any(user_gender in g or g in user_gender for g in restricted_genders):
                    audit["failed"].append(f"Scheme is restricted to {', '.join(target_gender) if isinstance(target_gender, list) else target_gender}s.")
                else:
                    audit["passed"].append("Gender requirement met.")
            else:
                audit["missing"].append("Gender")

    # 4. Caste Check
    target_caste = eligibility_rules.get("caste")
    if target_caste:
        if isinstance(target_caste, str):
            scheme_castes = [normalize_caste(target_caste)]
        elif isinstance(target_caste, list):
            scheme_castes = [normalize_caste(c) for c in target_caste]
        else:
            scheme_castes = []

        restricted_castes = [c for c in scheme_castes if c != "GENERAL"]
        if restricted_castes:
            user_caste = normalize_caste(ctx.get("caste"))
            if ctx.get("caste"):
                if user_caste not in restricted_castes:
                    audit["failed"].append(f"Scheme is restricted to {', '.join(target_caste) if isinstance(target_caste, list) else target_caste} category.")
                else:
                    audit["passed"].append("Caste category requirement met.")
            else:
                audit["missing"].append("Caste Category")

    # 5. Required Programs Check
    scheme_programs = eligibility_rules.get("required_programs", [])
    if scheme_programs:
        user_programs = ctx.get("enrolled_programs", [])
        unconfirmed = [
            p for p in scheme_programs 
            if p not in user_programs
        ]
        if unconfirmed:
            audit["missing"].append(
                f"Program enrollment: {', '.join(unconfirmed)}"
            )
        else:
            for program in scheme_programs:
                audit["passed"].append(f"Enrolled in required program: {program}.")

    return audit


def stem_word(w: str) -> str:
    """
    Extremely simple suffix-stripping English word stemmer to unify singulars/plurals.
    """
    w = w.lower().strip()
    if len(w) > 3:
        if w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        elif w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith("ing"):
            w = w[:-3]
        elif w.endswith("ed"):
            w = w[:-2]
    return w


def score_scheme(scheme: dict, ctx: dict, case_ctx: dict, query_emb: np.ndarray | None = None, scheme_index: int | None = None) -> tuple[int, list[str]]:
    # ==============================================================================
    # HYBRID RETRIEVAL SCORING FORMULA
    # ==============================================================================
    # Final Score = Relevance Score * (1.0 + Demographic Multiplier)
    #
    # 1. Relevance Score (0 - 100):
    #    - Keyword Relevance: Fraction of unique query terms matching the scheme's name 
    #      (weighted 70%) or description/text (weighted 30%), including synonyms.
    #    - Semantic Relevance: Min-max scaled cosine similarity mapping active baseline
    #      [0.15, 0.55] to [0.0, 100.0].
    #    - Weighted Blend: 0.60 * Semantic Relevance + 0.40 * Keyword Relevance.
    # 2. Demographic Multiplier (Amplification Factor):
    #    - State Match: +0.20 (if state-specific) or +0.10 (if national open)
    #    - Occupation Match: +0.15
    #    - Caste Match: +0.15
    #    - Gender Match: +0.15
    #    - Extreme Case Max DM: 0.20 + 0.15 + 0.15 + 0.15 = +0.65 (1.65x multiplier)
    #    - Extreme Case Min DM: +0.10 (1.10x multiplier)
    # 3. Hard Stateless Filter:
    #    - If scheme is state-restricted (state is not ["All"] and is non-empty),
    #      and user state is unknown/null -> STRICTLY EXCLUDED (returns -999).
    # ==============================================================================
    reasons: list[str] = []

    eligibility = scheme.get("eligibility", {}) or {}
    raw_states = scheme.get("state") or eligibility.get("state") or []
    if isinstance(raw_states, str):
        raw_states = [raw_states]
    states_str = " ".join(raw_states)

    text = " ".join([
        scheme.get("scheme_name", ""),
        scheme.get("brief_description", ""),
        " ".join(scheme.get("tags", []) or []),
        " ".join(scheme.get("category", []) or []),
        states_str
    ]).lower()
    problem_blob = " ".join(str(ctx.get(key, "") or "") for key in ["problem_statement", "problem_category"]).lower()
    
    user_state = (ctx.get("state") or "").lower().strip()
    occupation = (ctx.get("occupation") or "").lower().strip()

    # 1. State Routing and Strict Exclusion Filter
    raw_states = scheme.get("state") or eligibility.get("state") or []
    if isinstance(raw_states, str):
        raw_states = [raw_states]
    scheme_states = [str(s).lower().strip() for s in raw_states]
    scheme_states = [s for s in scheme_states if s]
    
    is_state_penalized = False
    if user_state:
        if scheme_states and not any(s == "all" or user_state in s or s in user_state for s in scheme_states):
            return None, ["State mismatch"]
    else:
        # User state is unknown: enforce three-tier state matching logic
        is_restricted = scheme_states and not any(s == "all" for s in scheme_states)
        if is_restricted:
            is_state_penalized = True
            reasons.append("State-restricted scheme with unknown user state (0.7x multiplier applied)")

    # 2. Demographic Multiplier Calculation
    demographic_multiplier = 0.0

    # 2.1 State Alignment Boost
    if user_state:
        if scheme_states:
            if any(user_state in s or s in user_state for s in scheme_states if s != "all"):
                demographic_multiplier += 0.20
                reasons.append(f"Highly relevant state-specific match (+20% amplification)")
            elif any(s == "all" for s in scheme_states):
                demographic_multiplier += 0.10
                reasons.append(f"Nationwide match (+10% amplification)")
    else:
        # Nationwide scheme matches stateless query
        demographic_multiplier += 0.10

    # 2.2 Occupation Alignment
    scheme_occ = [str(o).lower().strip() for o in (eligibility.get("occupation") or [])]
    scheme_occ = [o for o in scheme_occ if o]
    if occupation:
        if scheme_occ:
            if any(occupation in o or o in occupation for o in scheme_occ):
                demographic_multiplier += 0.15
                reasons.append(f"Fits your role as {ctx.get('occupation')} (+15% amplification)")
            else:
                demographic_multiplier -= 0.20
    else:
        if scheme_occ:
            demographic_multiplier -= 0.15

    # 2.3 Caste Alignment
    target_caste = eligibility.get("caste")
    if target_caste:
        if isinstance(target_caste, str):
            scheme_castes = [normalize_caste(target_caste)]
        elif isinstance(target_caste, list):
            scheme_castes = [normalize_caste(c) for c in target_caste]
        else:
            scheme_castes = []
        restricted_castes = [c for c in scheme_castes if c != "GENERAL"]
        
        user_caste = normalize_caste(ctx.get("caste"))
        if restricted_castes:
            if ctx.get("caste"):
                if user_caste in restricted_castes:
                    demographic_multiplier += 0.15
                    reasons.append(f"Caste category requirement met (+15% amplification)")
                else:
                    demographic_multiplier -= 0.25
            else:
                demographic_multiplier -= 0.15

    # 2.4 Gender Alignment
    target_gender = eligibility.get("gender")
    if target_gender:
        if isinstance(target_gender, str):
            scheme_genders = [target_gender.lower().strip()]
        elif isinstance(target_gender, list):
            scheme_genders = [str(g).lower().strip() for g in target_gender]
        else:
            scheme_genders = []
        restricted_genders = [g for g in scheme_genders if g not in ("", "all", "any", "both", "both genders")]
        
        user_gender = (ctx.get("gender") or "").lower().strip()
        if restricted_genders:
            if user_gender:
                if any(user_gender in rg or rg in user_gender for rg in restricted_genders):
                    demographic_multiplier += 0.15
                    reasons.append(f"Gender requirement met (+15% amplification)")
                else:
                    demographic_multiplier -= 0.25
            else:
                demographic_multiplier -= 0.15

    # 3. Relevance Score Calculation (0 - 100)
    STOPWORDS = {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
        "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", 
        "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", 
        "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", 
        "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
        "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", 
        "with", "about", "against", "between", "into", "through", "during", "before", "after", 
        "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", 
        "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", 
        "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", 
        "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", 
        "should", "now", "need", "seeking", "assistance", "want", "support", "help", "scheme", 
        "schemes", "yojana", "yojna", "government", "govt", "india", "indian", "state", "district",
        "beneficiary", "beneficiaries", "eligible"
    }

    SYNONYMS = {
        "insurance": {"bima", "insurance", "risk cover", "insurances"},
        "crop": {"fasal", "crop", "crops", "agriculture", "farming"},
        "farmer": {"kisan", "krishak", "farmer", "farmers"},
        "pension": {"pension", "old age", "vriddha", "destitute", "labourer", "labourers"},
        "goat": {"bakri", "goat", "goats", "livestock", "sheep"},
        "sheep": {"bhed", "sheep", "goat", "goats"},
        "cow": {"gai", "cow", "cows", "livestock", "dairy"},
        "employment": {"employment", "job", "livelihood", "rozgar", "berozgar", "work"},
        "unemployed": {"unemployed", "berozgar", "jobless"},
        "credit": {"credit", "card", "loan", "loans", "borrow", "debt", "kcc", "cash", "finance", "input"},
        "mahila": {"women", "female", "mahila"},
        "fish": {"fish", "fishery", "fisheries", "matsya", "machhli", "machli", "aquaculture"}
    }

    # 3.1 Keyword Relevance Score (0 - 100)
    keyword_relevance = 0.0
    matched_name_words = set()
    if problem_blob:
        blob_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", problem_blob) if w not in STOPWORDS}
        
        if blob_words:
            text_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", text) if w not in STOPWORDS}
            
            matched_query_words = set()
            for bw in blob_words:
                if bw in text_words:
                    matched_query_words.add(bw)
                else:
                    matched = False
                    for canon, syns in SYNONYMS.items():
                        stemmed_syns = {stem_word(s) for s in syns}
                        if bw in stemmed_syns or bw == stem_word(canon):
                            if any(s in text_words for s in stemmed_syns):
                                matched = True
                                break
                    if matched:
                        matched_query_words.add(bw)
                        
            name_text = scheme.get("scheme_name", "").lower()
            name_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", name_text) if w not in STOPWORDS}
            
            matched_name_words = set()
            for bw in blob_words:
                if bw in name_words:
                    matched_name_words.add(bw)
                else:
                    matched = False
                    for canon, syns in SYNONYMS.items():
                        stemmed_syns = {stem_word(s) for s in syns}
                        if bw in stemmed_syns or bw == stem_word(canon):
                            if any(s in name_words for s in stemmed_syns):
                                matched = True
                                break
                    if matched:
                        matched_name_words.add(bw)
                        
            # Raw additive overlap score capped at 100.0:
            raw_keyword_score = len(matched_name_words) * 35.0 + len(matched_query_words) * 15.0
            keyword_relevance = min(100.0, raw_keyword_score)
            
            # Direct boost for strong name overlap (3+ query terms matching the scheme's name)
            if len(matched_name_words) >= 3:
                keyword_relevance += 15.0

    # 3.2 Semantic Relevance Score (0 - 100)
    semantic_relevance = 0.0
    if not SEMANTIC_DISABLED and query_emb is not None and scheme_index is not None and _EMBEDDINGS is not None:
        similarity = float(np.dot(query_emb, _EMBEDDINGS[scheme_index]))
        if similarity >= 0.15:
            semantic_relevance = ((similarity - 0.15) / 0.40) * 100.0
            semantic_relevance = min(100.0, max(0.0, semantic_relevance))
            reasons.append(f"Semantic similarity: {round(similarity, 3)}")

    # 3.3 60/40 Weighted Blend
    relevance_score = 0.60 * semantic_relevance + 0.40 * keyword_relevance

    # 4. Multiplicative Score Merging
    final_score = int(round(relevance_score * (1.0 + demographic_multiplier)))
    if is_state_penalized:
        final_score = int(round(final_score * 0.7))
    return final_score, reasons


def make_action_steps(scheme: dict, ctx: dict, case_ctx: dict) -> list[str]:
    steps: list[str] = []
    app_mode = (scheme.get("application_mode") or "").lower().strip()
    district = ctx.get("district")

    if is_case_followup(case_ctx):
        return build_case_followup_steps(ctx, case_ctx)
    
    if app_mode == "offline":
        steps.append("Visit the nearest CSC, block office, or department office for offline submission.")
    elif app_mode == "online":
        steps.append("Apply through the official portal.")
    
    if district:
        steps.append(f"Use your district-level office or CSC in {district} for local help.")

    return steps[:3]


def filter_candidates(all_schemes: list[dict]) -> list[SchemeCandidate]:
    candidates: list[SchemeCandidate] = []
    for scheme in all_schemes:
        if not is_closed_scheme(scheme):
            try:
                candidates.append(to_candidate(scheme))
            except ValidationError:
                continue
    return candidates


def tokenize(text: str) -> set[str]:
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return set(cleaned.split())


def find_exact_name_match(query, candidates):
    query_tokens = tokenize(query)
    
    # Only check audit-passing candidates
    eligible = [
        c for c in candidates 
        if c.get("confidence") != "INELIGIBLE"
    ]
    
    best_candidates = []
    best_ratio = -1.0
    best_overlap = -1
    
    GENERIC_WORDS = {
        "scheme", "yojana", "yojna", "assistance", "support", "help",
        "government", "govt", "state", "national", "central", "department",
        "ministry", "board", "corporation", "society", "cooperative",
        "limited", "ltd", "private", "pvt", "public", "association",
        "trust", "foundation", "commission", "committee", "authority",
        "agency", "council", "federation", "union", "chamber", "group",
        "insurance", "subsidy", "loan", "credit", "grant", "pension",
        "scholarship", "fellowship", "stipend", "award", "prize",
        "training", "development", "welfare", "benefit", "incentive",
        "program", "programme", "project", "mission", "campaign",
        "drive", "initiative", "under", "for", "to", "of", "and", "in", "the", "a", "an"
    }
    DEMOGRAPHIC_WORDS = {
        "tamil", "nadu", "bihar", "gujarat", "haryana", "meghalaya", "assam", "uttarakhand",
        "uttar", "pradesh", "madhya", "himachal", "arunachal", "andhra", "jammu", "kashmir",
        "west", "bengal", "goa", "karnataka", "kerala", "maharashtra", "manipur", "mizoram",
        "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "telangana", "tripura", "jharkhand",
        "chhattisgarh", "delhi", "puducherry", "chandigarh", "ladakh", "lakshadweep", "daman", "diu",
        "sc", "st", "obc", "ebc", "bpl", "apl", "general", "caste", "castes", "tribe", "tribes",
        "scheduled", "backward", "minority", "minorities", "women", "woman", "female", "girl",
        "girls", "widow", "widows", "male", "men", "man", "boy", "boys", "children", "child",
        "elderly", "senior", "citizen", "citizens", "youth"
    }
    all_common = COMMON_SCHEME_WORDS | GENERIC_WORDS | DEMOGRAPHIC_WORDS
    
    for candidate in eligible:
        name_tokens = tokenize(candidate["name"])
        distinctive = name_tokens - all_common
        
        if not distinctive:
            continue
            
        if len(distinctive) == 1 and len(name_tokens) > 2:
            continue
        
        overlap = query_tokens & distinctive
        ratio = len(overlap) / len(distinctive)
        
        if ratio >= 0.6:
            if ratio > best_ratio:
                best_ratio = ratio
                best_overlap = len(overlap)
                best_candidates = [candidate["scheme_id"]]
            elif ratio == best_ratio:
                if len(overlap) > best_overlap:
                    best_overlap = len(overlap)
                    best_candidates = [candidate["scheme_id"]]
                elif len(overlap) == best_overlap:
                    best_candidates.append(candidate["scheme_id"])
    
    if len(best_candidates) == 1:
        return best_candidates[0]
    return None


def match_schemes(state: AgentState) -> AgentState:
    from app.language.sarvam import translate_to_english

    state["reranker_mode"] = "retrieval_only"
    all_schemes = load_schemes()
    ctx = state.get("user_context", {})
    case_ctx = state.get("case_context", {})

    # Build direct mapping from scheme_id to corpus index
    scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

    # Ensure matcher singletons are loaded/initialized at startup event (or lazy loaded now)
    init_matcher(eager_warm=False)

    # 1. Translate query to English if it is not already in English (via Sarvam pre-processing)
    raw_query = ctx.get("problem_statement") or state.get("user_input") or ""
    matching_query = translate_to_english(raw_query)
    
    # Expand acronyms for key terms
    matching_query = re.sub(r'\bkcc\b', 'kcc kishan credit card', matching_query, flags=re.IGNORECASE)

    # 2. Scoped context copy so that translations don't mutate state["user_context"]
    matching_ctx = dict(ctx)
    if raw_query:
        matching_ctx["problem_statement"] = matching_query

    # 3. Extract Intent & demographics via Groq (Phase 1)
    from app.agent.intent_extraction import extract_intent
    from app.agent.context import normalize_number, normalize_boolish
    intent_result = extract_intent(matching_query)
    
    # Clean and normalize demographics to prevent type crashes (e.g. string 'youth' for age)
    cleaned_demographics = {}
    for k, v in intent_result.extracted_demographics.items():
        if v in (None, "", [], {}):
            continue
        k_lower = k.lower().strip()
        if k_lower in {"age", "income", "land_owned"}:
            num_val = normalize_number(v)
            if num_val is not None:
                cleaned_demographics[k_lower] = num_val
        elif k_lower in {"aadhaar_linked", "bank_account", "ration_card", "bpl_status", "disability_status"}:
            bool_val = normalize_boolish(v)
            if bool_val is not None:
                cleaned_demographics[k_lower] = bool_val
        else:
            cleaned_demographics[k_lower] = str(v).strip()
            
    # Merge extracted demographics only for fields not already present/explicitly declared in user_context
    for field_name, field_val in cleaned_demographics.items():
        if field_name not in ctx or ctx.get(field_name) in (None, "", [], {}):
            matching_ctx[field_name] = field_val

    # Compute query embedding once per match request using the translated query
    query_emb = None
    if not SEMANTIC_DISABLED:
        if matching_query:
            query_emb = get_query_embedding(matching_query)

    candidates = filter_candidates(all_schemes)
    scored_candidates = []

    for candidate in candidates:
        raw = dump_model(candidate)
        scheme_id = raw.get("scheme_id")
        scheme_idx = scheme_id_to_index.get(scheme_id)

        # 1. Get Relevance Score (Hybrid) using the scoped context copy
        score, base_reasons = score_scheme(
            raw, 
            matching_ctx, 
            case_ctx, 
            query_emb, 
            scheme_idx
        )
        
        # 2. Run the Eligibility Audit using the scoped context copy
        audit = audit_eligibility(raw.get("eligibility", {}), matching_ctx)

        # Check demographic_match (FIX 3 / step 1 of demographic matching)
        demographic_match = False
        
        # State check
        user_state = (matching_ctx.get("state") or "").lower().strip()
        raw_states = raw.get("state") or raw.get("eligibility", {}).get("state") or []
        if isinstance(raw_states, str):
            raw_states = [raw_states]
        scheme_states = [str(s).lower().strip() for s in raw_states if s]
        
        state_match = False
        if user_state and scheme_states:
            if any(user_state in s or s in user_state for s in scheme_states if s not in ("all", "any")):
                state_match = True

        # Caste check
        user_caste = normalize_caste(matching_ctx.get("caste"))
        target_caste = raw.get("eligibility", {}).get("caste")
        if isinstance(target_caste, str):
            scheme_castes = [normalize_caste(target_caste)]
        elif isinstance(target_caste, list):
            scheme_castes = [normalize_caste(c) for c in target_caste]
        else:
            scheme_castes = []
        restricted_castes = [c for c in scheme_castes if c != "GENERAL"]
        
        caste_match = False
        if matching_ctx.get("caste") and restricted_castes:
            if user_caste in restricted_castes:
                caste_match = True

        # Gender check
        user_gender = (matching_ctx.get("gender") or "").lower().strip()
        target_gender = raw.get("eligibility", {}).get("gender")
        if isinstance(target_gender, str):
            scheme_genders = [target_gender.lower().strip()]
        elif isinstance(target_gender, list):
            scheme_genders = [str(g).lower().strip() for g in target_gender]
        else:
            scheme_genders = []
        restricted_genders = [g for g in scheme_genders if g not in ("", "all", "any", "both", "both genders")]
        
        gender_match = False
        if user_gender and restricted_genders:
            if any(user_gender in rg or rg in user_gender for rg in restricted_genders):
                gender_match = True

        if state_match or caste_match or gender_match:
            demographic_match = True

        raw["demographic_match"] = demographic_match
        
        # 3. Apply Hard Policy Constraints
        if score is None or audit["failed"]:
            confidence = "INELIGIBLE"
            score = -999 # Sink to bottom
        elif audit["passed"] and not audit["missing"]:
            confidence = "HIGH"
            score += 5 # Boost to top
        elif audit["missing"]:
            confidence = "NEEDS_VERIFICATION"
        else:
            confidence = "LIKELY" if score >= 4 else "NEEDS_VERIFICATION"

        # Determine if state verification is needed dynamically
        raw_states = raw.get("state") or raw.get("eligibility", {}).get("state") or []
        if isinstance(raw_states, str):
            raw_states = [raw_states]
        scheme_states = [str(s).lower().strip() for s in raw_states]
        scheme_states = [s for s in scheme_states if s]
        user_state = (ctx.get("state") or "").lower().strip()
        
        needs_state_verification = False
        if not user_state:
            is_restricted = scheme_states and not any(s == "all" for s in scheme_states)
            if is_restricted:
                needs_state_verification = True
                if "State" not in audit["missing"]:
                    audit["missing"].append("State")
                if confidence != "INELIGIBLE":
                    confidence = "NEEDS_VERIFICATION"

        if score is not None and (score > -500 or confidence == "NEEDS_VERIFICATION"):
            scored_candidates.append((score, confidence, raw, base_reasons, audit, needs_state_verification))

    # Sort by score descending and take top 10
    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    top_matches = scored_candidates[:10]

    # Check for low-confidence query (score < 35 or generic query, and user_context is empty or only contains occupation)
    top_score = top_matches[0][0] if top_matches else 0
    ctx_keys = [k for k, v in ctx.items() if v is not None and v != ""]
    is_empty_or_only_occupation = len(ctx_keys) == 0 or (len(ctx_keys) == 1 and "occupation" in ctx_keys)

    # Vague/generic query check (all words belong to generic/vague terms in English/Hindi)
    query_text = (ctx.get("problem_statement") or state.get("user_input") or "").lower().strip()
    query_words = re.findall(r"\b[a-z\u0900-\u097f]{2,}\b", query_text)
    
    GENERIC_TERMS = {
        "help", "scheme", "schemes", "yojana", "yojna", "government", "govt",
        "sarkari", "yojane", "madad", "chahiye", "paisa", "paise", "need", "want",
        "please", "kuch", "koi", "sir", "mam", "hello", "hi", "batao", "bataiye",
        "dikhao", "madd", "cahiye", "chahie", "dijiye", "dekhna", "deho",
        "मदद", "चाहिए", "पैसा", "पैसे", "सरकारी", "योजना", "योजनाएं", "सहायता"
    }
    
    is_generic = len(query_words) > 0 and all(w in GENERIC_TERMS for w in query_words)

    if (top_score < 35 or is_generic) and is_empty_or_only_occupation:
        state["is_low_confidence"] = True
        state["matched_schemes"] = []
        return state

    # 4. Data-Driven Clarification Check (FIX 4)
    from app.agent.clarification import detect_clarification_needed
    
    clarification_question = None
    if not ctx.get("clarification_resolved", False):
        schemes_lookup = {s.get("scheme_id"): s for s in all_schemes}
        top_candidates_dicts = [
            {"scheme_id": item[2].get("scheme_id")} for item in top_matches
        ]
        clar_res = detect_clarification_needed(top_candidates_dicts, schemes_lookup)
        if clar_res:
            clarification_question = clar_res.get("question")
            
    state["training_centre_clarification"] = clarification_question

    # 5. Rerank top 10 candidates
    from app.agent.reranker import rerank
    
    reranked_results = []
    reranker_mode = "retrieval_only"
    try:
        reranked_results, reranker_mode = rerank(matching_query, matching_ctx, top_matches)
    except Exception as e:
        print(f"Reranking failed or timed out: {e}. Falling back to top 5 retrieval candidates.")
        reranked_results = []
        reranker_mode = "retrieval_only"
    state["reranker_mode"] = reranker_mode
        
    if reranked_results:
        # Build mapping from scheme_id to candidate info
        candidates_map = {item[2].get("scheme_id"): item for item in top_matches}
        
        matches: list[SchemeMatch] = []
        for rank_item in reranked_results:
            scheme_id = rank_item["scheme_id"]
            if scheme_id in candidates_map:
                score, confidence, raw, base_reasons, audit, needs_state_verification = candidates_map[scheme_id]
                
                # Overwrite confidence from reranker
                conf = rank_item["confidence"]
                
                # Assemble deterministic user-facing reason card
                desc = raw.get("brief_description") or raw.get("description") or ""
                desc_truncated = desc[:200]
                if len(desc) > 200:
                    desc_truncated += "..."
                
                status_parts = []
                if conf == "HIGH":
                    status_parts.append("Eligibility Status: Fully Eligible (Meets all verified criteria).")
                elif conf == "LIKELY":
                    status_parts.append("Eligibility Status: Likely Eligible (Meets core criteria, some minor details unverified).")
                elif conf == "NEEDS_VERIFICATION":
                    status_parts.append("Eligibility Status: Needs Profile/State Verification.")
                
                if audit["missing"]:
                    missing_str = ", ".join(audit["missing"])
                    status_parts.append(f"Fields to verify: {missing_str}.")
                if needs_state_verification:
                    status_parts.append("Note: State residency needs to be verified.")
                
                status_text = " ".join(status_parts)
                reason_str = f"Description: {desc_truncated}\n{status_text}"
                
                matches.append(SchemeMatch(
                    scheme_id=raw.get("scheme_id", ""),
                    scheme_name=raw.get("scheme_name", "Unknown Scheme"),
                    confidence=conf,
                    reason=reason_str,
                    needs_state_verification=needs_state_verification,
                    passed_criteria=audit["passed"],
                    failed_criteria=audit["failed"],
                    missing_data=audit["missing"],
                    documents_required=raw.get("documents_required", []) or [],
                    action_steps=make_action_steps(raw, ctx, case_ctx),
                    portal=raw.get("portal") or None,
                    helpline=raw.get("helpline") or None,
                    clarification_group=raw.get("clarification_group"),
                    clarification_question=raw.get("clarification_question"),
                ))
    else:
        # Fallback to compiling top 5 raw retrieval candidates
        matches = []
        for score, confidence, raw, base_reasons, audit, needs_state_verification in top_matches[:5]:
            desc = raw.get("brief_description") or raw.get("description") or ""
            desc_truncated = desc[:200]
            if len(desc) > 200:
                desc_truncated += "..."
            
            status_parts = []
            if confidence == "HIGH":
                status_parts.append("Eligibility Status: Fully Eligible (Meets all verified criteria).")
            elif confidence == "LIKELY":
                status_parts.append("Eligibility Status: Likely Eligible (Meets core criteria, some minor details unverified).")
            elif confidence == "NEEDS_VERIFICATION":
                status_parts.append("Eligibility Status: Needs Profile/State Verification.")
            
            if audit["missing"]:
                missing_str = ", ".join(audit["missing"])
                status_parts.append(f"Fields to verify: {missing_str}.")
            if needs_state_verification:
                status_parts.append("Note: State residency needs to be verified.")
            
            status_text = " ".join(status_parts)
            reason_str = f"Description: {desc_truncated}\n{status_text}"

            matches.append(SchemeMatch(
                scheme_id=raw.get("scheme_id", ""),
                scheme_name=raw.get("scheme_name", "Unknown Scheme"),
                confidence=confidence,
                reason=reason_str,
                needs_state_verification=needs_state_verification,
                passed_criteria=audit["passed"],
                failed_criteria=audit["failed"],
                missing_data=audit["missing"],
                documents_required=raw.get("documents_required", []) or [],
                action_steps=make_action_steps(raw, ctx, case_ctx),
                portal=raw.get("portal") or None,
                helpline=raw.get("helpline") or None,
                clarification_group=raw.get("clarification_group"),
                clarification_question=raw.get("clarification_question"),
            ))

    # Exact proper noun match pre-emption (FIX 3)
    # Build candidates format with confidence, name, and scheme_id
    audit_candidates = []
    for item in scored_candidates:
        score_val, conf_val, raw_val, base_reasons_val, audit_val, needs_state_verification_val = item
        audit_candidates.append({
            "confidence": conf_val,
            "name": raw_val.get("scheme_name") or raw_val.get("name") or "",
            "scheme_id": raw_val.get("scheme_id")
        })
        
    matched_scheme_id = find_exact_name_match(matching_query, audit_candidates)
    if matched_scheme_id:
        # Find if this scheme is already in matches
        match_idx = None
        for i, match in enumerate(matches):
            if match.scheme_id == matched_scheme_id:
                match_idx = i
                break
        
        if match_idx is not None:
            if match_idx > 0:
                matched_item = matches.pop(match_idx)
                matches.insert(0, matched_item)
        else:
            # If not in matches (e.g. cut off by reranking), build and prepend it from scored_candidates
            cand_item = None
            for item in scored_candidates:
                if item[2].get("scheme_id") == matched_scheme_id:
                    cand_item = item
                    break
            
            if cand_item:
                score, confidence, raw, base_reasons, audit, needs_state_verification = cand_item
                
                desc = raw.get("brief_description") or raw.get("description") or ""
                desc_truncated = desc[:200]
                if len(desc) > 200:
                    desc_truncated += "..."
                
                status_parts = []
                if confidence == "HIGH":
                    status_parts.append("Eligibility Status: Fully Eligible (Meets all verified criteria).")
                elif confidence == "LIKELY":
                    status_parts.append("Eligibility Status: Likely Eligible (Meets core criteria, some minor details unverified).")
                elif confidence == "NEEDS_VERIFICATION":
                    status_parts.append("Eligibility Status: Needs Profile/State Verification.")
                
                if audit["missing"]:
                    missing_str = ", ".join(audit["missing"])
                    status_parts.append(f"Fields to verify: {missing_str}.")
                if needs_state_verification:
                    status_parts.append("Note: State residency needs to be verified.")
                
                status_text = " ".join(status_parts)
                reason_str = f"Description: {desc_truncated}\n{status_text}"
                
                match_obj = SchemeMatch(
                    scheme_id=raw.get("scheme_id", ""),
                    scheme_name=raw.get("scheme_name", "Unknown Scheme"),
                    confidence=confidence,
                    reason=reason_str,
                    needs_state_verification=needs_state_verification,
                    passed_criteria=audit["passed"],
                    failed_criteria=audit["failed"],
                    missing_data=audit["missing"],
                    documents_required=raw.get("documents_required", []) or [],
                    action_steps=make_action_steps(raw, ctx, case_ctx),
                    portal=raw.get("portal") or None,
                    helpline=raw.get("helpline") or None,
                    clarification_group=raw.get("clarification_group"),
                    clarification_question=raw.get("clarification_question"),
                )
                
                matches.insert(0, match_obj)
                if len(matches) > 5:
                    matches = matches[:5]

    state["matched_schemes"] = [dump_model(match) for match in matches]
    return state