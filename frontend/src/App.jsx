import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8000"

const SUGGESTED_QUERIES = [
  "Main UP mein kisan hoon, 1.5 hectare zameen hai",
  "I am a daily wage worker in rural Bihar",
  "Pregnant woman in Rajasthan, BPL household",
  "Street vendor in Delhi, no vending certificate yet",
  "Unemployed youth in Maharashtra, age 23",
]

function parseSchemeBlocks(text) {
  if (!text) return { type: "text", content: text }
  if (text.includes("==================================================")) {
    const intro = text.split("==================================================")[0].trim()
    const blocks = text.split("==================================================").slice(1)
    return {
      type: "schemes",
      intro,
      schemes: blocks.map(b => b.trim()).filter(Boolean)
    }
  }
  return { type: "text", content: text }
}

function parseSchemeBlock(raw) {
  const lines = raw.split("\n").map(l => l.trim()).filter(Boolean)
  const scheme = { name: "", confidence: "", reason: "", docs: [], steps: [], portal: "", helpline: "" }
  let section = null
  lines.forEach(line => {
    if (/^\d+\./.test(line)) { scheme.name = line.replace(/^\d+\.\s*/, ""); return }
    if (line.startsWith("Confidence:") || line.includes("आत्मविश्वास:")) {
      scheme.confidence = line.split(":")[1]?.trim() || ""
      return
    }
    if (line.startsWith("Why you qualify:") || line.includes("क्यों योग्य")) {
      scheme.reason = line.split(":").slice(1).join(":").trim(); return
    }
    if (line.startsWith("आप क्यों योग्य हैं:")) {
      scheme.reason = line.replace("आप क्यों योग्य हैं:", "").trim(); return
    }
    if (line.includes("Documents needed") || line.includes("आवश्यक दस्तावेज़") || line.includes("आवश्यक दस्तावेज")) {
      section = "docs"; return
    }
    if (line.includes("What to do now") || line.includes("अब क्या करें")) {
      section = "steps"; return
    }
    if (line.startsWith("Portal:") || line.startsWith("पोर्टल:")) {
      scheme.portal = line.split(":").slice(1).join(":").trim(); section = null; return
    }
    if (line.startsWith("Helpline:") || line.startsWith("हेल्पलाइन:")) {
      scheme.helpline = line.split(":")[1]?.trim() || ""; section = null; return
    }
    if (section === "docs" && (line.startsWith("-") || line.startsWith("•"))) {
      scheme.docs.push(line.replace(/^[-•]\s*/, "")); return
    }
    if (section === "steps" && line.startsWith("→")) {
      scheme.steps.push(line.replace(/^→\s*/, "")); return
    }
  })
  return scheme
}

function ConfidencePill({ label }) {
  const map = {
    "HIGH": { bg: "#14532d", text: "#bbf7d0", label: "HIGH" },
    "उच्च": { bg: "#14532d", text: "#bbf7d0", label: "उच्च" },
    "LIKELY": { bg: "#78350f", text: "#fde68a", label: "LIKELY" },
    "संभवतः": { bg: "#78350f", text: "#fde68a", label: "संभवतः" },
    "NEEDS_VERIFICATION": { bg: "#1e3a5f", text: "#bfdbfe", label: "VERIFY" },
  }
  const style = map[label?.trim()] || map["NEEDS_VERIFICATION"]
  return (
    <span style={{
      background: style.bg, color: style.text,
      padding: "2px 10px", borderRadius: 4,
      fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
      fontWeight: 600, letterSpacing: "0.08em",
      textTransform: "uppercase"
    }}>{style.label}</span>
  )
}

