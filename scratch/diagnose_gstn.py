import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["GROQ_RERANKING_ENABLED"] = "False"
os.environ["GROQ_INTENT_EXTRACTION_ENABLED"] = "False"

from sentence_transformers import CrossEncoder
from app.agent.reranker import build_scheme_text
from app.knowledge_base.scheme_loader import get_scheme_by_id

dalps = get_scheme_by_id("dalps")
gstn = get_scheme_by_id("gstn")

ctx = {"state": "Tamil Nadu", "age": 65, "problem_category": "social_welfare"}
query = "old age pension Tamil Nadu"

text_dalps = build_scheme_text(dalps, ctx)
text_gstn = build_scheme_text(gstn, ctx)

ce = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = ce.predict([(query, text_dalps), (query, text_gstn)])

print(f"dalps text: {text_dalps}")
print(f"gstn text: {text_gstn}")
print(f"CrossEncoder scores: dalps={scores[0]}, gstn={scores[1]}")
