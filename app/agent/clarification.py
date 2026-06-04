from typing import Any

def check_ambiguity_clarification(top_matches: list[dict]) -> str | None:
    """
    Loops over top candidates (usually top 5). If 2+ active schemes share the same 
    non-null 'clarification_group', returns the 'clarification_question' from the first match.
    """
    if not top_matches:
        return None
        
    group_counts = {}
    first_questions = {}
    
    for match in top_matches:
        # Exclude INELIGIBLE matches from clarification triggers
        if match.get("confidence") == "INELIGIBLE":
            continue
            
        group = match.get("clarification_group")
        question = match.get("clarification_question")
        
        if group:
            group_counts[group] = group_counts.get(group, 0) + 1
            if group not in first_questions and question:
                first_questions[group] = question
                
    for group, count in group_counts.items():
        if count >= 2:
            return first_questions.get(group)
            
    return None


def detect_clarification_needed(
    top_candidates, schemes_lookup
) -> dict | None:
    """
    Returns clarification dict if 2+ schemes 
    in top-5 share a clarification_group AND
    at least one is in the top-3.
    Maximum one clarification per query.
    """
    group_hits = {}
    
    for i, candidate in enumerate(top_candidates[:5]):
        scheme = schemes_lookup.get(
            candidate["scheme_id"], {}
        )
        group = scheme.get("clarification_group")
        if not group:
            continue
        if group not in group_hits:
            group_hits[group] = {
                "positions": [], 
                "question": scheme.get(
                    "clarification_question", ""
                )
            }
        group_hits[group]["positions"].append(i)
    
    # Find groups with 2+ hits where at least 
    # one position is in top-3 (index 0,1,2)
    for group, data in group_hits.items():
        positions = data["positions"]
        has_top3 = any(p < 3 for p in positions)
        if len(positions) >= 2 and has_top3:
            return {
                "type": "clarification",
                "group": group,
                "question": data["question"]
            }
    
    return None
