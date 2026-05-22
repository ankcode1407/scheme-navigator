import { useState } from "react"

function parseSchemeBlock(raw) {
  const lines = String(raw || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

  const scheme = {
    name: "",
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

    if (section === "docs" && /^[-*]/.test(line)) {
      scheme.docs.push(line.replace(/^[-*]\s*/, "").trim())
      continue
    }

    if (section === "steps" && (/^[>+-]/.test(line) || /^\d+\./.test(line))) {
      scheme.steps.push(
        line
          .replace(/^[>+-]\s*/, "")
          .replace(/^\d+\.\s*/, "")
          .trim()
      )
      continue
    }

    if (section === "verify" && /^[>+*-]/.test(line)) {
      scheme.verify.push(line.replace(/^[>+*-]\s*/, "").trim())
    }
  }

  return scheme
}

export default function SchemeCard({ raw, index }) {
  const [open, setOpen] = useState(index === 0)
  const scheme = parseSchemeBlock(raw)

  if (!scheme.name) return null

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
        onClick={() => setOpen((value) => !value)}
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
            {scheme.name}
          </span>
        </div>

        <span style={{ color: "#92400e", fontSize: 18, fontWeight: 800 }}>
          {open ? "-" : "+"}
        </span>
      </button>

      {open && (
        <div style={{ padding: "14px 16px 16px" }}>
          {scheme.reason && (
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
              {scheme.reason}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
            <ListSection title="Documents" color="#92400e" items={scheme.docs} empty="Not specified." />
            <ListSection title="Action steps" color="#166534" items={scheme.steps} empty="Check the official portal and local office." />
          </div>

          {(scheme.portal || scheme.helpline || scheme.verify.length > 0) && (
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
              {scheme.portal && (
                <div style={{ fontSize: 12 }}>
                  <MetaLabel>Portal</MetaLabel>
                  <a
                    href={scheme.portal}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#1d4ed8",
                      textDecoration: "none",
                      fontFamily: "'IBM Plex Mono', monospace",
                      wordBreak: "break-word",
                    }}
                  >
                    {scheme.portal.replace("https://", "")}
                  </a>
                </div>
              )}

              {scheme.helpline && (
                <div style={{ fontSize: 12 }}>
                  <MetaLabel>Helpline</MetaLabel>
                  <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: "#292524", fontWeight: 700 }}>
                    {scheme.helpline}
                  </span>
                </div>
              )}

              {scheme.verify.length > 0 && (
                <div style={{ fontSize: 12, color: "#57534e", lineHeight: 1.6 }}>
                  <MetaLabel color="#1e3a5f">Verify</MetaLabel>
                  {scheme.verify.join(" ")}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ListSection({ title, color, items, empty }) {
  return (
    <div>
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.12em",
          color,
          textTransform: "uppercase",
          fontFamily: "'IBM Plex Mono', monospace",
          marginBottom: 8,
        }}
      >
        {title}
      </div>

      {items.length > 0 ? (
        items.map((item, index) => (
          <div
            key={index}
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
            <span style={{ color, flexShrink: 0 }}>-</span>
            <span>{item}</span>
          </div>
        ))
      ) : (
        <div style={{ fontSize: 12, color: "#78716c" }}>{empty}</div>
      )}
    </div>
  )
}

function MetaLabel({ color = "#92400e", children }) {
  return (
    <span
      style={{
        fontSize: 10,
        color,
        fontWeight: 700,
        fontFamily: "'IBM Plex Mono', monospace",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        marginRight: 8,
      }}
    >
      {children}
    </span>
  )
}
