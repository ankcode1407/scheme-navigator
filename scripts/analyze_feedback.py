import json
from pathlib import Path
from collections import Counter

def main():
    schemes_path = Path("app/schemes/schemes_full.json")
    feedback_path = Path("data/feedback.jsonl")
    metrics_path = Path("data/metrics.jsonl")

    # Load scheme mapping to domain
    scheme_to_domain = {}
    if schemes_path.exists():
        try:
            with schemes_path.open("r", encoding="utf-8") as f:
                schemes_data = json.load(f)
                schemes = schemes_data.get("schemes", []) if isinstance(schemes_data, dict) else schemes_data
                for s in schemes:
                    s_id = s.get("id") or s.get("scheme_id")
                    cat = s.get("category") or "other"
                    
                    # Normalize category to domain
                    domain = cat.lower()
                    if "agri" in domain:
                        domain = "agriculture"
                    elif "edu" in domain or "scholar" in domain:
                        domain = "education"
                    elif "employ" in domain or "work" in domain:
                        domain = "employment"
                    elif "health" in domain or "med" in domain:
                        domain = "health"
                    elif "house" in domain or "housing" in domain:
                        domain = "housing"
                    elif "pension" in domain or "welfare" in domain:
                        domain = "pension"
                    elif "live" in domain or "dairy" in domain or "goat" in domain or "poultry" in domain:
                        domain = "livestock"
                        
                    scheme_to_domain[s_id] = domain
        except Exception as e:
            print(f"Warning: failed to load schemes: {e}")

    # Read feedback logs
    feedback_events = []
    feedback_sessions = set()
    clicks_by_session = {} # session_id -> list of clicked scheme_ids
    clicks_count = Counter() # scheme_id -> count of clicks
    
    if feedback_path.exists():
        try:
            with feedback_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    feedback_events.append(event)
                    sess_id = event.get("session_id")
                    if sess_id:
                        feedback_sessions.add(sess_id)
                    
                    if event.get("interaction_type") == "click":
                        scheme_id = event.get("scheme_id")
                        clicks_count[scheme_id] += 1
                        if sess_id:
                            if sess_id not in clicks_by_session:
                                clicks_by_session[sess_id] = []
                            clicks_by_session[sess_id].append(scheme_id)
        except Exception as e:
            print(f"Warning: failed to load feedback: {e}")

    # Read metrics logs
    metrics_events = []
    metrics_sessions = set()
    queries_by_domain = Counter()
    clicks_by_domain = Counter()
    
    queries_by_mode = Counter()
    clicks_by_mode = Counter()
    
    zero_click_queries_count = 0
    state_verif_domains = Counter()
    
    if metrics_path.exists():
        try:
            with metrics_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    metrics_events.append(entry)
                    sess_id = entry.get("session_id")
                    if sess_id:
                        metrics_sessions.add(sess_id)
                        
                    mode = entry.get("reranker_mode") or "cross_encoder"
                    top_scheme = entry.get("top_scheme_id")
                    domain = "other"
                    if top_scheme:
                        domain = scheme_to_domain.get(top_scheme, "other")
                        
                    queries_by_mode[mode] += 1
                    if top_scheme:
                        queries_by_domain[domain] += 1
                    
                    # Check if session received clicks
                    has_click = False
                    if sess_id in clicks_by_session:
                        has_click = True
                        
                    if has_click:
                        clicks_by_mode[mode] += 1
                        if top_scheme:
                            clicks_by_domain[domain] += 1
                    else:
                        if entry.get("response_type") == "schemes":
                            zero_click_queries_count += 1
                            
                    if entry.get("needs_state_verification") and top_scheme:
                        state_verif_domains[domain] += 1
        except Exception as e:
            print(f"Warning: failed to load metrics: {e}")

    all_sessions = feedback_sessions | metrics_sessions
    total_sessions = len(all_sessions)
    total_feedback = len(feedback_events)

    print("==================================================")
    print("SESSION SUMMARY & FEEDBACK ANALYSIS")
    print("==================================================")
    print(f"Total sessions: {total_sessions}")
    print(f"Total feedback events: {total_feedback}")
    print()
    
    print("Click-Through Rate (CTR) by Domain:")
    for dom in sorted(queries_by_domain.keys()):
        queries = queries_by_domain[dom]
        clicks = clicks_by_domain[dom]
        ctr = clicks / queries if queries > 0 else 0.0
        print(f"  {dom:18}: {ctr * 100:6.1f}% ({clicks}/{queries} queries)")
    print()
    
    print("Click-Through Rate (CTR) by Reranker Mode:")
    for mode in sorted(queries_by_mode.keys()):
        queries = queries_by_mode[mode]
        clicks = clicks_by_mode[mode]
        ctr = clicks / queries if queries > 0 else 0.0
        print(f"  {mode:18}: {ctr * 100:6.1f}% ({clicks}/{queries} queries)")
    print()
    
    print(f"Queries with zero clicks: {zero_click_queries_count}")
    print()
    
    print("Most common needs_state_verification domains:")
    for dom, count in state_verif_domains.most_common():
        print(f"  {dom:18}: {count} queries")
    print()
    
    print("Top 10 most clicked schemes:")
    for s_id, count in clicks_count.most_common(10):
        print(f"  {s_id:18}: {count} click(s)")
    print("==================================================")

if __name__ == "__main__":
    main()
