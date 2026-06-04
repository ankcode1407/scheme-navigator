import sys
from pathlib import Path

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import score_scheme, init_matcher, filter_candidates
from app.knowledge_base.scheme_loader import load_schemes
import numpy as np

init_matcher(eager_warm=True)
all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

from app.agent.scheme_matching import get_query_embedding, dump_model

user_context = {
    "occupation": "farmer",
    "problem_statement": "Need agriculture or farming support",
    "problem_category": "agriculture"
}

target_ids = ["nmsa-radg", "nmnf", "pmksypdmc", "pmfby"]

query_text = user_context.get("problem_statement")
query_emb = get_query_embedding(query_text)

candidates = filter_candidates(all_schemes)

for tid in target_ids:
    for c in candidates:
        raw = dump_model(c)
        if raw.get("scheme_id") == tid:
            idx = scheme_id_to_index.get(tid)
            
            # Reconstruct details
            import re
            STOPWORDS = {
                "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
                "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", 
                "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", 
                "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", 
                "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
                "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", 
                "with", "about", "against", "between", "into", "through", "during", "before", "after", 
                "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", 
                "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", 
                "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", 
                "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", 
                "should", "now", "need", "seeking", "assistance", "want", "support", "help", "scheme", 
                "schemes", "yojana", "yojna", "government", "govt", "india", "indian", "state", "district",
                "beneficiary", "beneficiaries", "eligible"
            }
            from app.agent.scheme_matching import stem_word, _EMBEDDINGS
            
            text = " ".join([
                raw.get("scheme_name", ""),
                raw.get("brief_description", ""),
                " ".join(raw.get("tags", []) or []),
                " ".join(raw.get("category", []) or [])
            ]).lower()
            problem_blob = " ".join(str(user_context.get(key, "") or "") for key in ["problem_statement", "problem_category"]).lower()
            
            blob_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", problem_blob) if w not in STOPWORDS}
            text_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", text) if w not in STOPWORDS}
            name_text = raw.get("scheme_name", "").lower()
            name_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", name_text) if w not in STOPWORDS}
            
            matched_query_words = set()
            for bw in blob_words:
                if bw in text_words:
                    matched_query_words.add(bw)
            
            matched_name_words = set()
            for bw in blob_words:
                if bw in name_words:
                    matched_name_words.add(bw)
            
            sim = float(np.dot(query_emb, _EMBEDDINGS[idx])) if _EMBEDDINGS is not None else 0
            kw_rel = (len(matched_name_words)/len(blob_words) * 0.70 + len(matched_query_words)/len(blob_words) * 0.30) * 100.0 if blob_words else 0
            sem_rel = ((sim - 0.15)/0.40)*100.0 if sim >= 0.15 else 0
            rel_score = 0.60 * sem_rel + 0.40 * kw_rel
            
            score, reasons = score_scheme(raw, user_context, {}, query_emb, idx)
            print(f"\n==========================================")
            print(f"Scheme: [{tid}] {raw.get('scheme_name')}")
            print(f"  Query words: {blob_words}")
            print(f"  Matched query text words: {matched_query_words}")
            print(f"  Keyword Relevance: {kw_rel:.2f}")
            print(f"  Similarity: {sim:.4f} -> Semantic Relevance: {sem_rel:.2f}")
            print(f"  Relevance Score: {rel_score:.2f}")
            print(f"  Final Score (with current 0.7x): {score}")
            print(f"  Reasons: {reasons}")
