import os
import base64
import io
from sarvamai import SarvamAI
from dotenv import load_dotenv

load_dotenv()

_sarvam_client = None

def get_sarvam_client():
    global _sarvam_client
    if _sarvam_client is None:
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY environment variable is not set")
        _sarvam_client = SarvamAI(api_subscription_key=api_key)
    return _sarvam_client

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

SUPPORTED_TTS_LANGUAGES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
    "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN",
}

SUPPORTED_STT_LANGUAGES = SUPPORTED_TTS_LANGUAGES | {"unknown"}

MIME_TO_AUDIO_CODEC = {
    "audio/webm": "webm",
    "audio/webm;codecs=opus": "webm",
    "audio/ogg": "ogg",
    "audio/ogg;codecs=opus": "ogg",
    "audio/mp4": "mp4",
    "audio/mpeg": "mpeg",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


def normalize_language_code(language_code: str | None, fallback: str = "hi-IN") -> str:
    if not language_code:
        return fallback

    text = str(language_code).strip()
    lowered = text.lower()
    if lowered in LANGUAGE_CODES:
        return LANGUAGE_CODES[lowered]

    for code in SUPPORTED_STT_LANGUAGES:
        if lowered == code.lower():
            return code

    if lowered.startswith("or-"):
        return "od-IN"

    return fallback

def detect_language(text: str) -> str:
    """
    Detect which Indian language the text is in.
    Returns a BCP-47 language code like 'hi-IN'.
    Falls back to 'hi-IN' if detection fails.
    """
    try:
        response = get_sarvam_client().text.identify_language(input=text)
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
            response = get_sarvam_client().text.translate(
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


def synthesize_bulbul_tts(
    text: str,
    target_language_code: str = "hi-IN",
    speaker: str = "anushka",
) -> str:
    """
    Return base64-encoded MP3 audio from Sarvam Bulbul TTS.
    """
    clean_text = " ".join(str(text or "").split())
    if not clean_text:
        return ""
    target_language_code = normalize_language_code(target_language_code, fallback="hi-IN")
    if target_language_code not in SUPPORTED_TTS_LANGUAGES:
        target_language_code = "hi-IN"

    response = get_sarvam_client().text_to_speech.convert(
        text=clean_text[:1800],
        target_language_code=target_language_code,
        speaker=speaker,
        model="bulbul:v2",
        output_audio_codec="mp3",
        enable_preprocessing=True,
    )
    audios = getattr(response, "audios", None) or []
    return audios[0] if audios else ""


def _codec_from_mime(mime_type: str | None) -> str:
    if not mime_type:
        return "webm"
    lowered = mime_type.lower().split(";")[0]
    return MIME_TO_AUDIO_CODEC.get(mime_type.lower()) or MIME_TO_AUDIO_CODEC.get(lowered) or "webm"


def transcribe_audio_base64(
    audio_base64: str,
    mime_type: str = "audio/webm",
    language_code: str = "unknown",
) -> dict:
    audio_bytes = base64.b64decode(audio_base64)
    if not audio_bytes:
        return {"transcript": "", "language_code": language_code, "language_probability": None}

    normalized_language = normalize_language_code(language_code, fallback="unknown")
    if normalized_language not in SUPPORTED_STT_LANGUAGES:
        normalized_language = "unknown"

    codec = _codec_from_mime(mime_type)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"recording.{codec}"

    response = get_sarvam_client().speech_to_text.transcribe(
        file=audio_file,
        model="saarika:v2.5",
        mode="transcribe",
        language_code=normalized_language,
        input_audio_codec=codec,
    )

    return {
        "transcript": getattr(response, "transcript", "") or "",
        "language_code": getattr(response, "language_code", None) or normalized_language,
        "language_probability": getattr(response, "language_probability", None),
    }
