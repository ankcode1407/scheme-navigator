from __future__ import annotations

DEFAULT_LANGUAGE_CODE = "en-IN"

# ---------------------------------------------------------------------------
# Core question prompts
# ---------------------------------------------------------------------------

QUESTIONS_MAP = {
    "problem_statement": "What kind of help are you looking for?",
    "occupation": "What work do you do, if it matters for this help?",
    "state": "Which state do you live in?",
    "district": "Which district do you live in?",
    "block": "Which block do you live in?",
    "residence": "Do you live in a rural area or urban area?",
    "application_status": "Has your application been submitted, rejected, or is it still pending?",
    "rejection_reason": "What reason was given for the rejection?",
    "missing_documents": "Which documents are missing?",
}

# ---------------------------------------------------------------------------
# Localized strings
# ---------------------------------------------------------------------------

LOCALIZED_STRINGS = {
    "language_gate_prompt": {
        "en-IN": "Please choose your language first.",
        "hi-IN": "कृपया पहले अपनी भाषा चुनें।",
        "bn-IN": "অনুগ্রহ করে আগে আপনার ভাষা নির্বাচন করুন।",
        "ta-IN": "முதலில் உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்.",
        "te-IN": "దయచేసి ముందుగా మీ భాషను ఎంచుకోండి.",
        "mr-IN": "कृपया आधी तुमची भाषा निवडा.",
        "gu-IN": "કૃપા કરીને પહેલા તમારી ભાષા પસંદ કરો.",
        "kn-IN": "ದಯವಿಟ್ಟು ಮೊದಲು ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "ml-IN": "ദയവായി ആദ്യം നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കുക.",
        "pa-IN": "ਕਿਰਪਾ ਕਰਕੇ ਪਹਿਲਾਂ ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ।",
        "od-IN": "ଦୟାକରି ପ୍ରଥମେ ଆପଣଙ୍କର ଭାଷା ଚୟନ କରନ୍ତୁ।",
    },
    "language_acknowledgement": {
        "en-IN": "Thanks. Tell me what problem you are facing.",
        "hi-IN": "धन्यवाद। कृपया बताइए कि आपको क्या समस्या हो रही है।",
        "bn-IN": "ধন্যবাদ। অনুগ্রহ করে বলুন আপনি কী সমস্যার সম্মুখীন হচ্ছেন।",
        "ta-IN": "நன்றி. தயவுசெய்து நீங்கள் சந்திக்கும் பிரச்சினையை சொல்லுங்கள்.",
        "te-IN": "ధన్యవాదాలు. దయచేసి మీరు ఎదుర్కొంటున్న సమస్యను చెప్పండి.",
        "mr-IN": "धन्यवाद। कृपया तुम्हाला कोणती अडचण येत आहे ते सांगा.",
        "gu-IN": "આભાર। કૃપા કરીને જણાવો કે તમને કઈ સમસ્યા આવી રહી છે.",
        "kn-IN": "ಧನ್ಯವಾದಗಳು. ದಯವಿಟ್ಟು ನೀವು ಎದುರಿಸುತ್ತಿರುವ ಸಮಸ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
        "ml-IN": "നന്ദി. ദയവായി നിങ്ങൾ നേരിടുന്ന പ്രശ്നം പറയൂ.",
        "pa-IN": "ਧੰਨਵਾਦ। ਕਿਰਪਾ ਕਰਕੇ ਦੱਸੋ ਤੁਹਾਨੂੰ ਕੀ ਸਮੱਸਿਆ ਆ ਰਹੀ है।",
        "od-IN": "ଧନ୍ୟବାଦ। ଦୟାକରି ଆପଣ କେଉଁ ସମସ୍ୟାର ସମ୍ମୁଖୀନ ହେଉଛନ୍ତି କୁହନ୍ତୁ।",
    },
    "problem_first_question": {
        "en-IN": (
            "What kind of help are you looking for? For example: scholarship, "
            "ration card, pension, crop loss, job, loan, health, or a rejected application."
        ),
        "hi-IN": (
            "आप किस प्रकार की सहायता चाहते हैं? उदाहरण: छात्रवृत्ति, राशन कार्ड, "
            "पेंशन, फसल नुकसान, नौकरी, ऋण, स्वास्थ्य या अस्वीकृत आवेदन।"
        ),
        "bn-IN": (
            "আপনি কী ধরনের সাহায্য খুঁজছেন? উদাহরণ: স্কলারশিপ, রেশন কার্ড, "
            "পেনশন, ফসলের ক্ষতি, চাকরি, ঋণ, স্বাস্থ্য বা বাতিল আবেদন।"
        ),
        "ta-IN": (
            "உங்களுக்கு எந்த வகையான உதவி தேவை? உதாரணம்: கல்வி உதவித்தொகை, "
            "ரேஷன் கார்டு, ஓய்வூதியம், பயிர் சேதம், வேலை, கடன், சுகாதாரம் அல்லது நிராகரிக்கப்பட்ட விண்ணப்பம்."
        ),
        "te-IN": (
            "మీకు ఏ విధమైన సహాయం కావాలి? ఉదాహరణకు: స్కాలర్‌షిప్, రేషన్ కార్డు, "
            "పెన్షన్, పంట నష్టం, ఉద్యోగం, రుణం, ఆరోగ్యం లేదా తిరస్కరించబడిన దరఖాస్తు."
        ),
        "mr-IN": (
            "तुम्हाला कोणत्या प्रकारची मदत हवी आहे? उदाहरणार्थ: शिष्यवृत्ती, "
            "रेशन कार्ड, पेन्शन, पिकांचे नुकसान, नोकरी, कर्ज, आरोग्य किंवा नाकारलेला अर्ज."
        ),
        "gu-IN": (
            "તમને કઈ પ્રકારની મદદ જોઈએ છે? ઉદાહરણ તરીકે: સ્કોલરશિપ, રેશન કાર્ડ, "
            "પેન્શન, પાક નુકસાન, નોકરી, લોન, આરોગ્ય અથવા નકારાયેલ અરજી."
        ),
        "kn-IN": (
            "ನಿಮಗೆ ಯಾವ ರೀತಿಯ ಸಹಾಯ ಬೇಕು? ಉದಾಹರಣೆಗೆ: ವಿದ್ಯಾರ್ಥಿವೇತನ, ರೇಷನ್ ಕಾರ್ಡ್, "
            "ಪಿಂಚಣಿ, ಬೆಳೆ ನಷ್ಟ, ಉದ್ಯೋಗ, ಸಾಲ, ಆರೋಗ್ಯ ಅಥವಾ ತಿರಸ್ಕೃತ ಅರ್ಜಿ."
        ),
        "ml-IN": (
            "നിങ്ങൾക്ക് എന്തുതരത്തിലുള്ള സഹായമാണ് വേണ്ടത്? ഉദാഹരണം: സ്കോളർഷിപ്പ്, റേഷൻ കാർഡ്, "
            "പെൻഷൻ, വിളനാശം, ജോലി, വായ്പ, ആരോഗ്യം അല്ലെങ്കിൽ നിരസിക്കപ്പെട്ട അപേക്ഷ."
        ),
        "pa-IN": (
            "ਤੁਹਾਨੂੰ ਕਿਸ ਤਰ੍ਹਾਂ ਦੀ ਮਦਦ ਚਾਹੀਦੀ ਹੈ? ਉਦਾਹਰਨ: ਸਕਾਲਰਸ਼ਿਪ, ਰੇਸ਼ਨ ਕਾਰਡ, "
            "ਪੈਨਸ਼ਨ, ਫਸਲ ਨੁਕਸਾਨ, ਨੌਕਰੀ, ਕਰਜ਼ਾ, ਸਿਹਤ ਜਾਂ ਰੱਦ ਕੀਤੀ ਅਰਜ਼ੀ।"
        ),
        "od-IN": (
            "ଆପଣ କେମିତି ପ୍ରକାରର ସହାୟତା ଚାହୁଁଛନ୍ତି? ଉଦାହରଣ: ଛାତ୍ରବୃତ୍ତି, ରେସନ କାର୍ଡ, "
            "ପେନସନ, ଫସଲ କ୍ଷତି, ଚାକିରି, ଋଣ, ସ୍ୱାସ୍ଥ୍ୟ କିମ୍ବା ଅସ୍ୱୀକୃତ ଆବେଦନ।"
        ),
    },
}