function SchemeCard({ raw, index }) {
  const [open, setOpen] = useState(index === 0)
  const s = parseSchemeBlock(raw)
  if (!s.name) return null

  return (
    <div style={{
      border: "1px solid #d4a843",
      borderRadius: 8,
      overflow: "hidden",
      marginBottom: 10,
      background: "#fffdf5",
      boxShadow: open ? "0 4px 24px rgba(180,120,0,0.10)" : "none",
      transition: "box-shadow 0.2s"
    }}>
      {/* Card header */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          padding: "12px 16px",
          display: "flex", alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          background: open ? "#fef3c7" : "#fffdf5",
          borderBottom: open ? "1px solid #d4a843" : "none",
          gap: 12,
          transition: "background 0.15s"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
          <span style={{
            width: 24, height: 24, borderRadius: "50%",
            background: "#92400e", color: "#fef3c7",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 700, flexShrink: 0,
            fontFamily: "'IBM Plex Mono', monospace"
          }}>{index + 1}</span>
          <span style={{
            fontFamily: "'Libre Baskerville', Georgia, serif",
            fontWeight: 700, fontSize: 14, color: "#1c1917",
            lineHeight: 1.3
          }}>{s.name}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <ConfidencePill label={s.confidence} />
          <span style={{ color: "#92400e", fontSize: 16, fontWeight: 700 }}>
            {open ? "−" : "+"}
          </span>
        </div>
      </div>

      {/* Card body */}
      {open && (
        <div style={{ padding: "14px 16px" }}>
          {s.reason && (
            <div style={{
              fontSize: 13, color: "#44403c", lineHeight: 1.6,
              marginBottom: 14, fontStyle: "italic",
              borderLeft: "3px solid #d4a843", paddingLeft: 10
            }}>{s.reason}</div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {s.docs.length > 0 && (
              <div>
                <div style={{
                  fontSize: 10, fontWeight: 600, letterSpacing: "0.1em",
                  color: "#92400e", textTransform: "uppercase",
                  fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6
                }}>Documents</div>
                {s.docs.map((d, i) => (
                  <div key={i} style={{
                    fontSize: 12, color: "#292524", padding: "3px 0",
                    borderBottom: "1px dashed #e7d5b0", display: "flex", gap: 6
                  }}>
                    <span style={{ color: "#d4a843", flexShrink: 0 }}>◆</span>
                    {d}
                  </div>
                ))}
              </div>
            )}

            {s.steps.length > 0 && (
              <div>
                <div style={{
                  fontSize: 10, fontWeight: 600, letterSpacing: "0.1em",
                  color: "#166534", textTransform: "uppercase",
                  fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6
                }}>Action steps</div>
                {s.steps.map((step, i) => (
                  <div key={i} style={{
                    fontSize: 12, color: "#292524", padding: "3px 0",
                    borderBottom: "1px dashed #bbf7d0", display: "flex", gap: 6
                  }}>
                    <span style={{ color: "#16a34a", flexShrink: 0 }}>→</span>
                    {step}
                  </div>
                ))}
              </div>
            )}
          </div>

          {(s.portal || s.helpline) && (
            <div style={{
              marginTop: 12, padding: "8px 12px",
              background: "#f5f0e8", borderRadius: 6,
              display: "flex", gap: 20, flexWrap: "wrap"
            }}>
              {s.portal && (
                <div style={{ fontSize: 12 }}>
                  <span style={{
                    fontSize: 10, color: "#92400e", fontWeight: 600,
                    fontFamily: "'IBM Plex Mono', monospace",
                    textTransform: "uppercase", letterSpacing: "0.08em",
                    marginRight: 6
                  }}>Portal</span>
                  <a href={s.portal} target="_blank" rel="noreferrer"
                    style={{ color: "#1d4ed8", textDecoration: "none", fontFamily: "'IBM Plex Mono', monospace" }}>
                    {s.portal.replace("https://", "")}
                  </a>
                </div>
              )}
              {s.helpline && (
                <div style={{ fontSize: 12 }}>
                  <span style={{
                    fontSize: 10, color: "#92400e", fontWeight: 600,
                    fontFamily: "'IBM Plex Mono', monospace",
                    textTransform: "uppercase", letterSpacing: "0.08em",
                    marginRight: 6
                  }}>Helpline</span>
                  <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: "#292524", fontWeight: 600 }}>
                    {s.helpline}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Message({ msg }) {
  const parsed = parseSchemeBlocks(msg.text)

  if (msg.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <div style={{
          background: "#1c4532",
          color: "#d1fae5",
          borderRadius: "16px 16px 4px 16px",
          padding: "10px 16px",
          maxWidth: "72%",
          fontSize: 14,
          lineHeight: 1.6,
          fontFamily: "'Libre Baskerville', Georgia, serif",
        }}>{msg.text}</div>
      </div>
    )
  }

  // Agent message
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 20, alignItems: "flex-start" }}>
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: "#92400e",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0, marginTop: 2,
        fontSize: 14
      }}>🏛</div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {parsed.type === "schemes" ? (
          <div>
            {parsed.intro && (
              <div style={{
                fontSize: 14, color: "#292524", lineHeight: 1.7,
                marginBottom: 14,
                fontFamily: "'Libre Baskerville', Georgia, serif",
              }}>{parsed.intro}</div>
            )}
            {parsed.schemes.map((raw, i) => (
              <SchemeCard key={i} raw={raw} index={i} />
            ))}
          </div>
        ) : (
          <div style={{
            background: "white",
            border: "1px solid #e7d5b0",
            borderRadius: "4px 16px 16px 16px",
            padding: "12px 16px",
            fontSize: 14, lineHeight: 1.7,
            color: "#292524",
            fontFamily: "'Libre Baskerville', Georgia, serif",
            maxWidth: "80%"
          }}>{msg.text}</div>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: "#92400e",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0, fontSize: 14
      }}>🏛</div>
      <div style={{
        background: "white", border: "1px solid #e7d5b0",
        borderRadius: "4px 16px 16px 16px",
        padding: "12px 16px", display: "flex", gap: 5, alignItems: "center"
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#d4a843",
            animation: "pulse 1.2s ease-in-out infinite",
            animationDelay: `${i * 0.2}s`
          }} />
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "agent",
      text: "Namaste! I can help you find government schemes you qualify for.\n\nTell me about yourself — your occupation, where you live, and what help you need. You can type in Hindi or English."
    }
  ])
  const [input, setInput] = useState("")
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const mediaRef = useRef(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function sendMessage(text) {
    if (!text.trim() || loading) return
    setShowSuggestions(false)
    setMessages(prev => [...prev, { role: "user", text }])
    setInput("")
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId })
      })
      const data = await res.json()
      if (!sessionId) setSessionId(data.session_id)
      setMessages(prev => [...prev, { role: "agent", text: data.response }])
    } catch {
      setMessages(prev => [...prev, {
        role: "agent",
        text: "Connection error. Please make sure the server is running at localhost:8000."
      }])
    }
    setLoading(false)
  }

  async function toggleRecording() {
    if (recording) {
      mediaRef.current?.stop()
      setRecording(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks = []
      recorder.ondataavailable = e => chunks.push(e.data)
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" })
        const form = new FormData()
        form.append("file", blob, "voice.webm")
        try {
          const res = await fetch(`${API}/transcribe`, { method: "POST", body: form })
          const data = await res.json()
          if (data.text) sendMessage(data.text)
        } catch {
          setMessages(prev => [...prev, {
            role: "agent",
            text: "Voice transcription not available yet. Please type your message."
          }])
        }
        stream.getTracks().forEach(t => t.stop())
      }
      recorder.start()
      mediaRef.current = recorder
      setRecording(true)
    } catch {
      alert("Microphone access denied.")
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #f5f0e8; }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .msg-animate { animation: fadeSlideIn 0.25s ease forwards; }
        textarea:focus { outline: none; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #f5f0e8; }
        ::-webkit-scrollbar-thumb { background: #d4a843; border-radius: 3px; }
        a:hover { text-decoration: underline; }
      `}</style>

      <div style={{
        display: "flex", flexDirection: "column",
        height: "100vh", maxWidth: 780,
        margin: "0 auto",
        fontFamily: "'Libre Baskerville', Georgia, serif",
        background: "#f5f0e8",
      }}>

        {/* Header */}
        <div style={{
          padding: "16px 24px",
          borderBottom: "2px solid #92400e",
          background: "#f5f0e8",
          display: "flex", alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 22 }}>🏛</span>
              <span style={{
                fontFamily: "'Libre Baskerville', Georgia, serif",
                fontSize: 20, fontWeight: 700, color: "#1c1917",
                letterSpacing: "-0.02em"
              }}>Scheme Navigator</span>
              <span style={{
                fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
                background: "#92400e", color: "#fef3c7",
                padding: "2px 8px", borderRadius: 4, fontWeight: 600,
                letterSpacing: "0.08em"
              }}>BETA</span>
            </div>
            <div style={{
              fontSize: 12, color: "#78716c", marginTop: 2,
              fontFamily: "'IBM Plex Mono', monospace"
            }}>
              4,600+ central & state schemes · Hindi & English
            </div>
          </div>
          <div style={{
            fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
            color: "#92400e", textAlign: "right", lineHeight: 1.6
          }}>
            <div style={{ fontWeight: 600 }}>Free · No registration</div>
            <div style={{ color: "#a8a29e" }}>Not an official govt. service</div>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: "auto",
          padding: "20px 24px",
          display: "flex", flexDirection: "column",
        }}>
          {messages.map((m, i) => (
            <div key={i} className="msg-animate">
              <Message msg={m} />
            </div>
          ))}

          {loading && <TypingIndicator />}

          {/* Suggested queries */}
          {showSuggestions && messages.length === 1 && (
            <div style={{ marginTop: 8 }}>
              <div style={{
                fontSize: 11, color: "#a8a29e",
                fontFamily: "'IBM Plex Mono', monospace",
                letterSpacing: "0.08em", textTransform: "uppercase",
                marginBottom: 10
              }}>Try asking</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {SUGGESTED_QUERIES.map((q, i) => (
                  <button key={i} onClick={() => sendMessage(q)} style={{
                    background: "white",
                    border: "1px solid #e7d5b0",
                    borderRadius: 8,
                    padding: "8px 14px",
                    textAlign: "left",
                    cursor: "pointer",
                    fontSize: 13,
                    color: "#44403c",
                    fontFamily: "'Libre Baskerville', Georgia, serif",
                    transition: "all 0.15s",
                    lineHeight: 1.4,
                  }}
                    onMouseEnter={e => {
                      e.target.style.background = "#fef3c7"
                      e.target.style.borderColor = "#d4a843"
                    }}
                    onMouseLeave={e => {
                      e.target.style.background = "white"
                      e.target.style.borderColor = "#e7d5b0"
                    }}
                  >
                    <span style={{ color: "#d4a843", marginRight: 8 }}>→</span>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div style={{
          padding: "12px 24px 16px",
          borderTop: "1px solid #e7d5b0",
          background: "#f5f0e8",
          flexShrink: 0,
        }}>
          <div style={{
            display: "flex", gap: 8, alignItems: "flex-end",
            background: "white",
            border: "1.5px solid #d4a843",
            borderRadius: 12,
            padding: "8px 8px 8px 14px",
            boxShadow: "0 2px 12px rgba(180,120,0,0.08)"
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = "auto"
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px"
              }}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(input)
                }
              }}
              placeholder="Type in Hindi or English... (Enter to send)"
              disabled={loading}
              rows={1}
              style={{
                flex: 1, border: "none", outline: "none",
                resize: "none", background: "transparent",
                fontSize: 14, lineHeight: 1.6,
                fontFamily: "'Libre Baskerville', Georgia, serif",
                color: "#1c1917", minHeight: 24,
                maxHeight: 120, overflow: "auto",
              }}
            />
            <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
              <button
                onClick={toggleRecording}
                title={recording ? "Stop recording" : "Voice input"}
                style={{
                  width: 38, height: 38, borderRadius: 8,
                  border: "none", cursor: "pointer",
                  background: recording ? "#dc2626" : "#fef3c7",
                  color: recording ? "white" : "#92400e",
                  fontSize: 16, transition: "all 0.15s",
                  display: "flex", alignItems: "center", justifyContent: "center"
                }}>
                {recording ? "⏹" : "🎤"}
              </button>
              <button
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim()}
                style={{
                  width: 38, height: 38, borderRadius: 8,
                  border: "none", cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                  background: loading || !input.trim() ? "#e7d5b0" : "#92400e",
                  color: loading || !input.trim() ? "#a8a29e" : "#fef3c7",
                  fontSize: 16, transition: "all 0.15s",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontWeight: 700
                }}>→</button>
            </div>
          </div>
          <div style={{
            fontSize: 10, color: "#a8a29e", marginTop: 6,
            fontFamily: "'IBM Plex Mono', monospace",
            textAlign: "center"
          }}>
            Shift+Enter for new line · This tool provides information only, not legal advice
          </div>
        </div>
      </div>
    </>
  )
}