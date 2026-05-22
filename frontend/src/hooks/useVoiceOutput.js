import { useRef, useState } from "react"
import { requestTextToSpeech } from "../api"

export function useVoiceOutput() {
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const audioRef = useRef(null)
  const lastSpokenMessageIdRef = useRef(null)

  function stopVoiceOutput() {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
  }

  async function speakResponse(text, languageCode) {
    if (!voiceEnabled || typeof window === "undefined") return

    try {
      stopVoiceOutput()
      const safeLangCode = languageCode || "en-IN"
      const data = await requestTextToSpeech({ text, languageCode: safeLangCode })
      if (!data.audio_base64) return

      const audio = new Audio(`data:${data.audio_mime_type || "audio/mpeg"};base64,${data.audio_base64}`)
      audioRef.current = audio
      await audio.play()
    } catch (error) {
      console.warn("TTS playback failed or was interrupted:", error)
    }
  }

  async function speakMessageOnce(message) {
    if (!message?.shouldPlayTTS || !message.ttsText) return
    if (lastSpokenMessageIdRef.current === message.id) return
    
    const resolvedLanguage = message.response_language || message.language || "en-IN"
    await speakResponse(message.ttsText, resolvedLanguage)
    lastSpokenMessageIdRef.current = message.id
  }

  function resetVoiceOutput() {
    stopVoiceOutput()
    lastSpokenMessageIdRef.current = null
  }

  return {
    voiceEnabled,
    setVoiceEnabled,
    speakResponse,
    speakMessageOnce,
    resetVoiceOutput,
  }
}