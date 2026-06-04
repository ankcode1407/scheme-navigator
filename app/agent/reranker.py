from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder
from app.agent.context import normalize_caste

load_dotenv()

logger = logging.getLogger("reranker")

# Control Switch Circuit Breaker (Default: True)
GROQ_RERANKING_ENABLED = os.getenv("GROQ_RERANKING_ENABLED", "True").strip().lower() == "true"

# Load local CrossEncoder at module load time (pre-cached at build time)
try:
    _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    logger.info("Successfully loaded local CrossEncoder fallback model.")
except Exception as e:
    logger.error(f"Failed to load local CrossEncoder fallback model: {e}")
    _cross_encoder = None

def edit_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def find_closest_candidate_id(returned_id: str, candidate_ids: list[str]) -> str | None:
    returned_id_clean = returned_id.strip().lower()
    if not returned_id_clean:
        return None
    
    # 1. Exact match (case-insensitive)
    for c_id in candidate_ids:
        if c_id.lower() == returned_id_clean:
            return c_id
            
    # 2. Simple substring / common prefix match
    for c_id in candidate_ids:
        c_id_lower = c_id.lower()
        if (c_id_lower.startswith(returned_id_clean[:3]) or returned_id_clean.startswith(c_id_lower[:3])) and c_id_lower[0] == returned_id_clean[0]:
            return c_id
            
    # 3. General substring match
    for c_id in candidate_ids:
        c_id_lower = c_id.lower()
        if returned_id_clean in c_id_lower or c_id_lower in returned_id_clean:
            return c_id
            
    # 4. Levenshtein distance fallback (up to 3 edits)
    best_id = None
    min_dist = 999
    for c_id in candidate_ids:
        c_id_lower = c_id.lower()
        dist = edit_distance(returned_id_clean, c_id_lower)
        if dist < min_dist and dist <= 3:
            min_dist = dist
            best_id = c_id
            
    return best_id


class CandidateTuple(tuple):
    def get(self, key, default=None):
        if key == "demographic_match":
            return self[2].get("demographic_match", default)
        if key == "retrieval_score":
            return self[0]
        return default


def retrieval_has_demographic_confidence(candidates):
    if len(candidates) < 2:
        return False
    top = candidates[0]
    second = candidates[1]
    return (
        top.get("demographic_match", False) and 
        not second.get("demographic_match", False)
    )


def build_demographic_signals(scheme: dict, user_context: dict) -> str:
    caste = user_context.get("caste")
    state = user_context.get("state")
    demographics = []
    if caste:
        demographics.append(f"Caste: {normalize_caste(caste)}")
    if state:
        demographics.append(f"State: {state.strip().title()}")
        
    if demographics:
        return "Demographics: " + ", ".join(demographics) + "."
    return ""


def build_scheme_text(scheme: dict, user_context: dict) -> str:
    MAX_DESC_CHARS = 200  # safe for 512 tokens
    
    name = scheme.get("scheme_name") or scheme.get("name") or ""
    desc = (scheme.get("brief_description") or scheme.get("description") or "")[:MAX_DESC_CHARS]
    
    base = f"{name}. {desc}"
    
    # Demographic signals appended after truncation — never lost
    signals = build_demographic_signals(scheme, user_context)
    
    return f"{base} {signals}".strip()


