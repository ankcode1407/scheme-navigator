import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.scheme_matching import load_schemes, compute_common_scheme_words, tokenize
all_schemes = load_schemes()
# Sort them by their actual order in the matching candidates
eligible = [
    {'scheme_id': 'batcs', 'name': 'Basic Agriculture Training Centre Scheme'},
    {'scheme_id': 'iatc', 'name': 'Integrated Agriculture Training Centre Scheme'}
]
query = 'agriculture training centre meghalaya'
query_tokens = tokenize(query)

GENERIC_WORDS = {
    'scheme', 'yojana', 'yojna', 'assistance', 'support', 'help',
    'government', 'govt', 'state', 'national', 'central', 'department',
    'ministry', 'board', 'corporation', 'society', 'cooperative',
    'limited', 'ltd', 'private', 'pvt', 'public', 'association',
    'trust', 'foundation', 'commission', 'committee', 'authority',
    'agency', 'council', 'federation', 'union', 'chamber', 'group',
    'insurance', 'subsidy', 'loan', 'credit', 'grant', 'pension',
    'scholarship', 'fellowship', 'stipend', 'award', 'prize',
    'training', 'development', 'welfare', 'benefit', 'incentive',
    'program', 'programme', 'project', 'mission', 'campaign',
    'drive', 'initiative', 'under', 'for', 'to', 'of', 'and', 'in', 'the', 'a', 'an'
}

for threshold in [0.03, 0.10]:
    common = compute_common_scheme_words(all_schemes, threshold) | GENERIC_WORDS
    print(f"\nThreshold {threshold}:")
    for candidate in eligible:
        name_tokens = tokenize(candidate['name'])
        distinctive = name_tokens - common
        overlap = query_tokens & distinctive
        ratio = len(overlap) / len(distinctive) if distinctive else 0
        print(f"  {candidate['scheme_id']}: name={name_tokens}, distinctive={distinctive}, overlap={overlap}, ratio={ratio:.4f}")
