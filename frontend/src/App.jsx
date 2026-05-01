import { useEffect, useMemo, useRef, useState } from "react"

const API = import.meta.env.VITE_API_URL || "https://web-production-33f21.up.railway.app"
const STORAGE_KEY = "schemeNavigator.appState.v3"

const LANGUAGE_OPTIONS = [
  { code: "hi-IN", label: "Hindi", hint: "हिंदी में बात करें" },
  { code: "en-IN", label: "English", hint: "Talk in English" },
]

const QUICK_START_PROMPTS = [
  "My crop failed after heavy rain.",
  "My scholarship application is pending.",
  "I need help with ration card issues.",
  "My application was rejected because of missing documents.",
  "I need a loan to start a small business.",
  "My father needs pension support.",
]

function makeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function safeJsonParse(value, fallback = null) {
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function normalizeLanguageCode(code) {
  if (!code) return null
  const lc = String(code).toLowerCase()
  if (lc.startsWith("hi")) return "hi-IN"
  if (lc.startsWith("en")) return "en-IN"
  return code
}

function languageLabel(code) {
  const normalized = normalizeLanguageCode(code)
  const found = LANGUAGE_OPTIONS.find((x) => x.code === normalized)
  return found?.label || normalized || "Unknown"
}

function loadPersistedState() {
  if (typeof window === "undefined") {
    return {
      messages: [],
      sessionId: null,
      preferredLanguage: null,
    }
  }

  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return {
      messages: [],
      sessionId: null,
      preferredLanguage: null,
    }
  }

  const parsed = safeJsonParse(raw, {})
  const messages = Array.isArray(parsed.messages)
    ? parsed.messages.map((m) => ({
        ...m,
        id: m.id || makeId(),
      }))
    : []

  return {
    messages,
    sessionId: parsed.sessionId || null,
    preferredLanguage: parsed.preferredLanguage || null,
  }
}

function persistState(nextState) {
  if (typeof window === "undefined") return
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      sessionId: nextState.sessionId || null,
      preferredLanguage: nextState.preferredLanguage || null,
      messages: nextState.messages || [],
    })
  )
}

function parseSchemeBlocks(text) {
  const content = String(text || "").trim()
  if (!content) return { type: "text", content: "" }

  if (!content.includes("==================================================")) {
    return { type: "text", content }
  }

  const segments = content.split("==================================================").map((s) => s.trim()).filter(Boolean)
  return {
    type: "schemes",
    intro: segments[0] || "",
    schemes: segments.slice(1),
  }
}

