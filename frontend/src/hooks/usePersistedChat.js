import { useEffect, useMemo, useState } from "react"
import { makeId, normalizeLanguageCode, safeJsonParse } from "../api"

const STORAGE_KEY = "schemeNavigator.appState.v4"

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
    ? parsed.messages.map((message) => ({
        ...message,
        id: message.id || makeId(),
      }))
    : []

  return {
    messages,
    sessionId: parsed.sessionId || null,
    preferredLanguage: normalizeLanguageCode(parsed.preferredLanguage),
  }
}

export function clearPersistedChat() {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(STORAGE_KEY)
}

export function usePersistedChat() {
  const persisted = useMemo(() => loadPersistedState(), [])
  const [messages, setMessages] = useState(persisted.messages)
  const [sessionId, setSessionId] = useState(persisted.sessionId)
  const [preferredLanguage, setPreferredLanguage] = useState(persisted.preferredLanguage)

  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sessionId: sessionId || null,
        preferredLanguage: preferredLanguage || null,
        messages,
      })
    )
  }, [sessionId, preferredLanguage, messages])

  function appendMessage(message) {
    const next = {
      id: makeId(),
      ...message,
    }
    setMessages((prev) => [...prev, next])
    return next
  }

  return {
    messages,
    setMessages,
    appendMessage,
    sessionId,
    setSessionId,
    preferredLanguage,
    setPreferredLanguage,
  }
}