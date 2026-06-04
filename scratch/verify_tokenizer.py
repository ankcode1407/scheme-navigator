import re

# Before Fix Logic
def before_tokenize(text: str) -> set[str]:
    return set(text.lower().split())

# After Fix Logic
def after_tokenize(text: str) -> set[str]:
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return set(cleaned.split())

query = "interest subvention kcc gujarat"
scheme_name = "Financial Assistance to Farmer for Interest Subvention (KCC)"

print("=== BEFORE FIX ===")
q_tokens_before = before_tokenize(query)
n_tokens_before = before_tokenize(scheme_name)
print(f"Query Tokens: {q_tokens_before}")
print(f"Scheme Name Tokens: {n_tokens_before}")
print(f"Does 'kcc' match '(kcc)'? {'kcc' in n_tokens_before}")

print("\n=== AFTER FIX ===")
q_tokens_after = after_tokenize(query)
n_tokens_after = after_tokenize(scheme_name)
print(f"Query Tokens: {q_tokens_after}")
print(f"Scheme Name Tokens: {n_tokens_after}")
print(f"Does 'kcc' match 'kcc'? {'kcc' in n_tokens_after}")
