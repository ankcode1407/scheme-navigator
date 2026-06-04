import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import COMMON_SCHEME_WORDS, audit_eligibility
from app.knowledge_base.scheme_loader import load_schemes, get_scheme_by_id

print("=== STEP 1: VERIFY COMMON_SCHEME_WORDS ===")
print(f"COMMON_SCHEME_WORDS count: {len(COMMON_SCHEME_WORDS)}")

expected_contains = ["scheme", "yojana", "national", "pradhan", "for", "of", "and"]
expected_not_contains = ["gausevak", "biotechnology", "mahila", "fasal"]

contains_ok = True
for w in expected_contains:
    if w in COMMON_SCHEME_WORDS:
        print(f"  [PASS] Contains '{w}'")
    else:
        print(f"  [FAIL] Missing '{w}'")
        contains_ok = False

not_contains_ok = True
for w in expected_not_contains:
    if w not in COMMON_SCHEME_WORDS:
        print(f"  [PASS] Does NOT contain '{w}'")
    else:
        print(f"  [FAIL] Contains '{w}'")
        not_contains_ok = False

print("\n=== STEP 2: VERIFY MMAPUY AUDIT ===")
scheme = get_scheme_by_id("seh-tmdummapuy")
if not scheme:
    print("  [FAIL] Could not find scheme seh-tmdummapuy")
else:
    eligibility_rules = scheme.get("eligibility", {})
    user_context = {"enrolled_programs": []}
    audit = audit_eligibility(eligibility_rules, user_context)
    print(f"Audit output for empty enrolled_programs: {audit}")
    if "Program enrollment: MMAPUY" in audit["missing"]:
        print("  [PASS] Missing contains 'Program enrollment: MMAPUY'")
    else:
        print("  [FAIL] Missing does NOT contain 'Program enrollment: MMAPUY'")