def rerank_local(query: str, user_context: dict, candidates: list[tuple]) -> list[tuple]:
    """
    Reranks candidates using the offline CrossEncoder model.
    Each candidate is scored based on enriched scheme description with demographic context.
    """
    if _cross_encoder is None or not candidates:
        logger.warning("Local CrossEncoder model is None or candidates are empty. Returning candidates as-is.")
        return candidates

    # Convert tuples to CandidateTuple to support .get() access for demographic matching
    candidates = [CandidateTuple(cand) for cand in candidates]

    # Pre-emption check: trust retrieval order if it has demographic confidence
    if retrieval_has_demographic_confidence(candidates):
        logger.info("Retrieval has demographic confidence. Trusting retrieval order.")
        return candidates

    promotion_floor = int(os.getenv("RETRIEVAL_PROMOTION_FLOOR", "45"))
    
    promotable = [
        c for c in candidates 
        if c.get("retrieval_score", 0) >= promotion_floor
    ]
    floored = [
        c for c in candidates 
        if c.get("retrieval_score", 0) < promotion_floor
    ]
    
    if not promotable:
        return candidates

    pairs = []
    for cand in promotable:
        raw = cand[2]
        combined = build_scheme_text(raw, user_context)
        
        # Rough token estimate: chars / 4
        estimated_tokens = len(combined) / 4
        if estimated_tokens > 480:
            scheme_id = raw.get("scheme_id") or raw.get("id") or "Unknown"
            logger.warning(
                f"Scheme {scheme_id} text near "
                f"512-token limit: ~{estimated_tokens}"
            )
            
        pairs.append((query, combined))

    try:
        start_time = time.time()
        scores = _cross_encoder.predict(pairs)
        logger.info(f"Local CrossEncoder finished in {(time.time() - start_time)*1000:.2f} ms")
        
        # Map zip(scores, promotable) into dicts for sorting
        dict_candidates = []
        for score, cand in zip(scores, promotable):
            dict_candidates.append({
                "confidence": cand[1],
                "cross_encoder_score": float(score),
                "original_cand": cand
            })

        CONFIDENCE_RANK = {
            "HIGH": 0,
            "LIKELY": 1,
            "NEEDS_VERIFICATION": 2,
            "INELIGIBLE": 999
        }

        dict_candidates.sort(key=lambda x: (
            CONFIDENCE_RANK.get(
                x.get("confidence", "LIKELY"), 1
            ),
            -x["cross_encoder_score"]
        ))

        ranked = [x["original_cand"] for x in dict_candidates]
        return ranked + floored
    except Exception as e:
        logger.error(f"Local CrossEncoder scoring failed: {e}")
        return candidates