function parseSchemeBlock(raw) {
  const lines = String(raw || "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)

  const scheme = {
    name: "",
    confidence: "",
    reason: "",
    docs: [],
    steps: [],
    verify: [],
    portal: "",
    helpline: "",
  }

  let section = null

  for (const line of lines) {
    if (/^\d+\./.test(line)) {
      scheme.name = line.replace(/^\d+\.\s*/, "").trim()
      continue
    }

    if (/^confidence\s*:/i.test(line)) {
      scheme.confidence = line.split(":").slice(1).join(":").trim()
      continue
    }

    if (/^why you qualify\s*:/i.test(line) || /^why it matches\s*:/i.test(line)) {
      scheme.reason = line.split(":").slice(1).join(":").trim()
      continue
    }

    if (/^documents needed\s*:/i.test(line) || /^documents required\s*:/i.test(line)) {
      section = "docs"
      continue
    }

    if (/^what to do now\s*:/i.test(line) || /^action steps\s*:/i.test(line)) {
      section = "steps"
      continue
    }

    if (/^what to verify\s*:/i.test(line)) {
      section = "verify"
      continue
    }

    if (/^portal\s*:/i.test(line)) {
      scheme.portal = line.split(":").slice(1).join(":").trim()
      section = null
      continue
    }

    if (/^helpline\s*:/i.test(line)) {
      scheme.helpline = line.split(":").slice(1).join(":").trim()
      section = null
      continue
    }

    if (section === "docs" && /^[-•]/.test(line)) {
      scheme.docs.push(line.replace(/^[-•]\s*/, "").trim())
      continue
    }

    if (section === "steps" && (/^[→>-]/.test(line) || /^\d+\./.test(line))) {
      scheme.steps.push(
        line
          .replace(/^[→>-]\s*/, "")
          .replace(/^\d+\.\s*/, "")
          .trim()
      )
      continue
    }

    if (section === "verify" && (/^[→>-]/.test(line) || /^[-•]/.test(line))) {
      scheme.verify.push(line.replace(/^[→>-•]\s*/, "").trim())
      continue
    }
  }

  return scheme
}

function ConfidencePill({ label }) {
  const normalized = String(label || "").trim().toUpperCase()

  const map = {
    HIGH: { bg: "#14532d", text: "#bbf7d0", label: "HIGH" },
    LIKELY: { bg: "#78350f", text: "#fde68a", label: "LIKELY" },
    NEEDS_VERIFICATION: { bg: "#1e3a5f", text: "#bfdbfe", label: "VERIFY" },
  }

  const style = map[normalized] || map.NEEDS_VERIFICATION

  return (
    <span
      style={{
        background: style.bg,
        color: style.text,
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {style.label}
    </span>
  )
}

function SchemeCard({ raw, index }) {
  const [open, setOpen] = useState(index === 0)
  const s = parseSchemeBlock(raw)

  if (!s.name) return null

  return (
    <div
      style={{
        border: "1px solid #e7d5b0",
        borderRadius: 16,
        overflow: "hidden",
        marginBottom: 12,
        background: "#fffdf5",
        boxShadow: open ? "0 10px 28px rgba(180,120,0,0.10)" : "none",
        transition: "box-shadow 0.2s ease",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          background: open ? "#fef3c7" : "#fffdf5",
          border: "none",
          borderBottom: open ? "1px solid #e7d5b0" : "none",
          gap: 12,
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
          <span
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "#92400e",
              color: "#fef3c7",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              fontWeight: 800,
              flexShrink: 0,
              fontFamily: "'IBM Plex Mono', monospace",
            }}
          >
            {index + 1}
          </span>
          <span
            style={{
              fontFamily: "'Libre Baskerville', Georgia, serif",
              fontWeight: 700,
              fontSize: 15,
              color: "#1c1917",
              lineHeight: 1.35,
            }}
          >
            {s.name}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <ConfidencePill label={s.confidence} />
          <span style={{ color: "#92400e", fontSize: 18, fontWeight: 800 }}>
            {open ? "−" : "+"}
          </span>
        </div>
      </button>

      {open && (
        <div style={{ padding: "14px 16px 16px" }}>
          {s.reason && (
            <div
              style={{
                fontSize: 13,
                color: "#44403c",
                lineHeight: 1.7,
                marginBottom: 14,
                fontStyle: "italic",
                borderLeft: "3px solid #d4a843",
                paddingLeft: 12,
              }}
            >
              {s.reason}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                  color: "#92400e",
                  textTransform: "uppercase",
                  fontFamily: "'IBM Plex Mono', monospace",
                  marginBottom: 8,
                }}
              >
                Documents
              </div>

              {s.docs.length > 0 ? (
                s.docs.map((d, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 12,
                      color: "#292524",
                      padding: "4px 0",
                      borderBottom: "1px dashed #ead7b6",
                      display: "flex",
                      gap: 8,
                      lineHeight: 1.45,
                    }}
                  >
                    <span style={{ color: "#d4a843", flexShrink: 0 }}>◆</span>
                    <span>{d}</span>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 12, color: "#78716c" }}>Not specified.</div>
              )}
            </div>

            <div>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                  color: "#166534",
                  textTransform: "uppercase",
                  fontFamily: "'IBM Plex Mono', monospace",
                  marginBottom: 8,
                }}
              >
                Action steps
              </div>

              {s.steps.length > 0 ? (
                s.steps.map((step, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 12,
                      color: "#292524",
                      padding: "4px 0",
                      borderBottom: "1px dashed #bbf7d0",
                      display: "flex",
                      gap: 8,
                      lineHeight: 1.45,
                    }}
                  >
                    <span style={{ color: "#16a34a", flexShrink: 0 }}>→</span>
                    <span>{step}</span>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 12, color: "#78716c" }}>Check the official portal and local office.</div>
              )}
            </div>
          </div>

          {(s.portal || s.helpline || s.verify.length > 0) && (
            <div
              style={{
                marginTop: 14,
                padding: "10px 12px",
                background: "#f5f0e8",
                borderRadius: 12,
                display: "grid",
                gap: 10,
              }}
            >
              {s.portal && (
                <div style={{ fontSize: 12 }}>
                  <span
                    style={{
                      fontSize: 10,
                      color: "#92400e",
                      fontWeight: 700,
                      fontFamily: "'IBM Plex Mono', monospace",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginRight: 8,
                    }}
                  >
                    Portal
                  </span>
                  <a
                    href={s.portal}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#1d4ed8",
                      textDecoration: "none",
                      fontFamily: "'IBM Plex Mono', monospace",
                      wordBreak: "break-word",
                    }}
                  >
                    {s.portal.replace("https://", "")}
                  </a>
                </div>
              )}

              {s.helpline && (
                <div style={{ fontSize: 12 }}>
                  <span
                    style={{
                      fontSize: 10,
                      color: "#92400e",
                      fontWeight: 700,
                      fontFamily: "'IBM Plex Mono', monospace",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginRight: 8,
                    }}
                  >
                    Helpline
                  </span>
                  <span
                    style={{
                      fontFamily: "'IBM Plex Mono', monospace",
                      color: "#292524",
                      fontWeight: 700,
                    }}
                  >
                    {s.helpline}
                  </span>
                </div>
              )}

              {s.verify.length > 0 && (
                <div style={{ fontSize: 12, color: "#57534e", lineHeight: 1.6 }}>
                  <span
                    style={{
                      fontSize: 10,
                      color: "#1e3a5f",
                      fontWeight: 700,
                      fontFamily: "'IBM Plex Mono', monospace",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginRight: 8,
                    }}
                  >
                    Verify
                  </span>
                  {s.verify.join(" ")}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusBanner({ userContext, caseContext, awaitingLanguageSelection, preferredLanguage }) {
  const problem = userContext?.problem_statement || userContext?.specific_problem
  const category = userContext?.problem_category
  const district = userContext?.district
  const status = caseContext?.application_status
  const reason = caseContext?.rejection_reason

  if (!problem && !category && !district && !status && !reason && !awaitingLanguageSelection && preferredLanguage) {
    return null
  }

  return (
    <div
      style={{
        background: "#fffdf5",
        border: "1px solid #ead7b6",
        borderRadius: 16,
        padding: 14,
        marginBottom: 14,
        boxShadow: "0 8px 24px rgba(180,120,0,0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        {preferredLanguage && (
          <span
            style={{
              fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              border: "1px solid #e7d5b0",
              borderRadius: 999,
              padding: "4px 10px",
              background: "#fef3c7",
              color: "#92400e",
              fontWeight: 700,
            }}
          >
            Language: {languageLabel(preferredLanguage)}
          </span>
        )}
        {category && (
          <span
            style={{
              fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              border: "1px solid #e7d5b0",
              borderRadius: 999,
              padding: "4px 10px",
              background: "white",
              color: "#1c1917",
              fontWeight: 700,
            }}
          >
            Problem: {category}
          </span>
        )}
        {district && (
          <span
            style={{
              fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              border: "1px solid #e7d5b0",
              borderRadius: 999,
              padding: "4px 10px",
              background: "white",
              color: "#1c1917",
              fontWeight: 700,
            }}
          >
            District: {district}
          </span>
        )}
        {status && (
          <span
            style={{
              fontSize: 11,
              fontFamily: "'IBM Plex Mono', monospace",
              border: "1px solid #e7d5b0",
              borderRadius: 999,
              padding: "4px 10px",
              background: "#fef3c7",
              color: "#92400e",
              fontWeight: 700,
            }}
          >
            Case: {status}
          </span>
        )}
      </div>

      {!preferredLanguage && (
        <div style={{ fontSize: 13, color: "#57534e", lineHeight: 1.65 }}>
          Pick Hindi or English first. Then tell me the problem you are facing.
        </div>
      )}

      {problem && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65 }}>
          <strong>Problem:</strong> {problem}
        </div>
      )}

      {reason && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65, marginTop: 6 }}>
          <strong>Rejection reason:</strong> {reason}
        </div>
      )}

      {awaitingLanguageSelection && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65, marginTop: 6 }}>
          Choose a language to continue.
        </div>
      )}
    </div>
  )
}

