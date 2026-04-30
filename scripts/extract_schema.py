import json
import os
import time
from groq import Groq
from dotenv import load_dotenv
from datetime import date

# Provider rotation — each has independent daily limits
# When one hits rate limit, script moves to the next
PROVIDERS = [
    {
        "name": "groq-llama3",
        "model": "llama3-8b-8192",   # Different model = different quota
        "client": "groq"
    },
    {
        "name": "groq-gemma",
        "model": "gemma2-9b-it",     # Google's model on Groq infra
        "client": "groq"
    },
]

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SCHEMA_TEMPLATE = {
    "id": "",
    "name": "",
    "category": "",
    "last_verified": str(date.today()),
    "source_url": "",
    "source_text": "",
    "description": "",
    "eligibility": {
        "occupation": [],
        "state": [],
        "residence": None,
        "age_min": None,
        "age_max": None,
        "gender": None,
        "income_category": None,
        "max_annual_income": None,
        "max_land_hectares": None,
        "caste": [],
        "requires_aadhaar": True,
        "requires_bank_account": True,
        "note": ""
    },
    "documents_required": [],
    "benefit": "",
    "portal": "",
    "helpline": "",
    "application_mode": ""
}

EXTRACTION_PROMPT = """You are extracting structured eligibility data from an Indian government scheme description.

Scheme information:
Name: {name}
Category: {category}
State: {state}
Level: {level}
Tags: {tags}
Description: {description}

Extract ONLY what is explicitly mentioned. If something is not mentioned, use null for strings/numbers and [] for lists.

Return ONLY valid JSON matching this exact structure:
{{
    "occupation": [list of occupations mentioned, e.g. "farmer", "student", "vendor"],
    "state": {state_list},
    "residence": null or "rural" or "urban" or "both",
    "age_min": null or number,
    "age_max": null or number,
    "gender": null or "male" or "female" or "all",
    "income_category": null or "BPL" or "APL" or "general",
    "max_annual_income": null or number in rupees,
    "max_land_hectares": null or number,
    "caste": [list of castes if mentioned, e.g. "SC", "ST", "OBC"],
    "benefit_summary": "one sentence describing the benefit",
    "documents_likely": [list of documents typically needed based on eligibility],
    "application_mode": "online" or "offline" or "both" or "CSC"
}}"""

def extract_single(raw_scheme: dict) -> dict | None:
    prompt = EXTRACTION_PROMPT.format(
        name=raw_scheme.get("name", ""),
        category=raw_scheme.get("category", []),
        state=raw_scheme.get("state", []),
        level=raw_scheme.get("level", ""),
        tags=raw_scheme.get("tags", []),
        description=raw_scheme.get("brief_description", ""),
        state_list=json.dumps(raw_scheme.get("state", [])),
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        extracted = json.loads(raw)

        # Build final schema
        return {
            "id": raw_scheme["slug"],
            "name": raw_scheme["name"],
            "category": (raw_scheme.get("category") or ["unknown"])[0]
                        .lower().replace(",", "").replace(" ", "_")
                        .replace("&", "and"),
            "last_verified": str(date.today()),
            "source_url": raw_scheme.get("source_url", ""),
            "source_text": raw_scheme.get("brief_description", ""),
            "description": raw_scheme.get("brief_description", ""),
            "eligibility": {
                "occupation": extracted.get("occupation", []),
                "state": extracted.get("state", []),
                "residence": extracted.get("residence"),
                "age_min": extracted.get("age_min"),
                "age_max": extracted.get("age_max"),
                "gender": extracted.get("gender"),
                "income_category": extracted.get("income_category"),
                "max_annual_income": extracted.get("max_annual_income"),
                "max_land_hectares": extracted.get("max_land_hectares"),
                "caste": extracted.get("caste", []),
                "requires_aadhaar": True,
                "requires_bank_account": True,
                "note": "",
            },
            "documents_required": extracted.get("documents_likely", [
                "Aadhaar card",
                "Bank account passbook",
            ]),
            "benefit": extracted.get("benefit_summary",
                                     raw_scheme.get("brief_description", "")[:100]),
            "portal": raw_scheme.get("source_url", ""),
            "helpline": "",
            "application_mode": extracted.get("application_mode", "offline"),
        }

    except Exception as e:
        print(f"    Extraction failed: {e}")
        return None

def batch_extract(raw_path: str, out_path: str,
                  limit: int = 100, start: int = 0):
    with open(raw_path, encoding="utf-8") as f:
        raw_schemes = json.load(f)

    batch = raw_schemes[start:start + limit]
    print(f"Processing {len(batch)} schemes "
          f"(index {start}–{start+len(batch)-1})")

    # Load existing output if resuming
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"schemes": []}

    extracted_ids = {s["id"] for s in existing["schemes"]}
    added = 0
    failed = 0

    for i, raw in enumerate(batch):
        if raw["slug"] in extracted_ids:
            print(f"  [{i+1}/{len(batch)}] Skip (exists): {raw['name'][:40]}")
            continue

        print(f"  [{i+1}/{len(batch)}] {raw['name'][:50]}")
        result = extract_single(raw)

        if result:
            existing["schemes"].append(result)
            extracted_ids.add(result["id"])
            added += 1
        else:
            failed += 1

        # Save after every 10 schemes — don't lose progress
        if (i + 1) % 10 == 0:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"    Checkpoint saved: {len(existing['schemes'])} total")

        time.sleep(0.2)

    # Final save
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Added: {added} | Failed: {failed} | "
          f"Total in file: {len(existing['schemes'])}")

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    batch_extract(
        raw_path="data/myscheme_raw.json",
        out_path="data/schemes_extracted.json",
       limit=4614,   # Full run
        start=46, 
    )