PROBLEM_FIRST_QUESTION = LOCALIZED_STRINGS["problem_first_question"][DEFAULT_LANGUAGE_CODE]


def get_localized_string(key: str, language_code: str = DEFAULT_LANGUAGE_CODE) -> str:
    localized = LOCALIZED_STRINGS.get(key, {})
    
    if not localized:
        return ""

    if language_code in localized:
        return localized[language_code]

    short_code = language_code.split("-")[0].lower()

    for candidate in localized:
        candidate_short = candidate.split("-")[0].lower()

        if candidate_short == short_code:
            return localized[candidate]

    return localized.get(DEFAULT_LANGUAGE_CODE, "")

# ---------------------------------------------------------------------------
# Language choices
# ---------------------------------------------------------------------------

LANGUAGE_CHOICES = {
    "hindi": "hi-IN",
    "हिंदी": "hi-IN",
    "english": "en-IN",
    "अंग्रेजी": "en-IN",
    "angrezi": "en-IN",
    "bengali": "bn-IN",
    "bangla": "bn-IN",
    "বাংলা": "bn-IN",
    "tamil": "ta-IN",
    "தமிழ்": "ta-IN",
    "telugu": "te-IN",
    "తెలుగు": "te-IN",
    "marathi": "mr-IN",
    "मराठी": "mr-IN",
    "gujarati": "gu-IN",
    "ગુજરાતી": "gu-IN",
    "kannada": "kn-IN",
    "ಕನ್ನಡ": "kn-IN",
    "malayalam": "ml-IN",
    "മലയാളം": "ml-IN",
    "punjabi": "pa-IN",
    "ਪੰਜਾਬੀ": "pa-IN",
    "odia": "od-IN",
    "oriya": "od-IN",
    "ଓଡ଼ିଆ": "od-IN",
}

