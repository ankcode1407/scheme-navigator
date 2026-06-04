import json
import os
from typing import Any


def _normalize_scheme(raw: dict[str, Any]) -> dict[str, Any]:
    scheme = dict(raw)

    scheme["scheme_id"] = scheme.get("scheme_id") or scheme.get("id", "")
    scheme["scheme_name"] = scheme.get("scheme_name") or scheme.get("name", "")

    if isinstance(scheme.get("state"), str):
        scheme["state"] = [scheme["state"]]
    elif scheme.get("state") is None:
        scheme["state"] = []

    if isinstance(scheme.get("category"), str):
        scheme["category"] = [scheme["category"]]
    elif scheme.get("category") is None:
        scheme["category"] = []

    if isinstance(scheme.get("tags"), str):
        scheme["tags"] = [scheme["tags"]]
    elif scheme.get("tags") is None:
        scheme["tags"] = []

    if scheme.get("eligibility") is None:
        scheme["eligibility"] = {}

    # Unify text fields: score_scheme reads brief_description and tags
    # but schemes_full.json stores content in description/source_text
    if not scheme.get("brief_description"):
        scheme["brief_description"] = (
            scheme.get("description") or scheme.get("source_text") or ""
        )

    # Normalize category: split concatenated string into searchable tokens
    # "social_welfare_and_empowerment" → ["social welfare", "empowerment"]
    if isinstance(scheme.get("category"), list) and len(scheme["category"]) == 1:
        raw_cat = scheme["category"][0]
        if "_" in raw_cat and " " not in raw_cat:
            scheme["category"] = [raw_cat.replace("_", " ")]
    elif isinstance(scheme.get("category"), str):
        raw_cat = scheme["category"]
        scheme["category"] = [raw_cat.replace("_", " ")]

    if scheme.get("documents_required") is None:
        scheme["documents_required"] = []

    if scheme.get("portal") is None:
        scheme["portal"] = ""

    if scheme.get("helpline") is None:
        scheme["helpline"] = ""

    if scheme.get("application_mode") is None:
        scheme["application_mode"] = ""

    return scheme


def load_schemes():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "schemes", "schemes_full.json")
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    schemes = data.get("schemes", [])
    return [_normalize_scheme(s) for s in schemes]


def get_scheme_by_id(scheme_id: str):
    schemes = load_schemes()
    for scheme in schemes:
        if scheme.get("scheme_id") == scheme_id or scheme.get("id") == scheme_id:
            return scheme
    return None


def get_schemes_by_category(category: str):
    schemes = load_schemes()
    category_lower = category.lower()
    return [
        s for s in schemes
        if category_lower in " ".join(s.get("category", [])).lower()
    ]


def get_all_scheme_names():
    schemes = load_schemes()
    return [s.get("scheme_name") or s.get("name", "") for s in schemes]