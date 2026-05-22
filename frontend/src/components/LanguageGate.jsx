import { LANGUAGE_OPTIONS } from "../api"

export default function LanguageGate({ onSelect, currentLanguage }) {
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
        Pick a language first. The assistant will remember it for this session and speak back in that language.
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
