from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# Setup standard logger
logger = logging.getLogger("intent_extractor")

# Control Switch Circuit Breaker (Default: True)
GROQ_INTENT_EXTRACTION_ENABLED = os.getenv("GROQ_INTENT_EXTRACTION_ENABLED", "True").strip().lower() == "true"

@dataclass
class IntentResult:
    primary_domain: str
    # One of: "agriculture", "livestock", "education",
    # "employment", "health", "housing", "financial",
    # "skill_development", "tribal", "disaster_relief",
    # "women", "elderly", "unclear"
    
    key_concepts: list[str] = field(default_factory=list)
    # English keywords extracted from query
    # e.g. ["crop", "insurance", "damage"]
    
    extracted_demographics: dict = field(default_factory=dict)
    # Any demographics found in query text
    # e.g. {"state": "Bihar", "caste": "SC", "age": 25}
    # Empty dict if none found
    
    confidence: str = "low"
    # "high" / "low" based on query clarity

def extract_intent(query: str) -> IntentResult:
    """
    Structured intent extractor using Groq (llama-3.3-70b-versatile).
    Returns an IntentResult dataclass containing domain, key concepts, and demographics.
    Falls back gracefully to a default IntentResult on failure or timeout (1.5s limit).
    """
    fallback_result = IntentResult(
        primary_domain="unclear",
        key_concepts=[],
        extracted_demographics={},
        confidence="low"
    )

    if not GROQ_INTENT_EXTRACTION_ENABLED:
        return fallback_result

    if not query or not query.strip():
        return fallback_result

    import time
    import re
    from app.agent.nodes import get_groq_client_no_retries

    max_retries = 3
    retry_delay = 3.0

    for attempt in range(max_retries):
        try:
            client = get_groq_client_no_retries()
            
            system_prompt = (
                "You are a precise citizen query intent extractor for an Indian government scheme navigator.\n"
                "Your task is to parse a query and return ONLY a valid JSON object. No markdown blocks, no markdown fences, no preamble, and no explanation.\n\n"
                "The JSON object must strictly match this schema:\n"
                "{\n"
                '  "primary_domain": string (one of: "agriculture", "livestock", "education", "employment", "health", "housing", "financial", "skill_development", "tribal", "disaster_relief", "women", "elderly", "unclear"),\n'
                '  "key_concepts": list of strings (English keywords and concepts extracted from query),\n'
                '  "extracted_demographics": object (key-value mapping of demographics found, such as "state", "caste", "gender", "age", "occupation", "marital_status". Use standard normalized strings if possible. Return empty object if none found),\n'
                '  "confidence": string ("high" or "low")\n'
                "}\n\n"
                "Rules:\n"
                "1. Do not include markdown JSON formatting (e.g. do not wrap the output in ```json ... ```).\n"
                "2. Translate all concepts and keywords to English for key_concepts.\n"
                "3. Demographics should capture explicitly mentioned details in the query (e.g. \"Bihar\", \"Scheduled Caste\" or \"SC\", \"women\", \"farmer\")."
            )
            
            user_prompt = (
                f"Here are some examples of inputs and outputs:\n\n"
                f"Example 1 — Transliterated Hindi agricultural:\n"
                f"Query: \"meri fasal kharab ho gayi\"\n"
                f"Output:\n"
                f'{{\n  "primary_domain": "agriculture",\n  "key_concepts": ["crop", "damage", "loss"],\n  "extracted_demographics": {{}},\n  "confidence": "high"\n}}\n\n'
                f"Example 2 — Native script with demographics:\n"
                f"Query: \"SC caste farmer Bihar mein crop insurance\"\n"
                f"Output:\n"
                f'{{\n  "primary_domain": "agriculture",\n  "key_concepts": ["crop", "insurance"],\n  "extracted_demographics": {{"state": "Bihar", "caste": "SC", "occupation": "farmer"}},\n  "confidence": "high"\n}}\n\n'
                f"Example 3 — Health domain:\n"
                f"Query: \"beemar hu hospital ka paisa nahi hai\"\n"
                f"Output:\n"
                f'{{\n  "primary_domain": "health",\n  "key_concepts": ["medical", "hospital", "financial assistance"],\n  "extracted_demographics": {{}},\n  "confidence": "high"\n}}\n\n'
                f"Example 4 — Vague query:\n"
                f"Query: \"help\"\n"
                f"Output:\n"
                f'{{\n  "primary_domain": "unclear",\n  "key_concepts": [],\n  "extracted_demographics": {{}},\n  "confidence": "low"\n}}\n\n'
                f"Example 5 — Housing domain Hindi:\n"
                f"Query: \"pukka makaan chahiye\"\n"
                f"Output:\n"
                f'{{\n  "primary_domain": "housing",\n  "key_concepts": ["housing", "construction", "permanent house"],\n  "extracted_demographics": {{}},\n  "confidence": "high"\n}}\n\n'
                f"Now parse this Query:\n"
                f"Query: \"{query}\"\n"
                f"Output:"
            )
            
            # Enforce strict 1.5s timeout
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=200,
                timeout=1.5
            )
            
            raw = completion.choices[0].message.content or "{}"
            raw = raw.strip()
            
            # Remove any leading/trailing markdown code fences if present (defense in depth)
            if raw.startswith("```"):
                lines = raw.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].endswith("```"):
                    lines = lines[:-1]
                raw = "\n".join(lines).strip()
                
            data = json.loads(raw)
            
            intent_res = IntentResult(
                primary_domain=data.get("primary_domain", "unclear"),
                key_concepts=data.get("key_concepts", []),
                extracted_demographics=data.get("extracted_demographics", {}),
                confidence=data.get("confidence", "low")
            )
            
            # Fallback logging check for non-trivial queries
            if intent_res.primary_domain == "unclear" and query and len(query.strip()) > 4:
                logger.warning(f"Intent extraction fell back for query: {query}")
                
            return intent_res

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str or "Rate limit" in err_str:
                # If it is a daily limit (TPD), do not retry
                if "TPD" in err_str or "tokens per day" in err_str or "Tokens Per Day" in err_str:
                    logger.warning(f"Groq Daily Tokens Per Day (TPD) Limit hit. Skipping retries and falling back immediately for query: {query}")
                    logger.warning(f"Intent extraction fell back due to error/timeout for query: {query}. Error: {e}")
                    return fallback_result
                if attempt < max_retries - 1:
                    sleep_time = retry_delay
                    match = re.search(r"try again in (\d+\.?\d*)s", err_str)
                    if match:
                        sleep_time = float(match.group(1)) + 0.1
                    logger.warning(f"Groq Rate Limit hit. Retrying in {sleep_time:.2f}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
            logger.warning(f"Intent extraction fell back due to error/timeout for query: {query}. Error: {e}")
            return fallback_result
