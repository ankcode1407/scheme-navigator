export default function VoiceInputButton({ recording, disabled, voiceEnabled, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      title={recording ? "Stop recording" : "Speak your problem"}
      style={{
        width: 54,
        height: 42,
        borderRadius: 12,
        border: "1px solid #d4a843",
        cursor: disabled ? "not-allowed" : "pointer",
        background: recording ? "#dc2626" : voiceEnabled ? "#fef3c7" : "white",
        color: recording ? "white" : "#92400e",
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
        transition: "all 0.15s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 800,
        flexShrink: 0,
      }}
    >
      {recording ? "Stop" : "Mic"}
    </button>
  )
}
