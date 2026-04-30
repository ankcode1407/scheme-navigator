import os
import base64
from sarvamai import SarvamAI
from dotenv import load_dotenv

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

# Language code map — detect from user input pattern
LANGUAGE_CODES = {
    "hindi":     "hi-IN",
    "bengali":   "bn-IN",
    "tamil":     "ta-IN",
    "telugu":    "te-IN",
    "marathi":   "mr-IN",
    "gujarati":  "gu-IN",
    "kannada":   "kn-IN",
    "malayalam": "ml-IN",
    "punjabi":   "pa-IN",
    "odia":      "od-IN",
    "english":   "en-IN",
}

def detect_language(text: str) -> str:
    """
    Detect which Indian language the text is in.
    Returns a BCP-47 language code like 'hi-IN'.
    Falls back to 'hi-IN' if detection fails.
    """
    try:
        response = client.text.identify_language(input=text)
        return response.language_code or "hi-IN"
    except Exception:
        # If detection fails, assume Hindi — most common use case
        return "hi-IN"

def translate_to_user_language(
    english_text: str,
    target_language_code: str = "hi-IN"
) -> str:
    if target_language_code == "en-IN":
        return english_text

    try:
        # Split at double newlines — preserves scheme boundaries
        # Fall back to 900-char hard split only if a section is too long
        sections = english_text.split("\n\n")
        chunks = []
        current = ""

        for section in sections:
            if len(current) + len(section) < 900:
                current += section + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = section + "\n\n"
        if current:
            chunks.append(current.strip())

        translated_chunks = []
        for chunk in chunks:
            response = client.text.translate(
                input=chunk,
                source_language_code="en-IN",
                target_language_code=target_language_code,
                model="sarvam-translate:v1",
            )
            translated_chunks.append(response.translated_text)

        return "\n\n".join(translated_chunks)

    except Exception as e:
        print(f"Translation failed: {e}. Returning English.")
        return english_text