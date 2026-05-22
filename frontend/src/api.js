export const API = import.meta.env.VITE_API_URL || ""

export const LANGUAGE_OPTIONS = [
  { code: "en-IN", label: "English", hint: "Talk in English" },
  { code: "hi-IN", label: "Hindi", hint: "Hindi mein baat karein" },
  { code: "bn-IN", label: "Bengali", hint: "Bangla mein baat karein" },
  { code: "ta-IN", label: "Tamil", hint: "Tamil mein pesungal" },
  { code: "te-IN", label: "Telugu", hint: "Telugu lo matladandi" },
  { code: "mr-IN", label: "Marathi", hint: "Marathi madhye bola" },
  { code: "gu-IN", label: "Gujarati", hint: "Gujarati ma vaat karo" },
  { code: "kn-IN", label: "Kannada", hint: "Kannada dalli matanadi" },
  { code: "ml-IN", label: "Malayalam", hint: "Malayalathil samsarikku" },
  { code: "pa-IN", label: "Punjabi", hint: "Punjabi vich gal karo" },
  { code: "od-IN", label: "Odia", hint: "Odia re katha kuhantu" },
]

export const QUICK_START_PROMPTS = [
  "My crop failed after heavy rain.",
  "My scholarship application is pending.",
  "I need help with ration card issues.",
  "My application was rejected because of missing documents.",
  "I need a loan to start a small business.",
  "My father needs pension support.",
]

export function makeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function safeJsonParse(value, fallback = null) {
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

export function normalizeLanguageCode(code) {
  if (!code) return null
  const lc = String(code).toLowerCase()
  const exact = LANGUAGE_OPTIONS.find((x) => x.code.toLowerCase() === lc)
  if (exact) return exact.code
  if (lc.startsWith("hi")) return "hi-IN"
  if (lc.startsWith("en")) return "en-IN"
  if (lc.startsWith("bn")) return "bn-IN"
  if (lc.startsWith("ta")) return "ta-IN"
  if (lc.startsWith("te")) return "te-IN"
  if (lc.startsWith("mr")) return "mr-IN"
  if (lc.startsWith("gu")) return "gu-IN"
  if (lc.startsWith("kn")) return "kn-IN"
  if (lc.startsWith("ml")) return "ml-IN"
  if (lc.startsWith("pa")) return "pa-IN"
  if (lc.startsWith("od") || lc.startsWith("or")) return "od-IN"
  return code
}

export function languageLabel(code) {
  const normalized = normalizeLanguageCode(code)
  const found = LANGUAGE_OPTIONS.find((x) => x.code === normalized)
  return found?.label || normalized || "Unknown"
}

export function parseLanguageSelection(text) {
  const normalized = String(text || "").trim().toLowerCase()
  const found = LANGUAGE_OPTIONS.find(
    (option) =>
      option.code.toLowerCase() === normalized ||
      option.label.toLowerCase() === normalized ||
      option.hint.toLowerCase() === normalized
  )
  return found?.code || null
}

export async function sendChatMessage({ message, sessionId }) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId || null,
    }),
  })

  if (!res.ok) {
    throw new Error(`Chat request failed with HTTP ${res.status}`)
  }

  return res.json()
}

export async function requestTextToSpeech({ text, languageCode }) {
  const res = await fetch(`${API}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: String(text || ""),
      language_code: normalizeLanguageCode(languageCode) || "en-IN",
    }),
  })

  if (!res.ok) {
    throw new Error(`TTS request failed with HTTP ${res.status}`)
  }

  return res.json()
}

export async function requestSpeechToText({ audioBase64, mimeType, languageCode }) {
  const res = await fetch(`${API}/stt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      audio_base64: audioBase64,
      mime_type: mimeType || "audio/webm",
      language_code: languageCode || "unknown",
    }),
  })

  if (!res.ok) {
    throw new Error(`STT request failed with HTTP ${res.status}`)
  }

  return res.json()
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || "")
      resolve(result.includes(",") ? result.split(",").pop() : result)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
