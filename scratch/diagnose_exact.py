import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import load_schemes, find_exact_name_match
all_schemes = load_schemes()

queries = [
    "old age pension Tamil Nadu",
    "SC caste scholarship"
]

audit_candidates = []
for scheme in all_schemes:
    audit_candidates.append({
        "confidence": "HIGH",
        "name": scheme.get("name") or "",
        "scheme_id": scheme.get("scheme_id")
    })

for q in queries:
    res = find_exact_name_match(q, audit_candidates)
    print(f"Query: '{q}' -> find_exact_name_match returned: {res}")
