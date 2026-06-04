import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.knowledge_base.scheme_loader import load_schemes
from collections import Counter

schemes = load_schemes()
total = len(schemes)
word_counts = Counter()
for scheme in schemes:
    words = set(scheme["name"].lower().split())
    word_counts.update(words)

for w in ["scheme", "yojana", "national", "pradhan", "for", "of", "and", "gausevak", "biotechnology", "mahila", "fasal"]:
    count = word_counts.get(w, 0)
    print(f"Word: '{w}', count: {count}, fraction: {count / total:.4f}")
