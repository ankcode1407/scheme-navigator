import { useEffect, useRef, useState } from "react"
import {
  LANGUAGE_OPTIONS,
  QUICK_START_PROMPTS,
  languageLabel,
  normalizeLanguageCode,
  parseLanguageSelection,
  sendChatMessage,
} from "./api"
import LanguageGate from "./components/LanguageGate"
import MessageBubble, { TypingIndicator } from "./components/MessageBubble"
import StatusBanner from "./components/StatusBanner"
import VoiceInputButton from "./components/VoiceInputButton"
import { clearPersistedChat, usePersistedChat } from "./hooks/usePersistedChat"
import { useVoiceInput } from "./hooks/useVoiceInput"
import { useVoiceOutput } from "./hooks/useVoiceOutput"

export default function App() {
  const {
    messages,
    setMessages,
    appendMessage,
    sessionId,
    setSessionId,
    preferredLanguage,
    setPreferredLanguage,
  } = usePersistedChat()

  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(messages.length === 0)
  const [awaitingLanguageSelection, setAwaitingLanguageSelection] = useState(!preferredLanguage)
  const [latestUserContext, setLatestUserContext] = useState(null)
  const [latestCaseContext, setLatestCaseContext] = useState(null)
  const [pendingStateVerification, setPendingStateVerification] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const { voiceEnabled, setVoiceEnabled, speakMessageOnce, resetVoiceOutput } = useVoiceOutput()
  const { recording, transcribing, toggleVoiceInput, resetVoiceInput } = useVoiceInput({
    preferredLanguage,
    disabled: loading,
    onTranscript: async (transcript) => {
      setInput(transcript)
      await sendMessage(transcript)
    },
    onError: (text) => appendMessage({ role: "agent", text, shouldPlayTTS: false }),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, loading, awaitingLanguageSelection])

  async function sendMessage(text) {
    const payloadText = String(text || "").trim()
    if (!payloadText || loading) return
    if (!preferredLanguage && !parseLanguageSelection(payloadText)) return

    setShowSuggestions(false)
    appendMessage({ role: "user", text: payloadText })
    setInput("")
    setLoading(true)

    try {
      const data = await sendChatMessage({
        message: payloadText,
        sessionId,
      })

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

      if (data.needs_state_verification && !pendingStateVerification) {
        setPendingStateVerification(data)
        return
      }

      const agentText = String(data.response || "")
      const agentMessage = appendMessage({
        role: "agent",
        text: agentText,
        ttsText: data.response_tts_text || agentText,
        shouldPlayTTS: data.should_play_tts !== false,
        language: data.response_language || nextPreferred || preferredLanguage || data.language_detected || "en-IN",
        contextComplete: Boolean(data.context_complete),
        schemesFound: Number(data.schemes_found || 0),
      })

      await speakMessageOnce(agentMessage)
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
    const option = LANGUAGE_OPTIONS.find((item) => item.code === normalized)
    sendMessage(option?.label || normalized)
  }

  function resetConversation() {
    resetVoiceInput()
    resetVoiceOutput()
    clearPersistedChat()
    setMessages([])
    setInput("")
    setSessionId(null)
    setPreferredLanguage(null)
    setAwaitingLanguageSelection(true)
    setShowSuggestions(true)
    setLatestUserContext(null)
    setLatestCaseContext(null)
    setPendingStateVerification(null)
    inputRef.current?.focus()
  }

  const headerLanguageLabel = preferredLanguage ? languageLabel(preferredLanguage) : "Choose language"
  const voiceInputDisabled = loading || transcribing || !preferredLanguage

  return (
    <>
      <GlobalStyles />

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
        <Header
          sessionId={sessionId}
          languageLabel={headerLanguageLabel}
          voiceEnabled={voiceEnabled}
          onToggleVoice={() => setVoiceEnabled((value) => !value)}
          onReset={resetConversation}
        />

        <main
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

          {messages.length === 0 && preferredLanguage && <ProblemPrompt />}

          {messages.map((message) => (
            <div key={message.id} className="msg-animate">
              <MessageBubble 
                msg={message} 
                sessionId={sessionId} 
                onSelectChip={(chipText) => {
                  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
                  let originalQuery = lastUserMsg ? lastUserMsg.text : "";
                  
                  const isLangSelect = (text) => {
                    const normalized = String(text || "").trim().toLowerCase();
                    return LANGUAGE_OPTIONS.some(
                      (opt) =>
                        opt.label.toLowerCase() === normalized ||
                        opt.code.toLowerCase() === normalized ||
                        opt.hint.toLowerCase() === normalized
                    );
                  };
                  
                  if (isLangSelect(originalQuery)) {
                    originalQuery = "";
                  }
                  
                  const combinedText = originalQuery ? `${originalQuery}, ${chipText}` : chipText;
                  sendMessage(combinedText);
                }}
              />
            </div>
          ))}

          {pendingStateVerification && (
            <StateVerificationPrompt
              onSubmit={(stateName) => {
                setPendingStateVerification(null)
                sendMessage(`My state is ${stateName}`)
              }}
              onSkip={async () => {
                const data = pendingStateVerification
                setPendingStateVerification(null)
                
                const agentText = String(data.response || "")
                const nextPreferred = normalizeLanguageCode(
                  data.preferred_language || preferredLanguage || data.language_detected
                )
                const agentMessage = appendMessage({
                  role: "agent",
                  text: agentText,
                  ttsText: data.response_tts_text || agentText,
                  shouldPlayTTS: data.should_play_tts !== false,
                  language: data.response_language || nextPreferred || preferredLanguage || data.language_detected || "en-IN",
                  contextComplete: Boolean(data.context_complete),
                  schemesFound: Number(data.schemes_found || 0),
                })
                await speakMessageOnce(agentMessage)
              }}
            />
          )}

          {loading && <TypingIndicator />}

          {showSuggestions && preferredLanguage && messages.length <= 1 && (
            <QuickStartSuggestions onSelect={sendMessage} />
          )}

          <div ref={bottomRef} />
        </main>

        <Composer
          input={input}
          setInput={setInput}
          inputRef={inputRef}
          loading={loading}
          transcribing={transcribing}
          recording={recording}
          preferredLanguage={preferredLanguage}
          awaitingLanguageSelection={awaitingLanguageSelection}
          voiceEnabled={voiceEnabled}
          voiceInputDisabled={voiceInputDisabled}
          onSend={() => sendMessage(input)}
          onVoiceToggle={toggleVoiceInput}
          onChangeLanguage={() => {
            setPreferredLanguage(null)
            setAwaitingLanguageSelection(true)
          }}
        />
      </div>
    </>
  )
}

function Header({ sessionId, languageLabel, voiceEnabled, onToggleVoice, onReset }) {
  return (
    <header
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
          <span
            style={{
              fontFamily: "'Libre Baskerville', Georgia, serif",
              fontSize: 20,
              fontWeight: 700,
              color: "#1c1917",
            }}
          >
            Scheme Navigator
          </span>
          <HeaderPill active>BETA</HeaderPill>
          {sessionId && <HeaderPill>SESSION ACTIVE</HeaderPill>}
        </div>
        <div
          style={{
            fontSize: 12,
            color: "#78716c",
            marginTop: 3,
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          Problem-first guidance - multilingual voice support
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
          <div style={{ fontWeight: 700 }}>{languageLabel}</div>
          <div style={{ color: "#a8a29e" }}>{voiceEnabled ? "Voice on" : "Voice off"}</div>
        </div>

        <HeaderButton active={voiceEnabled} onClick={onToggleVoice}>
          {voiceEnabled ? "Mute voice" : "Enable voice"}
        </HeaderButton>
        <HeaderButton onClick={onReset}>New chat</HeaderButton>
      </div>
    </header>
  )
}

function HeaderPill({ active = false, children }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontFamily: "'IBM Plex Mono', monospace",
        background: active ? "#92400e" : "#fef3c7",
        color: active ? "#fef3c7" : "#92400e",
        padding: "2px 8px",
        borderRadius: 999,
        fontWeight: 700,
        letterSpacing: "0.06em",
      }}
    >
      {children}
    </span>
  )
}