function MessageBubble({ msg }) {
  const parsed = parseSchemeBlocks(msg.text)

  if (msg.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <div
          style={{
            background: "#1c4532",
            color: "#d1fae5",
            borderRadius: "18px 18px 6px 18px",
            padding: "10px 16px",
            maxWidth: "78%",
            fontSize: 14,
            lineHeight: 1.65,
            fontFamily: "'Libre Baskerville', Georgia, serif",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {msg.text}
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 18, alignItems: "flex-start" }}>
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: "50%",
          background: "#92400e",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          marginTop: 2,
          fontSize: 15,
        }}
      >
        🏛
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {parsed.type === "schemes" ? (
          <div>
            {parsed.intro && (
              <div
                style={{
                  fontSize: 14,
                  color: "#292524",
                  lineHeight: 1.75,
                  marginBottom: 14,
                  fontFamily: "'Libre Baskerville', Georgia, serif",
                  whiteSpace: "pre-wrap",
                }}
              >
                {parsed.intro}
              </div>
            )}
            {parsed.schemes.map((raw, i) => (
              <SchemeCard key={i} raw={raw} index={i} />
            ))}
          </div>
        ) : (
          <div
            style={{
              background: "white",
              border: "1px solid #e7d5b0",
              borderRadius: "6px 18px 18px 18px",
              padding: "12px 16px",
              fontSize: 14,
              lineHeight: 1.75,
              color: "#292524",
              fontFamily: "'Libre Baskerville', Georgia, serif",
              maxWidth: "90%",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
            }}
          >
            {msg.text}
          </div>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: "50%",
          background: "#92400e",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          fontSize: 15,
        }}
      >
        🏛
      </div>
      <div
        style={{
          background: "white",
          border: "1px solid #e7d5b0",
          borderRadius: "6px 18px 18px 18px",
          padding: "12px 16px",
          display: "flex",
          gap: 6,
          alignItems: "center",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#d4a843",
              animation: "pulse 1.1s ease-in-out infinite",
              animationDelay: `${i * 0.16}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

function LanguageGate({ onSelect, currentLanguage }) {
  return (
    <div
      style={{
        background: "#fffdf5",
        border: "1px solid #ead7b6",
        borderRadius: 18,
        padding: 18,
        marginBottom: 16,
        boxShadow: "0 8px 24px rgba(180,120,0,0.06)",
      }}
    >
      <div
        style={{
          fontFamily: "'Libre Baskerville', Georgia, serif",
          fontSize: 18,
          fontWeight: 700,
          color: "#1c1917",
          marginBottom: 6,
        }}
      >
        Start in your preferred language
      </div>
      <div
        style={{
          fontSize: 13,
          color: "#57534e",
          lineHeight: 1.65,
          marginBottom: 14,
        }}
      >
        Pick Hindi or English first. The assistant will remember it for this session and speak back in that language.
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {LANGUAGE_OPTIONS.map((option) => (
          <button
            key={option.code}
            type="button"
            onClick={() => onSelect(option.code)}
            style={{
              border: "1px solid #d4a843",
              background: currentLanguage === option.code ? "#fef3c7" : "white",
              color: "#1c1917",
              borderRadius: 12,
              padding: "10px 14px",
              cursor: "pointer",
              minWidth: 132,
              textAlign: "left",
              boxShadow: currentLanguage === option.code ? "0 4px 14px rgba(180,120,0,0.10)" : "none",
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 700, fontFamily: "'Libre Baskerville', Georgia, serif" }}>
              {option.label}
            </div>
            <div style={{ fontSize: 11, color: "#78716c", marginTop: 2, fontFamily: "'IBM Plex Mono', monospace" }}>
              {option.hint}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function chipStyle(active) {
  return {
    border: "1px solid #e7d5b0",
    background: active ? "#fef3c7" : "white",
    color: "#1c1917",
    borderRadius: 999,
    padding: "8px 12px",
    cursor: "pointer",
    fontSize: 12,
    fontFamily: "'Libre Baskerville', Georgia, serif",
    lineHeight: 1.35,
    whiteSpace: "nowrap",
    boxShadow: active ? "0 4px 12px rgba(180,120,0,0.08)" : "none",
  }
}

export default function App() {
  const persisted = useMemo(() => loadPersistedState(), [])

  const [messages, setMessages] = useState(persisted.messages)
  const [input, setInput] = useState("")
  const [sessionId, setSessionId] = useState(persisted.sessionId)
  const [preferredLanguage, setPreferredLanguage] = useState(
    normalizeLanguageCode(persisted.preferredLanguage)
  )
  const [loading, setLoading] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [showSuggestions, setShowSuggestions] = useState(messages.length === 0)
  const [awaitingLanguageSelection, setAwaitingLanguageSelection] = useState(!preferredLanguage)
  const [latestUserContext, setLatestUserContext] = useState(null)
  const [latestCaseContext, setLatestCaseContext] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const lastSpokenMessageIdRef = useRef(null)

  useEffect(() => {
    persistState({
      sessionId,
      preferredLanguage,
      messages,
    })
  }, [sessionId, preferredLanguage, messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, loading, awaitingLanguageSelection])

  function speakResponse(text, lang) {
    if (!voiceEnabled) return
    if (typeof window === "undefined" || !window.speechSynthesis) return

    try {
      window.speechSynthesis.cancel()

      const utterance = new SpeechSynthesisUtterance(String(text || ""))
      utterance.lang = normalizeLanguageCode(lang) || "en-IN"
      utterance.rate = 1
      utterance.pitch = 1
      utterance.volume = 1

      window.speechSynthesis.speak(utterance)
    } catch {
      // silent fallback
    }
  }

  function appendMessage(message) {
    const next = {
      id: makeId(),
      ...message,
    }
    setMessages((prev) => [...prev, next])
    return next
  }

  async function sendMessage(text) {
    const payloadText = String(text || "").trim()
    if (!payloadText || loading) return

    setShowSuggestions(false)
    appendMessage({ role: "user", text: payloadText })
    setInput("")
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: payloadText,
          session_id: sessionId || null,
        }),
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()

      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id)
      }

      const nextPreferred = normalizeLanguageCode(
        data.preferred_language || preferredLanguage || data.language_detected
      )
      if (nextPreferred) {
        setPreferredLanguage(nextPreferred)
      }

      setAwaitingLanguageSelection(Boolean(data.awaiting_language_selection))
      setLatestUserContext(data.user_context || null)
      setLatestCaseContext(data.case_context || null)

      const agentText = String(data.response || "")
      const agentMessage = appendMessage({
        role: "agent",
        text: agentText,
        ttsText: data.response_tts_text || agentText,
        shouldPlayTTS: data.should_play_tts !== false,
        language: nextPreferred || preferredLanguage || data.language_detected || "en-IN",
        contextComplete: Boolean(data.context_complete),
        schemesFound: Number(data.schemes_found || 0),
      })

      if (
        agentMessage.shouldPlayTTS &&
        agentMessage.ttsText &&
        lastSpokenMessageIdRef.current !== agentMessage.id
      ) {
        speakResponse(agentMessage.ttsText, agentMessage.language)
        lastSpokenMessageIdRef.current = agentMessage.id
      }
    } catch {
      appendMessage({
        role: "agent",
        text: "Connection error. Please make sure the backend is running on localhost:8000.",
        shouldPlayTTS: false,
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function selectLanguage(code) {
    const normalized = normalizeLanguageCode(code)
    setPreferredLanguage(normalized)
    setAwaitingLanguageSelection(false)
    sendMessage(normalized === "hi-IN" ? "Hindi" : "English")
  }

  function resetConversation() {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    window.localStorage.removeItem(STORAGE_KEY)
    setMessages([])
    setInput("")
    setSessionId(null)
    setPreferredLanguage(null)
    setAwaitingLanguageSelection(true)
    setShowSuggestions(true)
    setLatestUserContext(null)
    setLatestCaseContext(null)
    lastSpokenMessageIdRef.current = null
    inputRef.current?.focus()
  }

  const headerLanguageLabel = preferredLanguage ? languageLabel(preferredLanguage) : "Choose language"

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { height: 100%; }
        body { background: #f5f0e8; }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .msg-animate { animation: fadeSlideIn 0.22s ease forwards; }
        textarea:focus { outline: none; }
        ::-webkit-scrollbar { width: 7px; }
        ::-webkit-scrollbar-track { background: #f5f0e8; }
        ::-webkit-scrollbar-thumb { background: #d4a843; border-radius: 999px; }
        a:hover { text-decoration: underline; }
        button { font: inherit; }
      `}</style>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          maxWidth: 920,
          margin: "0 auto",
          background: "#f5f0e8",
          color: "#1c1917",
        }}
      >
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "2px solid #92400e",
            background: "#f5f0e8",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexShrink: 0,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 22 }}>🏛</span>
              <span
                style={{
                  fontFamily: "'Libre Baskerville', Georgia, serif",
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#1c1917",
                  letterSpacing: "-0.02em",
                }}
              >
                Scheme Navigator
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "'IBM Plex Mono', monospace",
                  background: "#92400e",
                  color: "#fef3c7",
                  padding: "2px 8px",
                  borderRadius: 999,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              >
                BETA
              </span>
              {sessionId && (
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: "'IBM Plex Mono', monospace",
                    background: "#fef3c7",
                    color: "#92400e",
                    padding: "2px 8px",
                    borderRadius: 999,
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                  }}
                >
                  SESSION ACTIVE
                </span>
              )}
            </div>
            <div
              style={{
                fontSize: 12,
                color: "#78716c",
                marginTop: 3,
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              Problem-first guidance · Hindi and English · auto voice output
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <div
              style={{
                fontSize: 11,
                fontFamily: "'IBM Plex Mono', monospace",
                color: "#92400e",
                textAlign: "right",
                lineHeight: 1.5,
              }}
            >
              <div style={{ fontWeight: 700 }}>{headerLanguageLabel}</div>
              <div style={{ color: "#a8a29e" }}>
                {voiceEnabled ? "Voice on" : "Voice off"}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setVoiceEnabled((v) => !v)}
              style={{
                border: "1px solid #e7d5b0",
                background: voiceEnabled ? "#fef3c7" : "white",
                color: "#92400e",
                borderRadius: 999,
                padding: "8px 12px",
                cursor: "pointer",
                fontSize: 12,
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
              }}
            >
              {voiceEnabled ? "Mute voice" : "Enable voice"}
            </button>

            <button
              type="button"
              onClick={resetConversation}
              style={{
                border: "1px solid #e7d5b0",
                background: "white",
                color: "#1c1917",
                borderRadius: 999,
                padding: "8px 12px",
                cursor: "pointer",
                fontSize: 12,
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
              }}
            >
              New chat
            </button>
          </div>
        </div>

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "18px 18px 8px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {!preferredLanguage && (
            <LanguageGate onSelect={selectLanguage} currentLanguage={preferredLanguage} />
          )}

          <StatusBanner
            userContext={latestUserContext}
            caseContext={latestCaseContext}
            awaitingLanguageSelection={awaitingLanguageSelection}
            preferredLanguage={preferredLanguage}
          />

          {messages.length === 0 && preferredLanguage && (
            <div
              style={{
                background: "#fffdf5",
                border: "1px solid #ead7b6",
                borderRadius: 18,
                padding: 18,
                marginBottom: 16,
              }}
            >
              <div
                style={{
                  fontFamily: "'Libre Baskerville', Georgia, serif",
                  fontSize: 18,
                  fontWeight: 700,
                  color: "#1c1917",
                  marginBottom: 6,
                }}
              >
                What problem are you facing?
              </div>
              <div style={{ fontSize: 13, color: "#57534e", lineHeight: 1.65 }}>
                Start with the issue itself. For example: crop loss, scholarship, ration card, pension, loan, or a rejected application.
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className="msg-animate">
              <MessageBubble msg={m} />
            </div>
          ))}

          {loading && <TypingIndicator />}

          {showSuggestions && (!preferredLanguage || messages.length <= 1) && (
            <div style={{ marginTop: 8, marginBottom: 8 }}>
              <div
                style={{
                  fontSize: 11,
                  color: "#a8a29e",
                  fontFamily: "'IBM Plex Mono', monospace",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 10,
                }}
              >
                Try a problem statement
              </div>

              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                }}
              >
                {QUICK_START_PROMPTS.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => sendMessage(q)}
                    style={chipStyle(false)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "#fef3c7"
                      e.currentTarget.style.borderColor = "#d4a843"
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "white"
                      e.currentTarget.style.borderColor = "#e7d5b0"
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div
          style={{
            padding: "12px 18px 16px",
            borderTop: "1px solid #e7d5b0",
            background: "#f5f0e8",
            flexShrink: 0,
          }}
        >
          {preferredLanguage && (
            <div style={{ marginBottom: 10, display: "flex", flexWrap: "wrap", gap: 8 }}>
              <button
                type="button"
                onClick={() => {
                  setPreferredLanguage(null)
                  setAwaitingLanguageSelection(true)
                }}
                style={chipStyle(true)}
              >
                Change language
              </button>

              <div
                style={{
                  ...chipStyle(false),
                  cursor: "default",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>Language:</span>
                <span>{languageLabel(preferredLanguage)}</span>
              </div>

              <div
                style={{
                  ...chipStyle(false),
                  cursor: "default",
                }}
              >
                {awaitingLanguageSelection ? "Waiting for language selection" : "Ready to help"}
              </div>
            </div>
          )}

          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "flex-end",
              background: "white",
              border: "1.5px solid #d4a843",
              borderRadius: 16,
              padding: "10px 10px 10px 14px",
              boxShadow: "0 4px 18px rgba(180,120,0,0.08)",
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                e.target.style.height = "auto"
                e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              placeholder={
                preferredLanguage === "hi-IN"
                  ? "यहाँ अपनी समस्या लिखें... (Enter to send)"
                  : "Type your problem here... (Enter to send)"
              }
              disabled={loading}
              rows={1}
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                resize: "none",
                background: "transparent",
                fontSize: 14,
                lineHeight: 1.7,
                fontFamily: "'Libre Baskerville', Georgia, serif",
                color: "#1c1917",
                minHeight: 26,
                maxHeight: 140,
                overflow: "auto",
              }}
            />

            <button
              type="button"
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              style={{
                width: 42,
                height: 42,
                borderRadius: 12,
                border: "none",
                cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                background: loading || !input.trim() ? "#e7d5b0" : "#92400e",
                color: loading || !input.trim() ? "#a8a29e" : "#fef3c7",
                fontSize: 18,
                transition: "all 0.15s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                flexShrink: 0,
              }}
            >
              →
            </button>
          </div>

          <div
            style={{
              fontSize: 10,
              color: "#a8a29e",
              marginTop: 6,
              fontFamily: "'IBM Plex Mono', monospace",
              textAlign: "center",
              lineHeight: 1.55,
            }}
          >
            Shift+Enter for a new line · The assistant can speak responses aloud · Session is saved locally for continuity
          </div>
        </div>
      </div>
    </>
  )
}