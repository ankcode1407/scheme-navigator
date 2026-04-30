import json
import os

def load_schemes():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schemes_path = os.path.join(base_dir, "schemes", "schemes_full.json")
    with open(schemes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["schemes"]

def get_scheme_by_id(scheme_id: str):
    schemes = load_schemes()
    for scheme in schemes:
        if scheme["id"] == scheme_id:
            return scheme
    return None

def get_schemes_by_category(category: str):
    schemes = load_schemes()
    return [s for s in schemes if s["category"] == category]

def get_all_scheme_names():
    schemes = load_schemes()
    return [s["name"] for s in schemes]