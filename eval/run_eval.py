"""
run_eval.py
-----------
Precision eval harness for scheme_matching.

Runs 60 hand-labelled test cases (exactly 5 per domain across 12 domains)
against the matcher and reports:
  - Hit@1   : correct scheme in top 1 result
  - Hit@3   : correct scheme in top 3 results
  - Hit@5   : correct scheme in top 5 results
  - Precision: no disqualifying schemes surfaced for known-ineligible users
  - Regression flags: previously-fixed bugs re-appearing

Usage:
    python eval/run_eval.py
    python eval/run_eval.py --verbose
    python eval/run_eval.py --tag health
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import match_schemes

# ---------------------------------------------------------------------------
# Test case schema
# ---------------------------------------------------------------------------
# Each case:
#   id          : unique identifier
#   tag         : category for filtering (one of the 12 domains)
#   description : what this test is checking
#   user_context: the ctx dict passed to match_schemes
#   expect_ids  : list of scheme IDs that MUST appear in top-5
#   reject_ids  : list of scheme IDs that MUST NOT appear (wrong match)
#   expect_ineligible: if True, top result should be INELIGIBLE confidence
#   min_hit_rank: how high the match must appear (default 5, stricter = 1)

TEST_CASES: list[dict] = [

    # ── 1. AGRICULTURE ──────────────────────────────────────────────────────

    {
        "id": "agri_001",
        "tag": "agriculture",
        "description": "Bihar farmer with crop loss should get state-specific schemes",
        "user_context": {
            "state": "Bihar",
            "occupation": "farmer",
            "problem_statement": "my crop failed due to heavy rain",
            "problem_category": "agriculture",
        },
        "expect_ids": ["brfsy"],           # Bihar Rajya Fasal Sahayata Yojna
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "agri_002",
        "tag": "agriculture",
        "description": "All-states crop insurance scheme should surface for any farmer",
        "user_context": {
            "state": "Rajasthan",
            "occupation": "farmer",
            "problem_statement": "crop insurance for my wheat farm",
            "problem_category": "agriculture",
        },
        "expect_ids": ["pmfby"],           # Pradhan Mantri Fasal Bima Yojna
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "agri_003",
        "tag": "agriculture",
        "description": "Gujarat farmer asking about drone tech should get state-specific scheme",
        "user_context": {
            "state": "Gujarat",
            "occupation": "farmer",
            "problem_statement": "want to use drone spraying on my farm",
            "problem_category": "agriculture",
        },
        "expect_ids": ["uadtas"],          # Drone Technology scheme, Gujarat-only
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "agri_004",
        "tag": "agriculture",
        "description": "UP farmer should NOT get Gujarat-only drone scheme (state mismatch)",
        "user_context": {
            "state": "Uttar Pradesh",
            "occupation": "farmer",
            "problem_statement": "drone spraying agricultural support",
            "problem_category": "agriculture",
        },
        "expect_ids": [],
        "reject_ids": ["uadtas"],          # Gujarat-only; should be state-filtered out
        "min_hit_rank": 5,
    },
    {
        "id": "agri_005",
        "tag": "agriculture",
        "description": "Uttarakhand farmer with crop damage from wildlife",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "farmer",
            "problem_statement": "wild animals destroyed my crops need compensation",
            "problem_category": "agriculture",
        },
        "expect_ids": ["cllpwaafadcebnbds"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },

    # ── 2. LIVESTOCK ────────────────────────────────────────────────────────

    {
        "id": "live_001",
        "tag": "livestock",
        "description": "Odisha farmer asking about goat farming subsidy",
        "user_context": {
            "state": "Odisha",
            "occupation": "farmer",
            "problem_statement": "want to start goat farming need financial support",
            "problem_category": "agriculture",
        },
        "expect_ids": ["ssgsf"],           # Prani Sampad Samruddhi Yojana — Odisha
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "live_002",
        "tag": "livestock",
        "description": "SC caste user in Haryana for goat scheme — caste match",
        "user_context": {
            "state": "Haryana",
            "occupation": "unemployed",
            "caste": "SC",
            "problem_statement": "goat farming support for scheduled caste",
            "problem_category": "agriculture",
        },
        "expect_ids": ["mbbpuyhr"],        # SC-only goat scheme Haryana
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "live_003",
        "tag": "livestock",
        "description": "General caste user should be marked INELIGIBLE for SC-only goat scheme",
        "user_context": {
            "state": "Haryana",
            "occupation": "farmer",
            "caste": "General",
            "problem_statement": "goat farming subsidy haryana",
            "problem_category": "agriculture",
        },
        "expect_ids": [],
        "reject_ids": ["mbbpuyhr"],        # SC-restricted — should sink or be INELIGIBLE
        "min_hit_rank": 5,
        "expect_ineligible_ids": ["mbbpuyhr"],
    },
    {
        "id": "live_004",
        "tag": "livestock",
        "description": "Livestock insurance for Uttarakhand farmer",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "farmer",
            "problem_statement": "insurance for my cattle and livestock",
            "problem_category": "agriculture",
        },
        "expect_ids": ["lisulm"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "live_005",
        "tag": "livestock",
        "description": "Transliterated Hindi query for Haryana sheep/goat SC scheme",
        "user_context": {
            "state": "Haryana",
            "occupation": "unemployed",
            "caste": "SC",
            "problem_statement": "bhed bakri palan yojana government subsidy",
            "problem_category": "agriculture",
        },
        "expect_ids": ["mbbpuyhr"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },

    # ── 3. EDUCATION ────────────────────────────────────────────────────────

    {
        "id": "edu_001",
        "tag": "education",
        "description": "Student asking for scholarship — IARI scheme should surface",
        "user_context": {
            "occupation": "student",
            "problem_statement": "scholarship for agricultural studies",
            "problem_category": "education",
        },
        "expect_ids": ["iaris"],           # IARI Scholarship — All states
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "edu_002",
        "tag": "education",
        "description": "Disabled student should get post-matric disability scholarship",
        "user_context": {
            "occupation": "student",
            "problem_statement": "scholarship for disabled students post matric",
            "problem_category": "education",
        },
        "expect_ids": ["post-dis"],        # Post Matric Scholarship Students With Disabilities
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "edu_003",
        "tag": "education",
        "description": "Scholarship query should NOT return livestock schemes (regression: keyword noise)",
        "user_context": {
            "occupation": "student",
            "problem_statement": "I need a scholarship for my college fees",
            "problem_category": "education",
        },
        "expect_ids": [],
        "reject_ids": ["ssgsf", "kbpyy", "lisulm", "brfsy"],
        "min_hit_rank": 5,
    },
    {
        "id": "edu_004",
        "tag": "education",
        "description": "Nishadraj Scholarship Madhya Pradesh for MP students",
        "user_context": {
            "state": "Madhya Pradesh",
            "occupation": "student",
            "problem_statement": "nishadraj scholarship scheme madhya pradesh",
            "problem_category": "education",
        },
        "expect_ids": ["nss"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "edu_005",
        "tag": "education",
        "description": "Krishi Vidya Nidhi Yojana Odisha professional studies scholarship",
        "user_context": {
            "state": "Odisha",
            "occupation": "farmer",
            "problem_statement": "krishi vidya nidhi yojana higher education scholarship odisha",
            "problem_category": "education",
        },
        "expect_ids": ["kvny"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },

    # ── 4. EMPLOYMENT ───────────────────────────────────────────────────────

    {
        "id": "emp_001",
        "tag": "employment",
        "description": "Unemployed youth in Haryana — goat/piggery employment scheme",
        "user_context": {
            "state": "Haryana",
            "occupation": "unemployed",
            "problem_statement": "unemployed youth need employment or livelihood support",
            "problem_category": "employment",
        },
        "expect_ids": ["speoepsgug"],      # Employment via piggery/goat, Haryana
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "emp_002",
        "tag": "employment",
        "description": "REGRESSION: 'Afforestation for Tribals' must not be top result for generic unemployed youth",
        "user_context": {
            "problem_statement": "unemployed youth seeking assistance",
            "problem_category": "employment",
        },
        "expect_ids": [],
        "reject_ids": [],
        "reject_top1_ids": ["aspie"],      # aspie = afforestation scheme — was bug session
        "min_hit_rank": 5,
    },
    {
        "id": "emp_003",
        "tag": "employment",
        "description": "Haryana unemployed aged 25 with SC caste — age+caste eligible scheme",
        "user_context": {
            "state": "Haryana",
            "occupation": "unemployed",
            "caste": "SC",
            "age": 25,
            "problem_statement": "need employment support or self employment scheme",
            "problem_category": "employment",
        },
        "expect_ids": ["speoscelu"],  # 18-60 age range, Haryana
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "emp_004",
        "tag": "employment",
        "description": "Over-age user (65) should be INELIGIBLE for 18-60 employment scheme",
        "user_context": {
            "state": "Haryana",
            "occupation": "unemployed",
            "age": 65,
            "problem_statement": "employment support for senior citizen",
            "problem_category": "employment",
        },
        "expect_ids": [],
        "reject_ids": [],
        "expect_ineligible_ids": ["speoepsgugmmapuy"],  # age_max=60, should fail
        "min_hit_rank": 5,
    },
    {
        "id": "emp_005",
        "tag": "employment",
        "description": "Generic unemployed youth seeking stateless job assistance",
        "user_context": {
            "problem_statement": "Unemployed youth seeking assistance",
            "problem_category": "employment",
        },
        "expect_ids": [],
        "reject_top1_ids": ["aspie"],
        "min_hit_rank": 5,
    },

    # ── 5. PENSION ──────────────────────────────────────────────────────────

    {
        "id": "pen_001",
        "tag": "pension",
        "description": "Elderly farmer in Tamil Nadu should get destitute labourer pension",
        "user_context": {
            "state": "Tamil Nadu",
            "occupation": "farmer",
            "age": 65,
            "problem_statement": "old age pension for farmer labourer",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["dalps"],           # Destitute Ag Labourers Pension — TN, age 60+
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "pen_002",
        "tag": "pension",
        "description": "Young farmer (age 30) should be INELIGIBLE for elderly pension scheme",
        "user_context": {
            "state": "Tamil Nadu",
            "occupation": "farmer",
            "age": 30,
            "problem_statement": "pension for farmers",
            "problem_category": "social_welfare",
        },
        "expect_ids": [],
        "reject_ids": [],
        "expect_ineligible_ids": ["dalps"],  # age_min=60, should fail at 30
        "min_hit_rank": 5,
    },
    {
        "id": "pen_003",
        "tag": "pension",
        "description": "Transliterated destitute old age agricultural pension in TN",
        "user_context": {
            "state": "Tamil Nadu",
            "occupation": "farmer",
            "age": 65,
            "problem_statement": "budhapa pension kheti mazdoor",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["dalps"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "pen_004",
        "tag": "pension",
        "description": "Teelu Rauteli special pension for disabled agricultural workers Uttarakhand",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "farmer",
            "age": 45,
            "problem_statement": "special pension for disabled agricultural workers uttarakhand teelu rauteli",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["dp-f"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "pen_005",
        "tag": "pension",
        "description": "Old age pension for small and marginal farmers Rajasthan",
        "user_context": {
            "state": "Rajasthan",
            "occupation": "farmer",
            "age": 65,
            "problem_statement": "small and marginal farmers old age pension rajasthan",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["cmsmfops"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },

    # ── 6. WOMEN ────────────────────────────────────────────────────────────

    {
        "id": "women_001",
        "tag": "women",
        "description": "Woman farmer in Uttarakhand for dairy support",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "farmer",
            "gender": "female",
            "problem_statement": "women dairy farming support scheme",
            "problem_category": "agriculture",
        },
        "expect_ids": ["mddpu"],           # Mahila Dairy Vikas Pariyojana — Uttarakhand
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "women_002",
        "tag": "women",
        "description": "Mukhyamantri Mahila Utkarsh Yojana women SHG credit in Gujarat",
        "user_context": {
            "state": "Gujarat",
            "occupation": "entrepreneur",
            "gender": "female",
            "problem_statement": "mukhyamantri mahila utkarsh yojana self help group loan gujarat",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["mmuy"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "women_003",
        "tag": "women",
        "description": "Udyogini Scheme financial grant/subsidy for Karnataka female entrepreneurs",
        "user_context": {
            "state": "Karnataka",
            "occupation": "trade",
            "gender": "female",
            "problem_statement": "udyogini scheme karnataka financial assistance for women entrepreneurs",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["us"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "women_004",
        "tag": "women",
        "description": "A-HELP women workers livestock training scheme in Uttarakhand",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "Pashu Sakhi",
            "gender": "female",
            "problem_statement": "a-help training for women workers livestock uttarakhand pashu sakhi",
            "problem_category": "agriculture",
        },
        "expect_ids": ["tpehw"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "women_005",
        "tag": "women",
        "description": "Financial assistance for poor widow daughters marriage in Delhi",
        "user_context": {
            "state": "Delhi",
            "gender": "female",
            "problem_statement": "poor widows daughters marriage financial assistance delhi",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["famdpwog"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },

    # ── 7. HEALTH ───────────────────────────────────────────────────────────

    {
        "id": "health_001",
        "tag": "health",
        "description": "Chikitsa Pratipoorti Yojana serious illness financial assistance Jharkhand",
        "user_context": {
            "state": "Jharkhand",
            "occupation": "Construction Worker",
            "problem_statement": "serious illness financial help cancer heart treatment",
            "problem_category": "health",
        },
        "expect_ids": ["cpy"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "health_002",
        "tag": "health",
        "description": "Krishak Durghatna Kalyan Yojana accident benefit for farmers in UP",
        "user_context": {
            "state": "Uttar Pradesh",
            "occupation": "farmer",
            "problem_statement": "kisano ko durghatna kalyan accident help",
            "problem_category": "health",
        },
        "expect_ids": ["kdky"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "health_003",
        "tag": "health",
        "description": "TB and cancer patient social welfare financial aid Puducherry",
        "user_context": {
            "state": "Puducherry",
            "age": 62,
            "problem_statement": "tb cancer financial help Puducherry",
            "problem_category": "health",
        },
        "expect_ids": ["faoapstbc"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "health_004",
        "tag": "health",
        "description": "Kera Suraksha accident insurance cover for coconut tree climbers",
        "user_context": {
            "occupation": "farmer",
            "problem_statement": "coconut tree climber accident cover insurance",
            "problem_category": "health",
        },
        "expect_ids": ["ksis"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "health_005",
        "tag": "health",
        "description": "Accident medical cover under PMMSY for Gujarat fishermen",
        "user_context": {
            "state": "Gujarat",
            "occupation": "fishermen",
            "problem_statement": "group accident insurance scheme under pmmsy medical treatment gujarat",
            "problem_category": "health",
        },
        "expect_ids": ["gaisguj3"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },

    # ── 8. HOUSING ──────────────────────────────────────────────────────────

    {
        "id": "house_001",
        "tag": "housing",
        "description": "Ved-Vyas Housing Construction Scheme for Jharkhand fish farmers",
        "user_context": {
            "state": "Jharkhand",
            "occupation": "fish farmer",
            "bpl_status": True,
            "problem_statement": "ved vyas housing construction",
            "problem_category": "housing",
        },
        "expect_ids": ["v-vhcs"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "house_002",
        "tag": "housing",
        "description": "Antyodaya Gruha Yojana housing incentive Odisha",
        "user_context": {
            "state": "Odisha",
            "problem_statement": "antyodaya gruha yojana housing subsidy",
            "problem_category": "housing",
        },
        "expect_ids": ["agy-itb"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "house_003",
        "tag": "housing",
        "description": "Aawaas Sahayata for ST student studying in Madhya Pradesh",
        "user_context": {
            "state": "Madhya Pradesh",
            "caste": "Scheduled Tribe",
            "occupation": "student",
            "problem_statement": "awas sahayata for st student madhya pradesh",
            "problem_category": "housing",
        },
        "expect_ids": ["as"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "house_004",
        "tag": "housing",
        "description": "Svamitva scheme property card and village survey mapping",
        "user_context": {
            "problem_statement": "svamitva scheme property card village map",
            "problem_category": "housing",
        },
        "expect_ids": ["pmsy"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "house_005",
        "tag": "housing",
        "description": "Uttar Pradesh student should NOT get MP Awas Sahayata (state mismatch)",
        "user_context": {
            "state": "Uttar Pradesh",
            "caste": "Scheduled Tribe",
            "occupation": "student",
            "problem_statement": "awas sahayata for st student",
            "problem_category": "housing",
        },
        "expect_ids": [],
        "reject_ids": ["as"],
        "min_hit_rank": 5,
    },

    # ── 9. FINANCIAL ────────────────────────────────────────────────────────

    {
        "id": "fin_001",
        "tag": "financial",
        "description": "Mukhya mantri Krishak Udyami Yojana loan/credit MP",
        "user_context": {
            "state": "Madhya Pradesh",
            "occupation": "farmer",
            "problem_statement": "loan for farmer son self employment madhya pradesh",
            "problem_category": "financial",
        },
        "expect_ids": ["mkuy"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "fin_002",
        "tag": "financial",
        "description": "KCC Interest Subvention Scheme Gujarat",
        "user_context": {
            "state": "Gujarat",
            "occupation": "farmer",
            "problem_statement": "interest subvention kcc gujarat",
            "problem_category": "financial",
        },
        "expect_ids": ["fafiskc"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "fin_003",
        "tag": "financial",
        "description": "Atma Nirbhar Matsya Palan Yojana loan/subsidy Arunachal Pradesh",
        "user_context": {
            "state": "Arunachal Pradesh",
            "occupation": "farmer",
            "problem_statement": "fishery loan subsidy arunachal pradesh",
            "problem_category": "financial",
        },
        "expect_ids": ["anmpy"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "fin_004",
        "tag": "financial",
        "description": "Subsidized manure/fertilizer loans Dadra Nagar Haveli",
        "user_context": {
            "state": "Dadra & Nagar Haveli and Daman & Diu",
            "occupation": "farmer",
            "problem_statement": "manure fertilizer loan dadra nagar haveli",
            "problem_category": "financial",
        },
        "expect_ids": ["slsmf"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "fin_005",
        "tag": "financial",
        "description": "Farmer seeking credit/loan - expect KCC",
        "user_context": {
            "occupation": "farmer",
            "problem_statement": "Farmer with 10000 loan",
            "problem_category": "financial",
            "income": 10000
        },
        "expect_ids": ["kcc"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },

    # ── 10. SKILL DEVELOPMENT ───────────────────────────────────────────────

    {
        "id": "skill_001",
        "tag": "skill_development",
        "description": "Gausevak Training initial and refresher program in MP",
        "user_context": {
            "state": "Madhya Pradesh",
            "occupation": "unemployed",
            "problem_statement": "gausevak training madhya pradesh",
            "problem_category": "skills",
        },
        "expect_ids": ["gtiar"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "skill_002",
        "tag": "skill_development",
        "description": "Biotechnology entrepreneurship training program Uttarakhand",
        "user_context": {
            "state": "Uttarakhand",
            "occupation": "student",
            "problem_statement": "biotechnology entrepreneurship training uttarakhand",
            "problem_category": "skills",
        },
        "expect_ids": ["tpedb"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "skill_003",
        "tag": "skill_development",
        "description": "Integrated Agriculture Training Centre Meghalaya",
        "user_context": {
            "state": "Meghalaya",
            "occupation": "farmer",
            "problem_statement": "agriculture training centre meghalaya",
            "problem_category": "skills",
        },
        "expect_ids": ["iatc"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "skill_004",
        "tag": "skill_development",
        "description": "Community canning and fruit preservation training Assam",
        "user_context": {
            "state": "Assam",
            "occupation": "unemployed",
            "problem_statement": "canning training fruit preservation assam",
            "problem_category": "skills",
        },
        "expect_ids": ["cctofp"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "skill_005",
        "tag": "skill_development",
        "description": "Gujarat resident should NOT get MP Gausevak training (state mismatch)",
        "user_context": {
            "state": "Gujarat",
            "occupation": "unemployed",
            "problem_statement": "gausevak training program",
            "problem_category": "skills",
        },
        "expect_ids": [],
        "reject_ids": ["gtiar"],
        "min_hit_rank": 5,
    },

    # ── 11. TRIBAL ──────────────────────────────────────────────────────────

    {
        "id": "tribal_001",
        "tag": "tribal",
        "description": "Incentives/employment in forestry for unemployed tribals in Tamil Nadu",
        "user_context": {
            "state": "Tamil Nadu",
            "caste": "ST",
            "occupation": "unemployed tribals",
            "problem_statement": "afforestation incentives tribals forest tamil nadu",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["aspie"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "tribal_002",
        "tag": "tribal",
        "description": "Adivasi area water pipeline irrigation subsidy Gujarat",
        "user_context": {
            "state": "Gujarat",
            "caste": "ST",
            "occupation": "farmer",
            "problem_statement": "adivasi farmer gujarat pipeline subsidy",
            "problem_category": "agriculture",
        },
        "expect_ids": ["dspvsfwcplguj"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "tribal_003",
        "tag": "tribal",
        "description": "Kadaknath poultry birds subsidy unit for scheduled tribes Gujarat",
        "user_context": {
            "state": "Gujarat",
            "caste": "ST",
            "occupation": "farmer",
            "problem_statement": "kadaknath chicken ST gujarat poultry",
            "problem_category": "agriculture",
        },
        "expect_ids": ["sse25krbust"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "tribal_004",
        "tag": "tribal",
        "description": "Adivasi water pump set subsidy Gujarat TASP/OTASP",
        "user_context": {
            "state": "Gujarat",
            "caste": "ST",
            "occupation": "farmer",
            "problem_statement": "tribal farmer water pump gujarat tasp",
            "problem_category": "agriculture",
        },
        "expect_ids": ["dsmpvhvfpsguj"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "tribal_005",
        "tag": "tribal",
        "description": "General category farmer should NOT get Kadaknath ST subsidy (caste mismatch)",
        "user_context": {
            "state": "Gujarat",
            "caste": "General",
            "occupation": "farmer",
            "problem_statement": "kadaknath poultry subsidy gujarat",
            "problem_category": "agriculture",
        },
        "expect_ids": [],
        "reject_ids": ["sse25krbust"],
        "min_hit_rank": 5,
    },

    # ── 12. DISASTER RELIEF ──────────────────────────────────────────────────

    {
        "id": "disaster_001",
        "tag": "disaster_relief",
        "description": "Livestock/animal death calamity compensation Gujarat",
        "user_context": {
            "state": "Gujarat",
            "occupation": "farmer",
            "problem_statement": "compensation for livestock death gujarat",
            "problem_category": "agriculture",
        },
        "expect_ids": ["ciad"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "disaster_002",
        "tag": "disaster_relief",
        "description": "Goa natural calamity relief assistance for fishermen",
        "user_context": {
            "state": "Goa",
            "occupation": "farmer",
            "problem_statement": "natural calamity assistance goa fisherman",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["ncrfs"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
    {
        "id": "disaster_003",
        "tag": "disaster_relief",
        "description": "Puducherry natural calamity relief for cyclone, flood, fire",
        "user_context": {
            "state": "Puducherry",
            "problem_statement": "natural calamity relief cyclone flood Puducherry",
            "problem_category": "social_welfare",
        },
        "expect_ids": ["rdnccff-sw"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "disaster_004",
        "tag": "disaster_relief",
        "description": "Madhya Pradesh cattle injury/loss compensation wild animals",
        "user_context": {
            "state": "Madhya Pradesh",
            "occupation": "farmer",
            "problem_statement": "wild animal crop livestock damage madhya pradesh",
            "problem_category": "agriculture",
        },
        "expect_ids": ["cfllcbwa"],
        "reject_ids": [],
        "min_hit_rank": 5,
    },
    {
        "id": "disaster_005",
        "tag": "disaster_relief",
        "description": "Real crop failure disaster query - expect BRFSY",
        "user_context": {
            "state": "Bihar",
            "occupation": "farmer",
            "problem_statement": "crop failed due to rain",
            "problem_category": "agriculture",
            "age": 25,
            "gender": "female",
            "income": 50000
        },
        "expect_ids": ["brfsy"],
        "reject_ids": [],
        "min_hit_rank": 3,
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def make_agent_state(user_context: dict) -> dict:
    return {
        "user_context": user_context,
        "case_context": {},
        "user_input": user_context.get("problem_statement", ""),
        "matched_schemes": [],
        "response_to_user": "",
    }


def run_case(case: dict, verbose: bool = False) -> dict:
    state = make_agent_state(case["user_context"])
    result = match_schemes(state)
    matches = result.get("matched_schemes", [])

    returned_ids = [m.get("scheme_id", "") for m in matches]
    returned_names = [m.get("scheme_name", "") for m in matches]
    returned_confidences = {m.get("scheme_id", ""): m.get("confidence", "") for m in matches}

    max_rank = case.get("min_hit_rank", 5)

    # Hit check
    hit_rank: Optional[int] = None
    for eid in case.get("expect_ids", []):
        for rank, rid in enumerate(returned_ids, 1):
            if eid == rid and rank <= max_rank:
                hit_rank = rank
                break

    hit = hit_rank is not None or not case.get("expect_ids")

    # Reject check (must not appear at all)
    rejected_found = [rid for rid in case.get("reject_ids", []) if rid in returned_ids]

    # Reject top-1 check (regression: specific scheme must not be #1)
    reject_top1_violation = False
    if case.get("reject_top1_ids") and returned_ids:
        reject_top1_violation = returned_ids[0] in case["reject_top1_ids"]

    # Ineligible check (scheme should appear but as INELIGIBLE)
    ineligible_ok = True
    for iid in case.get("expect_ineligible_ids", []):
        conf = returned_confidences.get(iid)
        if conf and conf != "INELIGIBLE":
            ineligible_ok = False
            break

    passed = hit and not rejected_found and not reject_top1_violation and ineligible_ok

    result_dict = {
        "id": case["id"],
        "tag": case["tag"],
        "description": case["description"],
        "passed": passed,
        "hit_rank": hit_rank,
        "rejected_found": rejected_found,
        "reject_top1_violation": reject_top1_violation,
        "ineligible_ok": ineligible_ok,
        "returned_ids": returned_ids,
        "returned_names": returned_names[:5],
    }

    if verbose:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n  {status}  [{case['id']}] {case['description']}")
        if not passed:
            if not hit and case.get("expect_ids"):
                print(f"    Expected IDs: {case['expect_ids']}")
                print(f"    Got IDs:      {returned_ids[:5]}")
                print(f"    Got names:    {[n[:50] for n in returned_names[:3]]}")
            if rejected_found:
                print(f"    Rejected IDs found in results: {rejected_found}")
            if reject_top1_violation:
                print(f"    Top-1 regression: {returned_ids[0]}")
            if not ineligible_ok:
                print(f"    Expected INELIGIBLE for: {case.get('expect_ineligible_ids')}")

    return result_dict


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def print_summary(results: list[dict]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = [r for r in results if not r["passed"]]

    # Metrics
    has_expect = [r for r in results if r.get("hit_rank") is not None or
                  any(c["id"] == r["id"] and c.get("expect_ids") for c in TEST_CASES)]

    hit1 = sum(1 for r in results if r.get("hit_rank") == 1)
    hit3 = sum(1 for r in results if r.get("hit_rank") and r["hit_rank"] <= 3)
    hit5 = sum(1 for r in results if r.get("hit_rank") and r["hit_rank"] <= 5)
    cases_with_expect = [c for c in TEST_CASES if c.get("expect_ids")]
    n_expect = len(cases_with_expect)

    SEP = "-" * 60
    print(f"\n{'='*60}")
    print("  SCHEME NAVIGATOR — EVAL RESULTS")
    print(f"{'='*60}\n")
    print(f"  Cases run     : {total}")
    print(f"  Passed        : {passed}/{total}  ({round(100*passed/total)}%)")
    print(f"  Failed        : {len(failed)}/{total}")
    if n_expect:
        print(f"\n  Hit@1  (top result correct)  : {hit1}/{n_expect}  ({round(100*hit1/n_expect)}%)")
        print(f"  Hit@3  (in top 3)            : {hit3}/{n_expect}  ({round(100*hit3/n_expect)}%)")
        print(f"  Hit@5  (in top 5)            : {hit5}/{n_expect}  ({round(100*hit5/n_expect)}%)")

    # By tag
    tags = sorted(set(r["tag"] for r in results))
    print(f"\n{SEP}")
    print("  RESULTS BY CATEGORY")
    print(SEP)
    for tag in tags:
        tag_results = [r for r in results if r["tag"] == tag]
        tag_pass = sum(1 for r in tag_results if r["passed"])
        bar = "#" * tag_pass + "." * (len(tag_results) - tag_pass)
        print(f"  {tag:<15} {bar}  {tag_pass}/{len(tag_results)}")

    if failed:
        print(f"\n{SEP}")
        print("  FAILED CASES")
        print(SEP)
        for r in failed:
            print(f"\n  [FAIL] [{r['id']}] {r['description']}")
            reasons = []
            if r.get("rejected_found"):
                reasons.append(f"reject hit: {r['rejected_found']}")
            if r.get("reject_top1_violation"):
                reasons.append(f"wrong top-1: {r['returned_ids'][0] if r['returned_ids'] else '?'}")
            if not r.get("ineligible_ok"):
                reasons.append("ineligible not flagged")
            if r.get("hit_rank") is None:
                case = next((c for c in TEST_CASES if c["id"] == r["id"]), {})
                if case.get("expect_ids"):
                    reasons.append(f"expected {case['expect_ids']} not in top-5")
            if reasons:
                print(f"    Reason: {'; '.join(reasons)}")
            print(f"    Got:    {r['returned_ids'][:5]}")

    print(f"\n{'='*60}\n")
    return passed == total


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--tag", help="Run only cases with this tag")
    args = parser.parse_args()

    cases = TEST_CASES
    if args.tag:
        cases = [c for c in cases if c["tag"] == args.tag]
        if not cases:
            print(f"No cases found for tag '{args.tag}'")
            sys.exit(1)

    print(f"\nRunning {len(cases)} eval cases...")
    if args.verbose:
        print("-" * 60)

    results = [run_case(c, verbose=args.verbose) for c in cases]
    all_passed = print_summary(results)

    sys.exit(0 if all_passed else 1)