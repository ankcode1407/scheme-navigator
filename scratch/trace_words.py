import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "OneDrive" / "Desktop" / "scheme-navigator"))

from app.agent.scheme_matching import score_scheme, init_matcher, filter_candidates
from app.knowledge_base.scheme_loader import load_schemes
import numpy as np

init_matcher(eager_warm=True)
all_schemes = load_schemes()
scheme_id_to_index = {s.get("scheme_id"): i for i, s in enumerate(all_schemes)}

from app.agent.scheme_matching import get_query_embedding, dump_model

def trace_scheme_words(tid):
    for c in all_schemes:
        if c.get("scheme_id") == tid:
            import re
            from app.agent.scheme_matching import stem_word
            
            text = " ".join([
                c.get("scheme_name", ""),
                c.get("brief_description", ""),
                " ".join(c.get("tags", []) or []),
                " ".join(c.get("category", []) or [])
            ]).lower()
            
            STOPWORDS = {"i", "me", "my", "myself"} # minimize stopwords for printing
            text_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", text)}
            print(f"\nSCHEME: {tid}")
            print(f"Text words: {text_words}")
            print(f"Is 'bima' in text words? {'bima' in text_words}")
            print(f"Is 'fasal' in text words? {'fasal' in text_words}")

trace_scheme_words("pmfby")