def rerank(query: str, user_context: dict[str, Any], candidates: list[tuple]) -> tuple[list[dict[str, Any]], str]:
    """
    Reranks up to 20 candidate schemes using Groq (llama-3.3-70b-versatile with llama-3.1-8b-instant fallback),
    with a local CrossEncoder model as a tertiary offline fallback.
    
    Each candidate in 'candidates' is a tuple:
      (score, confidence, raw_scheme, base_reasons, audit, needs_state_verification)
    
    Returns a tuple:
      (ranked_candidates_list, reranker_mode_str)
    """
    if not candidates:
        return [], "retrieval_only"

    candidate_ids = [str(c[2].get("scheme_id")).strip() for c in candidates if c[2] and c[2].get("scheme_id")]

    last_error = None
    if GROQ_RERANKING_ENABLED:
        # 1. Format candidate list for prompt (keep it compact but detailed)
        candidates_formatted = []
        for idx, (score, conf, raw, reasons, audit, state_verif) in enumerate(candidates[:20]):
            elig = raw.get("eligibility", {}) or {}
            # Clean eligibility rules to save tokens
            clean_elig = {k: v for k, v in elig.items() if v not in (None, "", [], {})}
            
            cand_str = (
                f"Candidate {idx+1}:\n"
                f"  ID: {raw.get('scheme_id')}\n"
                f"  Name: {raw.get('scheme_name')}\n"
                f"  Category: {raw.get('category')}\n"
                f"  State Restriction: {raw.get('state')}\n"
                f"  Eligibility Rules: {clean_elig}\n"
                f"  Benefit: {raw.get('benefit')}\n"
                f"  Description: {raw.get('brief_description')}\n"
                f"  Rule Audit: {audit}\n"
            )
            candidates_formatted.append(cand_str)
        
        candidates_text = "\n".join(candidates_formatted)
        
        # 2. System and User Prompt setup
        system_prompt = (
            "You are an expert citizen scheme eligibility and relevance reranking engine for an Indian government scheme navigator.\n"
            "Your task is to select and rank the top 5 most relevant and eligible schemes from a list of up to 20 candidate schemes based on the user's query and their demographic context.\n"
            "Return ONLY a valid JSON object matching the requested schema. No markdown fences, no preamble, and no explanation.\n\n"
            "Schema:\n"
            "{\n"
            '  "rankings": [\n'
            "    {\n"
            '      "scheme_id": "string (the exact ID of the candidate scheme)",\n'
            '      "confidence": "string (one of: \\"HIGH\\", \\"LIKELY\\", \\"NEEDS_VERIFICATION\\")"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Guidelines:\n"
            "1. Check the User Context carefully against the Eligibility Rules and the Rule Audit. The Rule Audit shows which criteria passed, failed, or are missing.\n"
            "2. HIGH: User fully meets all eligibility criteria.\n"
            "3. LIKELY: User fits the primary domain/intent of the scheme, but there are minor missing details.\n"
            "4. NEEDS_VERIFICATION: User meets some criteria but is missing critical fields (e.g. state residency) that must be verified.\n"
            "5. Do not include schemes where the Rule Audit explicitly failed critical conditions (e.g. age or income limits) unless no other relevant schemes exist.\n"
            "6. Return up to 5 schemes. If fewer than 5 are relevant or eligible, return only those."
        )
        
        user_prompt = (
            f"User Query: \"{query}\"\n"
            f"User Context:\n"
            f"{json.dumps(user_context, indent=2)}\n\n"
            f"Candidate Schemes:\n"
            f"{candidates_text}\n\n"
            f"Output JSON:"
        )

        from app.agent.nodes import get_groq_client_no_retries
        try:
            client = get_groq_client_no_retries()
        except Exception as e:
            client = None
            last_error = e

        if client:
            models = [
                {"name": "llama-3.3-70b-versatile", "timeout": 2.5},
                {"name": "llama-3.1-8b-instant", "timeout": 2.0}
            ]
            
            for model_info in models:
                model_name = model_info["name"]
                timeout_val = model_info["timeout"]
                
                max_attempts = 3
                retry_delay = 3.0
                
                for attempt in range(max_attempts):
                    try:
                        logger.info(f"Invoking reranker model: {model_name} (Attempt {attempt+1}/{max_attempts})...")
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0,
                            max_tokens=800,
                            timeout=timeout_val
                        )
                        
                        raw = completion.choices[0].message.content or "{}"
                        raw = raw.strip()
                        
                        # Remove markdown JSON blocks if present
                        if raw.startswith("```"):
                            lines = raw.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].endswith("```"):
                                lines = lines[:-1]
                            raw = "\n".join(lines).strip()
                        
                        data = json.loads(raw)
                        rankings = data.get("rankings", [])
                        if not isinstance(rankings, list):
                            raise ValueError("JSON response rankings field is not a list")
                            
                        # Basic validation with fuzzy ID matching mapping
                        valid_rankings = []
                        for r in rankings:
                            if "scheme_id" in r:
                                raw_id = str(r["scheme_id"]).strip()
                                mapped_id = find_closest_candidate_id(raw_id, candidate_ids)
                                if mapped_id:
                                    valid_rankings.append({
                                        "scheme_id": mapped_id,
                                        "confidence": str(r.get("confidence", "NEEDS_VERIFICATION")).strip().upper()
                                    })
                        mode = "groq_primary" if "70b" in model_name else "groq_fallback"
                        return valid_rankings, mode
                        
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        logger.warning(f"Reranker model {model_name} (Attempt {attempt+1}/{max_attempts}) failed. Error: {e}")
                        
                        # If it's a daily rate limit (TPD), do not retry, break to move to next model instantly
                        if "TPD" in err_str or "tokens per day" in err_str or "Tokens Per Day" in err_str:
                            logger.warning(f"Groq Daily Token Limit hit on reranker for {model_name}. Short-circuiting model.")
                            break
                        
                        # If it is a TPM / general rate limit 429, retry
                        if "429" in err_str or "rate_limit" in err_str or "Rate limit" in err_str:
                            if attempt < max_attempts - 1:
                                sleep_time = retry_delay
                                match = re.search(r"try again in (\d+\.?\d*)s", err_str)
                                if match:
                                    sleep_time = float(match.group(1)) + 0.1
                                logger.warning(f"Groq Rate Limit hit on reranker for {model_name}. Retrying in {sleep_time:.2f}s...")
                                time.sleep(sleep_time)
                                continue
                        
                        # For other errors, do not retry, just break to next model
                        break
    else:
        last_error = RuntimeError("Groq reranking is disabled.")

    # 4. Tertiary Fallback: Local CrossEncoder reranking
    logger.warning(f"Groq reranking unavailable ({last_error}). Falling back to local CrossEncoder...")
    try:
        local_sorted = rerank_local(query, user_context, candidates)
        valid_rankings = []
        for cand in local_sorted[:5]:
            raw_scheme = cand[2]
            valid_rankings.append({
                "scheme_id": raw_scheme.get("scheme_id"),
                "confidence": cand[1]
            })
        return valid_rankings, "cross_encoder"
    except Exception as e:
        logger.error(f"Local CrossEncoder fallback failed: {e}")
        
    # If even local CrossEncoder fails, raise error to fall back to raw retrieval order in match_schemes
    raise RuntimeError(f"Reranking failed on all models and local fallback. Last error: {last_error}")
