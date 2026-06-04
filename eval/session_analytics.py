"""
session_analytics.py
--------------------
Reads sessions.json and produces a diagnostic report.

Usage:
    python eval/session_analytics.py --sessions data/sessions.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def extract_returned_schemes(content: str) -> list[str]:
    """Extract scheme names from assistant message text."""
    schemes = []
    for line in content.split("\n"):
        m = re.match(r"^\s*\d+\.\s+(.+)", line.strip())
        if m:
            name = m.group(1).strip()
            # Filter out lines that are clearly not scheme names
            if len(name) > 10 and not name.lower().startswith("confidence"):
                schemes.append(name)
    return schemes


def is_zero_result(content: str) -> bool:
    keywords = ["could not find", "no match", "no strong match", "could not identify"]
    return any(k in content.lower() for k in keywords)


def count_turns(history: list[dict]) -> tuple[int, int]:
    user = sum(1 for m in history if m.get("role") == "user")
    asst = sum(1 for m in history if m.get("role") == "assistant")
    return user, asst


# ---------------------------------------------------------------------------
# Core analyser
# ---------------------------------------------------------------------------

def analyse(sessions: dict) -> dict:
    total = len(sessions)

    # Per-session metrics
    zero_result_sessions = []
    long_sessions = []           # > 4 user turns without resolution
    no_state_sessions = []
    problem_categories = Counter()
    top_returned_schemes = Counter()
    suspicious_matches: list[dict] = []  # high-confidence but likely wrong
    slot_fill_rates: dict[str, int] = defaultdict(int)
    slot_fill_totals: dict[str, int] = defaultdict(int)
    turn_counts: list[int] = []

    TRACKED_SLOTS = ["state", "occupation", "district", "age", "income", "caste", "gender"]
    KNOWN_BAD_MATCHES = [
        # (query_keyword, bad_scheme_keyword) — tuples indicating known irrelevant matches
        ("unemployed youth", "afforestation"),
        ("unemployed youth", "tribal"),
        ("scholarship", "livestock"),
        ("crop insurance", "fisheries"),
    ]

    for sid, session in sessions.items():
        ctx = session.get("user_context", {}) or {}
        history = session.get("conversation_history", []) or []
        user_turns, asst_turns = count_turns(history)
        turn_counts.append(user_turns)

        # Problem category
        cat = ctx.get("problem_category", "unknown") or "unknown"
        problem_categories[cat] += 1

        # Slot fill tracking
        problem = (ctx.get("problem_statement") or "").lower()
        for slot in TRACKED_SLOTS:
            slot_fill_totals[slot] += 1
            if ctx.get(slot):
                slot_fill_rates[slot] += 1

        # State missing
        if not ctx.get("state"):
            no_state_sessions.append(sid)

        # Zero result
        zero = False
        returned: list[str] = []
        for m in history:
            if m.get("role") == "assistant":
                content = m.get("content", "")
                if is_zero_result(content):
                    zero = True
                returned.extend(extract_returned_schemes(content))

        if zero:
            zero_result_sessions.append({"session_id": sid, "problem": ctx.get("problem_statement")})

        # Long session without resolution
        if user_turns > 4:
            long_sessions.append({"session_id": sid, "turns": user_turns, "problem": ctx.get("problem_statement")})

        # Top returned schemes
        for s in returned:
            top_returned_schemes[s] += 1

        # Suspicious match detection
        for (q_kw, bad_kw) in KNOWN_BAD_MATCHES:
            if q_kw in problem:
                for scheme_name in returned:
                    if bad_kw in scheme_name.lower():
                        suspicious_matches.append({
                            "session_id": sid,
                            "query_keyword": q_kw,
                            "bad_scheme": scheme_name,
                        })

    # Slot fill rates as percentages
    slot_fill_pct = {
        slot: round(100 * slot_fill_rates[slot] / slot_fill_totals[slot])
        if slot_fill_totals[slot] else 0
        for slot in TRACKED_SLOTS
    }

    avg_turns = round(sum(turn_counts) / len(turn_counts), 1) if turn_counts else 0

    return {
        "total_sessions": total,
        "avg_user_turns_per_session": avg_turns,
        "zero_result_rate": f"{len(zero_result_sessions)}/{total}",
        "sessions_missing_state": f"{len(no_state_sessions)}/{total}",
        "long_sessions_over_4_turns": len(long_sessions),
        "problem_category_distribution": dict(problem_categories.most_common()),
        "slot_fill_rates_pct": slot_fill_pct,
        "top_returned_schemes": dict(top_returned_schemes.most_common(10)),
        "suspicious_matches_detected": suspicious_matches,
        "zero_result_sessions": zero_result_sessions,
        "long_sessions": long_sessions,
    }


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def print_report(report: dict) -> None:
    SEP = "─" * 60

    print(f"\n{'═'*60}")
    print("  SCHEME NAVIGATOR — SESSION ANALYTICS REPORT")
    print(f"{'═'*60}\n")

    print(f"  Total sessions analysed : {report['total_sessions']}")
    print(f"  Avg user turns/session  : {report['avg_user_turns_per_session']}")
    print(f"  Zero-result rate        : {report['zero_result_rate']}")
    print(f"  Sessions missing state  : {report['sessions_missing_state']}")
    print(f"  Long sessions (>4 turns): {report['long_sessions_over_4_turns']}\n")

    print(SEP)
    print("  PROBLEM CATEGORY DISTRIBUTION")
    print(SEP)
    for cat, count in report["problem_category_distribution"].items():
        bar = "█" * count
        print(f"  {cat:<25} {bar} ({count})")

    print(f"\n{SEP}")
    print("  SLOT FILL RATES  (% of sessions where slot was populated)")
    print(SEP)
    for slot, pct in report["slot_fill_rates_pct"].items():
        filled = "█" * (pct // 5)
        gap = "░" * (20 - pct // 5)
        print(f"  {slot:<12} {filled}{gap}  {pct}%")

    print(f"\n{SEP}")
    print("  TOP RETURNED SCHEMES")
    print(SEP)
    for scheme, count in report["top_returned_schemes"].items():
        print(f"  [{count:>2}x]  {scheme[:70]}")

    if report["suspicious_matches_detected"]:
        print(f"\n{SEP}")
        print("  ⚠  SUSPICIOUS MATCHES DETECTED")
        print(SEP)
        for m in report["suspicious_matches_detected"]:
            print(f"  Query '{m['query_keyword']}' → returned: {m['bad_scheme'][:60]}")

    if report["zero_result_sessions"]:
        print(f"\n{SEP}")
        print("  ZERO-RESULT SESSIONS")
        print(SEP)
        for s in report["zero_result_sessions"]:
            print(f"  [{s['session_id'][:8]}]  {s['problem']}")

    print(f"\n{'═'*60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", default="data/sessions.json")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of report")
    args = parser.parse_args()

    path = Path(args.sessions)
    if not path.exists():
        print(f"ERROR: sessions file not found at {path}")
        raise SystemExit(1)

    with open(path) as f:
        sessions = json.load(f)

    if isinstance(sessions, list):
        sessions = {str(i): s for i, s in enumerate(sessions)}

    report = analyse(sessions)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)