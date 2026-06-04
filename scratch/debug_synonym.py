import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "OneDrive" / "Desktop" / "scheme-navigator"))

from app.agent.scheme_matching import stem_word
from app.knowledge_base.scheme_loader import load_schemes

all_schemes = load_schemes()
pmfby = None
for s in all_schemes:
    if s.get("scheme_id") == "pmfby":
        pmfby = s
        break

text = " ".join([
    pmfby.get("scheme_name", ""),
    pmfby.get("brief_description", ""),
    " ".join(pmfby.get("tags", []) or []),
    " ".join(pmfby.get("category", []) or [])
]).lower()

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

SYNONYMS = {
    "insurance": {"bima", "insurance", "risk cover", "insurances"},
    "crop": {"fasal", "crop", "crops", "agriculture", "farming"},
    "farmer": {"kisan", "krishak", "farmer", "farmers"},
}

problem_blob = "crop insurance for my wheat farm"
blob_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", problem_blob) if w not in STOPWORDS}
text_words = {stem_word(w) for w in re.findall(r"\b[a-z]{2,}\b", text) if w not in STOPWORDS}

print(f"blob_words: {blob_words}")
print(f"text_words has 'bima': {'bima' in text_words}")

bw = "insurance"
print(f"\nTracing bw = '{bw}':")
for canon, syns in SYNONYMS.items():
    stemmed_syns = {stem_word(s) for s in syns}
    print(f"  Canon: {canon} | stemmed_syns: {stemmed_syns}")
    match1 = bw in stemmed_syns
    match2 = bw == stem_word(canon)
    print(f"    bw in stemmed_syns: {match1} | bw == stem_word(canon): {match2}")
    if match1 or match2:
        for s in stemmed_syns:
            in_text = s in text_words
            print(f"      Checking synonym '{s}': in_text = {in_text}")
