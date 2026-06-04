"""
calculate_hit1_breakdown.py
---------------------------
Runs the 60-case eval suite using the offline CrossEncoder reranker
and prints a detailed breakdown of Hit@1, Hit@3, and Hit@5 accuracy by domain.
"""

import sys
from pathlib import Path
import os

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offline mode for reranker
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["PYTHONIOENCODING"] = "utf-8"

from eval.run_eval import TEST_CASES, run_case

def main():
    print("Running 60 evaluation cases to calculate domain-wise Hit metrics...")
    
    # Run all cases
    results = []
    for case in TEST_CASES:
        res = run_case(case, verbose=False)
        results.append(res)
    
    # Group results by domain (tag)
    by_domain = {}
    for case, res in zip(TEST_CASES, results):
        tag = case["tag"]
        if tag not in by_domain:
            by_domain[tag] = []
        by_domain[tag].append((case, res))
        
    print("\n" + "="*80)
    print(f"{'DOMAIN':<20} | {'TOTAL':<5} | {'ELIGIBLE':<8} | {'HIT@1':<12} | {'HIT@3':<12} | {'HIT@5':<12} | {'PASS RATE':<10}")
    print("="*80)
    
    overall_total = 0
    overall_eligible = 0
    overall_hit1 = 0
    overall_hit3 = 0
    overall_hit5 = 0
    overall_passed = 0
    
    for domain in sorted(by_domain.keys()):
        items = by_domain[domain]
        total = len(items)
        eligible_cases = [x for x in items if x[0].get("expect_ids")]
        n_eligible = len(eligible_cases)
        
        hit1 = sum(1 for x in eligible_cases if x[1].get("hit_rank") == 1)
        hit3 = sum(1 for x in eligible_cases if x[1].get("hit_rank") and x[1]["hit_rank"] <= 3)
        hit5 = sum(1 for x in eligible_cases if x[1].get("hit_rank") and x[1]["hit_rank"] <= 5)
        passed = sum(1 for x in items if x[1]["passed"])
        
        hit1_pct = f"{hit1}/{n_eligible} ({round(100*hit1/n_eligible)}%)" if n_eligible else "N/A"
        hit3_pct = f"{hit3}/{n_eligible} ({round(100*hit3/n_eligible)}%)" if n_eligible else "N/A"
        hit5_pct = f"{hit5}/{n_eligible} ({round(100*hit5/n_eligible)}%)" if n_eligible else "N/A"
        pass_pct = f"{passed}/{total} ({round(100*passed/total)}%)"
        
        print(f"{domain:<20} | {total:<5} | {n_eligible:<8} | {hit1_pct:<12} | {hit3_pct:<12} | {hit5_pct:<12} | {pass_pct:<10}")
        
        overall_total += total
        overall_eligible += n_eligible
        overall_hit1 += hit1
        overall_hit3 += hit3
        overall_hit5 += hit5
        overall_passed += passed
        
    print("="*80)
    overall_hit1_pct = f"{overall_hit1}/{overall_eligible} ({round(100*overall_hit1/overall_eligible)}%)"
    overall_hit3_pct = f"{overall_hit3}/{overall_eligible} ({round(100*overall_hit3/overall_eligible)}%)"
    overall_hit5_pct = f"{overall_hit5}/{overall_eligible} ({round(100*overall_hit5/overall_eligible)}%)"
    overall_pass_pct = f"{overall_passed}/{overall_total} ({round(100*overall_passed/overall_total)}%)"
    print(f"{'OVERALL':<20} | {overall_total:<5} | {overall_eligible:<8} | {overall_hit1_pct:<12} | {overall_hit3_pct:<12} | {overall_hit5_pct:<12} | {overall_pass_pct:<10}")
    print("="*80 + "\n")
    
    # Detailed case list
    print("DETAILED CASE LIST")
    print("-" * 80)
    for tag in sorted(by_domain.keys()):
        print(f"\nDOMAIN: {tag.upper()}")
        for case, res in by_domain[tag]:
            status = "PASS" if res["passed"] else "FAIL"
            expect = case.get("expect_ids", [])
            hit_rank = res.get("hit_rank")
            rank_str = f"Rank {hit_rank}" if hit_rank else "Not in top 5" if expect else "N/A (Negative Case)"
            print(f"  [{status}] {case['id']}: {case['description'][:60]:<60} | Expected: {expect} | {rank_str}")

if __name__ == "__main__":
    main()
