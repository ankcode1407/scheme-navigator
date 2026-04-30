from app.language.sarvam import detect_language, translate_to_user_language

# Test 1 — Language detection
print("TEST 1 — Language detection")
print("-" * 40)
test_texts = [
    "Main UP mein kisan hoon",
    "நான் ஒரு விவசாயி",
    "I am a farmer in UP",
    "আমি একজন কৃষক",
]
for text in test_texts:
    lang = detect_language(text)
    print(f"  '{text[:30]}...' → {lang}")

# Test 2 — Translation
print("\nTEST 2 — English to Hindi translation")
print("-" * 40)
english = (
    "I found 2 schemes you may be eligible for:\n\n"
    "1. PM-Kisan Samman Nidhi\n"
    "   Confidence: HIGH\n"
    "   Why you qualify: You are a farmer with less than 2 hectares of land.\n"
    "   Documents needed: Aadhaar card, Land records, Bank account\n"
    "   Portal: https://pmkisan.gov.in\n"
    "   Helpline: 155261"
)
hindi = translate_to_user_language(english, "hi-IN")
print(hindi)