function HeaderButton({ active = false, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        border: "1px solid #e7d5b0",
        background: active ? "#fef3c7" : "white",
        color: active ? "#92400e" : "#1c1917",
        borderRadius: 999,
        padding: "8px 12px",
        cursor: "pointer",
        fontSize: 12,
        fontFamily: "'IBM Plex Mono', monospace",
        fontWeight: 700,
      }}
    >
      {children}
    </button>
  )
}

function StateVerificationPrompt({ onSubmit, onSkip }) {
  const [stateInput, setStateInput] = useState("")

  return (
    <div
      style={{
        background: "#fffdf5",
        border: "1px solid #ead7b6",
        borderRadius: 18,
        padding: 18,
        marginBottom: 16,
      }}
      className="msg-animate"
    >
      <div
        style={{
          fontFamily: "'Libre Baskerville', Georgia, serif",
          fontSize: 15,
          fontWeight: 700,
          color: "#1c1917",
          marginBottom: 12,
        }}
      >
        Some schemes I found are state-specific. Which state are you in?
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          type="text"
          value={stateInput}
          onChange={(e) => setStateInput(e.target.value)}
          placeholder="Enter your state (e.g. Maharashtra)"
          style={{
            flex: 1,
            minWidth: 200,
            padding: "10px 14px",
            border: "1px solid #e7d5b0",
            background: "#ffffff",
            color: "#1c1917",
            borderRadius: 8,
            fontSize: 14,
            fontFamily: "'Libre Baskerville', Georgia, serif",
            outline: "none",
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && stateInput.trim()) {
              onSubmit(stateInput.trim())
            }
          }}
        />
        <button
          onClick={() => onSubmit(stateInput.trim())}
          disabled={!stateInput.trim()}
          style={{
            background: stateInput.trim() ? "#92400e" : "#e7d5b0",
            color: stateInput.trim() ? "#fef3c7" : "#a8a29e",
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            cursor: stateInput.trim() ? "pointer" : "not-allowed",
            fontWeight: 700,
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          Submit
        </button>
        <button
          onClick={onSkip}
          style={{
            background: "transparent",
            color: "#78716c",
            border: "1px solid #d6d3d1",
            borderRadius: 8,
            padding: "8px 16px",
            cursor: "pointer",
            fontWeight: 700,
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          Skip
        </button>
      </div>
    </div>
  )
}

function ProblemPrompt() {
  return (
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
  )
}

function QuickStartSuggestions({ onSelect }) {
  return (
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

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {QUICK_START_PROMPTS.map((prompt, index) => (
          <button
            key={index}
            type="button"
            onClick={() => onSelect(prompt)}
            style={chipStyle(false)}
            onMouseEnter={(event) => {
              event.currentTarget.style.background = "#fef3c7"
              event.currentTarget.style.borderColor = "#d4a843"
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.background = "white"
              event.currentTarget.style.borderColor = "#e7d5b0"
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}

function Composer({
  input,
  setInput,
  inputRef,
  loading,
  transcribing,
  recording,
  preferredLanguage,
  awaitingLanguageSelection,
  voiceEnabled,
  voiceInputDisabled,
  onSend,
  onVoiceToggle,
  onChangeLanguage,
}) {
  const sendDisabled = loading || transcribing || !input.trim()

  return (
    <footer
      style={{
        padding: "12px 18px 16px",
        borderTop: "1px solid #e7d5b0",
        background: "#f5f0e8",
        flexShrink: 0,
      }}
    >
      {preferredLanguage && (
        <div style={{ marginBottom: 10, display: "flex", flexWrap: "wrap", gap: 8 }}>
          <button type="button" onClick={onChangeLanguage} style={chipStyle(true)}>
            Change language
          </button>

          <div style={{ ...chipStyle(false), cursor: "default", display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>Language:</span>
            <span>{languageLabel(preferredLanguage)}</span>
          </div>

          <div style={{ ...chipStyle(false), cursor: "default" }}>
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
          onChange={(event) => {
            setInput(event.target.value)
            event.target.style.height = "auto"
            event.target.style.height = `${Math.min(event.target.scrollHeight, 140)}px`
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              onSend()
            }
          }}
          placeholder={
            !preferredLanguage
              ? "Type your language (e.g., 'hindi') or choose above..."
              : preferredLanguage === "hi-IN"
              ? "Yahan apni samasya likhein... (Enter to send)"
              : "Type your problem here... (Enter to send)"
          }
          disabled={loading || transcribing}
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

        <VoiceInputButton
          recording={recording}
          disabled={voiceInputDisabled}
          voiceEnabled={voiceEnabled}
          onToggle={onVoiceToggle}
        />

        <button
          type="button"
          onClick={onSend}
          disabled={sendDisabled}
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            border: "none",
            cursor: sendDisabled ? "not-allowed" : "pointer",
            background: sendDisabled ? "#e7d5b0" : "#92400e",
            color: sendDisabled ? "#a8a29e" : "#fef3c7",
            fontSize: 18,
            transition: "all 0.15s",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            flexShrink: 0,
          }}
        >
          {">"}
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
        {recording
          ? "Recording... press stop when finished"
          : transcribing
          ? "Transcribing voice with Sarvam..."
          : "Shift+Enter for a new line - speak or type your problem - responses are read aloud"}
      </div>
    </footer>
  )
}

// ----------------------------------------------------------------------
// THESE ARE THE FUNCTIONS THAT WERE MISSING CAUSING THE CRASH
// ----------------------------------------------------------------------

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

function GlobalStyles() {
  return (
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
  )
}