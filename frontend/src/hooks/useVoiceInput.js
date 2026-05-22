import { useRef, useState } from "react"
import { fileToBase64, requestSpeechToText } from "../api"

export function useVoiceInput({ preferredLanguage, disabled, onTranscript, onError }) {
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const recordedChunksRef = useRef([])

  async function transcribeBlob(blob) {
    if (!blob || blob.size === 0) return
    setTranscribing(true)

    try {
      const audioBase64 = await fileToBase64(blob)
      const data = await requestSpeechToText({
        audioBase64,
        mimeType: blob.type || "audio/webm",
        languageCode: preferredLanguage || "unknown",
      })
      const transcript = String(data.transcript || "").trim()
      if (transcript) {
        await onTranscript(transcript)
      } else {
        onError?.("I could not hear the recording clearly. Please try again or type the problem.")
      }
    } catch {
      onError?.("Voice input failed. Please check microphone permission and try again.")
    } finally {
      setTranscribing(false)
    }
  }

  async function startVoiceInput() {
    if (!preferredLanguage || disabled || transcribing || recording) return

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError?.("Voice recording is not supported in this browser. Please type the problem.")
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      recordedChunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          recordedChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm"
        const blob = new Blob(recordedChunksRef.current, { type: mimeType })
        stream.getTracks().forEach((track) => track.stop())
        mediaRecorderRef.current = null
        recordedChunksRef.current = []
        transcribeBlob(blob)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      onError?.("Microphone permission was not granted. Please allow microphone access or type the problem.")
    }
  }

  function stopVoiceInput() {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === "inactive") return
    recorder.stop()
    setRecording(false)
  }

  function toggleVoiceInput() {
    if (recording) {
      stopVoiceInput()
    } else {
      startVoiceInput()
    }
  }

  function resetVoiceInput() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    recordedChunksRef.current = []
    setRecording(false)
    setTranscribing(false)
  }

  return {
    recording,
    transcribing,
    toggleVoiceInput,
    resetVoiceInput,
  }
}
