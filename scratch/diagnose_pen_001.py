import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Print absolute path of root
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
print("Root dir:", root_dir)
sys.path.insert(0, str(root_dir))

from sentence_transformers import CrossEncoder
from app.agent.reranker import build_scheme_text
from app.knowledge_base.scheme_loader import get_scheme_by_id

dalps = get_scheme_by_id("dalps")
pmkmdy = get_scheme_by_id("pmkmdy")

ctx = {
    "state": "Tamil Nadu",
    "occupation": "farmer",
    "age": 65,
    "problem_statement": "old age pension for farmer labourer",
    "problem_category": "social_welfare",
}
query = "old age pension for farmer labourer"

text_dalps = build_scheme_text(dalps, ctx)
text_pmkmdy = build_scheme_text(pmkmdy, ctx)

ce = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
scores = ce.predict([(query, text_dalps), (query, text_pmkmdy)])

print(f"Query: {query}")
print(f"dalps score: {scores[0]}")
print(f"pmkmdy score: {scores[1]}")
