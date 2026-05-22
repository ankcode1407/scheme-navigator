from __future__ import annotations


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

PROBLEM_FIRST_QUESTION = (
    "What kind of help are you looking for? For example: scholarship, ration card, "
    "pension, crop loss, job, loan, health, or a rejected application."
)

STATE_PREFIXES_TO_STRIP = [
    "main ", "mein ", "i am from ", "i live in ",
    "from ", "in ", "i'm from ", "located in ",
]

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

RURAL_WORDS = {"rural", "village", "gaon", "gram", "gramin"}
URBAN_WORDS = {"urban", "city", "town", "nagar", "metro"}

PROBLEM_CATEGORY_KEYWORDS = {
    "agriculture": [
        "crop", "farming", "farmer", "seed", "irrigation", "fertilizer", "paddy",
        "wheat", "rice", "harvest", "agri", "agriculture", "land", "soil",
        "livestock", "cow", "buffalo", "goat", "poultry", "fish", "fisher",
        "fisherman", "animal husbandry", "rain", "flood", "drought",
    ],
    "education": ["scholarship", "school", "college", "fees", "admission", "student", "exam"],
    "employment": [
        "job", "employment", "unemployed", "jobless", "berozgar",
        "training", "skill", "startup", "business", "work", "income", "livelihood",
        "mgnrega", "nrega", "job card", "payment not received", "wage",
    ],
    "health": ["health", "hospital", "medicine", "treatment", "doctor", "medical"],
    "housing": ["house", "home", "roof", "shelter", "housing", "toilet", "sanitation"],
    "ration": ["ration", "food security", "pds", "card", "subsidized food"],
    "women_child": ["pregnant", "child", "girl", "women", "mother", "anganwadi"],
    "pension": ["pension", "old age", "widow", "disability pension"],
    "disability": ["disability", "disabled", "pwd", "handicapped"],
    "documents": ["aadhaar", "bank account", "ration card", "document", "certificate", "duplicate", "update"],
    "water": ["water", "drinking water", "pipeline", "well", "pump"],
    "fisheries": ["fish", "fisherman", "fisher", "boat", "net", "marine"],
    "debt": ["loan", "debt", "installment", "rejected", "pending", "delayed"],
}
