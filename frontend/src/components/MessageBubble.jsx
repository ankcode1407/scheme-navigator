import SchemeCard from "./SchemeCard"
import VisitSlip from "./VisitSlip"

function parseSchemeBlocks(text) {
  const content = String(text || "").trim()
  if (!content) return { type: "text", content: "" }

  if (!content.includes("==================================================")) {
    return { type: "text", content }
  }

  const segments = content
    .split("==================================================")
    .map((segment) => segment.trim())
    .filter(Boolean)

  return {
    type: "schemes",
    intro: segments[0] || "",
    schemes: segments.slice(1),
  }
}

function cleanListLine(line) {
  return String(line || "")
    .replace(/^[-*>+\s]+/, "")
    .trim()
}

function parseVisitSlip(text) {
  const lines = String(text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

  const readValue = (label) => {
    const found = lines.find((line) => line.toLowerCase().startsWith(label.toLowerCase()))
    return found ? found.split(":").slice(1).join(":").trim() : ""
  }

  const where = readValue("Where to go")
  const ask = readValue("What to ask")
  const carry = readValue("What to carry")

  if (!where && !ask && !carry) return null

  const nextStart = lines.findIndex((line) => /^do this next\s*:/i.test(line))
  const steps =
    nextStart >= 0
      ? lines
          .slice(nextStart + 1)
          .filter((line) => /^[-*>+]/.test(line))
          .map(cleanListLine)
          .slice(0, 3)
      : []

  return {
    title: readValue("Scheme/application") || "Office visit slip",
    status: readValue("Current status"),
    reason: readValue("Reason to verify"),
    where,
    ask,
    carry,
    steps,
  }
}

export function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 16, alignItems: "center" }}>
      <Avatar />
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
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#d4a843",
              animation: "pulse 1.1s ease-in-out infinite",
              animationDelay: `${index * 0.16}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

export default function MessageBubble({ msg }) {
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

  const visitSlip = parseVisitSlip(msg.text)

  return (
    <div style={{ display: "flex", gap: 10, marginBottom: 18, alignItems: "flex-start" }}>
      <Avatar />

      <div style={{ flex: 1, minWidth: 0 }}>
        <VisitSlip slip={visitSlip} />

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
            {parsed.schemes.map((raw, index) => (
              <SchemeCard key={index} raw={raw} index={index} />
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

function Avatar() {
  return (
    <div
      style={{
        width: 34,
        height: 34,
        borderRadius: "50%",
        background: "#92400e",
        color: "#fef3c7",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: 2,
        fontSize: 13,
        fontFamily: "'IBM Plex Mono', monospace",
        fontWeight: 800,
      }}
    >
      SN
    </div>
  )
}