# ---------------------------------------------------------------------------
# Text normalization / heuristics
# ---------------------------------------------------------------------------

STATE_PREFIXES_TO_STRIP = [
    "main ",
    "mein ",
    "i am from ",
    "i live in ",
    "from ",
    "in ",
    "i'm from ",
    "located in ",
]

RURAL_WORDS = {"rural", "village", "gaon", "gram", "gramin"}
URBAN_WORDS = {"urban", "city", "town", "nagar", "metro"}

PROBLEM_CATEGORY_KEYWORDS = {
    "agriculture": [
        "crop",
        "farming",
        "farmer",
        "seed",
        "irrigation",
        "fertilizer",
        "paddy",
        "wheat",
        "rice",
        "harvest",
        "agri",
        "agriculture",
        "land",
        "soil",
        "livestock",
        "cow",
        "buffalo",
        "goat",
        "poultry",
        "fish",
        "fisher",
        "fisherman",
        "animal husbandry",
        "rain",
        "flood",
        "drought",
    ],
    "education": [
        "scholarship",
        "school",
        "college",
        "fees",
        "admission",
        "student",
        "exam",
    ],
    "employment": [
        "job",
        "employment",
        "unemployed",
        "jobless",
        "berozgar",
        "training",
        "skill",
        "startup",
        "business",
        "work",
        "income",
        "livelihood",
        "mgnrega",
        "nrega",
        "job card",
        "payment not received",
        "wage",
    ],
    "health": [
        "health",
        "hospital",
        "medicine",
        "treatment",
        "doctor",
        "medical",
    ],
    "housing": [
        "house",
        "home",
        "roof",
        "shelter",
        "housing",
        "toilet",
        "sanitation",
    ],
    "ration": [
        "ration",
        "food security",
        "pds",
        "card",
        "subsidized food",
    ],
    "women_child": [
        "pregnant",
        "child",
        "girl",
        "women",
        "mother",
        "anganwadi",
    ],
    "pension": [
        "pension",
        "old age",
        "widow",
        "disability pension",
    ],
    "disability": [
        "disability",
        "disabled",
        "pwd",
        "handicapped",
    ],
    "documents": [
        "aadhaar",
        "bank account",
        "ration card",
        "document",
        "certificate",
        "duplicate",
        "update",
    ],
    "water": [
        "water",
        "drinking water",
        "pipeline",
        "well",
        "pump",
    ],
    "fisheries": [
        "fish",
        "fisherman",
        "fisher",
        "boat",
        "net",
        "marine",
    ],
    "debt": [
        "loan",
        "debt",
        "installment",
        "rejected",
        "pending",
        "delayed",
    ],
}