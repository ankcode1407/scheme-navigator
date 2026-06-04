import { useState } from "react"

function parseSchemeBlock(raw) {
  const lines = String(raw || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

  const scheme = {
    name: "",
    reason: "",
    passed: [],   // NEW: For green audit badges
    failed: [],   // NEW: For red audit badges
    missing: [],  // NEW: For amber audit badges
    docs: [],
    steps: [],
    verify: [],
    portal: "",
    helpline: "",
  }

  let section = null

  for (const line of lines) {
    // 1. Title and ID Extraction
    if (/^ID\s*:/i.test(line)) {
      scheme.id = line.split(":")[1].trim()
      continue
    }

    if (/^\d+\./.test(line)) {
      scheme.name = line.replace(/^\d+\.\s*/, "").trim()
      continue
    }

    // 2. Section Headers (Regex Hooks)
    if (/^why you qualify\s*:/i.test(line) || /^why it matches\s*:/i.test(line) || /^reason\s*:/i.test(line)) {
      scheme.reason = line.split(":").slice(1).join(":").trim()
      continue
    }

    // --- NEW AUDIT HOOKS ---
    if (/^passed criteria\s*:/i.test(line) || /^passed\s*:/i.test(line)) {
      section = "passed"
      continue
    }
    if (/^failed criteria\s*:/i.test(line) || /^failed\s*:/i.test(line) || /^ineligible because\s*:/i.test(line)) {
      section = "failed"
      continue
    }
    if (/^missing data\s*:/i.test(line) || /^missing\s*:/i.test(line) || /^we need to verify\s*:/i.test(line)) {
      section = "missing"
      continue
    }
    // -----------------------

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
      const rawPortal = line.split(":").slice(1).join(":").trim()
      scheme.portal = rawPortal.startsWith("http") ? rawPortal : `https://${rawPortal}`
      section = null
      continue
    }

    if (/^helpline\s*:/i.test(line)) {
      scheme.helpline = line.split(":").slice(1).join(":").trim()
      section = null
      continue
    }

    // 3. Line Item Pushing based on active section
    const cleanLine = line.replace(/^[-*>+\s]+/, "").trim()
    if (!cleanLine) continue // Skip empty bullets

    if (section === "passed" && /^[-*>+]/.test(line)) scheme.passed.push(cleanLine)
    if (section === "failed" && /^[-*>+]/.test(line)) scheme.failed.push(cleanLine)
    if (section === "missing" && /^[-*>+]/.test(line)) scheme.missing.push(cleanLine)
    
    if (section === "docs" && /^[-*>+]/.test(line)) scheme.docs.push(cleanLine)
    if (section === "verify" && /^[-*>+]/.test(line)) scheme.verify.push(cleanLine)
    
    if (section === "steps" && (/^[>+-]/.test(line) || /^\d+\./.test(line))) {
      scheme.steps.push(line.replace(/^[-*>+\s]+/, "").replace(/^\d+\.\s*/, "").trim())
    }
  }

  return scheme
}

import { postFeedback } from "../api"

export default function SchemeCard({ raw, index, sessionId }) {
  const [open, setOpen] = useState(index === 0)
  const [answeredQuals, setAnsweredQuals] = useState({})
  const scheme = parseSchemeBlock(raw)

  if (!scheme.name) return null

  const handleOpenToggle = () => {
    const nextOpen = !open
    setOpen(nextOpen)
    if (nextOpen && scheme.id) {
      postFeedback({ sessionId, schemeId: scheme.id, interactionType: "click" })
    }
  }

  const handleQualification = (req, type) => {
    if (!scheme.id) return
    postFeedback({ sessionId, schemeId: scheme.id, interactionType: type })
    setAnsweredQuals((prev) => ({ ...prev, [req]: type === "qualification_yes" ? "yes" : "no" }))
  }

  // Determine the overall card border based on eligibility status
  const numAnsweredYes = Object.values(answeredQuals).filter(a => a === "yes").length
  const numAnsweredNo = Object.values(answeredQuals).filter(a => a === "no").length

  const isFailed = scheme.failed.length > 0 || numAnsweredNo > 0
  const isPerfectMatch = scheme.passed.length > 0 && (scheme.missing.length === numAnsweredYes) && !isFailed

  let displayReason = scheme.reason
  if (numAnsweredNo > 0) {
    const newlyFailed = Object.keys(answeredQuals).filter(k => answeredQuals[k] === "no")
    displayReason = `You do not qualify: ${[...scheme.failed, ...newlyFailed].join(", ")}`
  } else if (numAnsweredYes > 0) {
    const stillMissing = scheme.missing.filter(m => !answeredQuals[m])
    if (stillMissing.length > 0) {
      displayReason = `Matches your profile, but we need to verify: ${stillMissing.join(", ")}`
    } else {
      const allPassed = [...scheme.passed, ...Object.keys(answeredQuals).filter(k => answeredQuals[k] === "yes")]
      displayReason = `You meet all verified criteria: ${allPassed.join(", ")}`
    }
  }
  
  const borderColor = isFailed ? "#fca5a5" : isPerfectMatch ? "#86efac" : "#e7d5b0"
  const headerBg = open ? (isFailed ? "#fef2f2" : isPerfectMatch ? "#f0fdf4" : "#fef3c7") : "#fffdf5"

  return (
    <div
      style={{
        border: `1px solid ${borderColor}`,
        borderRadius: 16,
        overflow: "hidden",
        marginBottom: 12,
        background: "#fffdf5",
        boxShadow: open ? "0 10px 28px rgba(0,0,0,0.04)" : "none",
        transition: "box-shadow 0.2s ease",
      }}
    >
      <button
        type="button"
        onClick={handleOpenToggle}
        style={{
          width: "100%",
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          background: headerBg,
          border: "none",
          borderBottom: open ? `1px solid ${borderColor}` : "none",
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
              background: isFailed ? "#991b1b" : isPerfectMatch ? "#166534" : "#92400e",
              color: "white",
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
              color: isFailed ? "#7f1d1d" : "#1c1917",
              lineHeight: 1.35,
              textDecoration: isFailed ? "line-through" : "none"
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
          
          {/* Eligibility Audit Badges */}
          {(scheme.passed.length > 0 || scheme.failed.length > 0 || scheme.missing.length > 0) && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {scheme.failed.map((req, i) => (
                <AuditBadge key={`f-${i}`} type="failed" text={req} />
              ))}
              {scheme.missing.map((req, i) => {
                const badgeText = req.trim().toLowerCase() === "state" ? "State: Unverified" : req
                const answered = answeredQuals[req]

                return (
                  <div key={`m-${i}`} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: answered ? "transparent" : "#fef9c3", borderRadius: 999, paddingRight: answered ? 0 : 4 }}>
                    <AuditBadge type={answered === "yes" ? "passed" : answered === "no" ? "failed" : "missing"} text={badgeText} />
                    
                    {!answered && scheme.id && badgeText !== "State: Unverified" && (
                      <div style={{ display: "inline-flex", gap: 4 }}>
                        <button
                          onClick={() => handleQualification(req, "qualification_yes")}
                          style={{
                            background: "#dcfce7", color: "#166534", border: "1px solid #86efac",
                            borderRadius: 999, padding: "2px 8px", fontSize: 10, fontWeight: 700, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace"
                          }}
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => handleQualification(req, "qualification_no")}
                          style={{
                            background: "#fee2e2", color: "#991b1b", border: "1px solid #fca5a5",
                            borderRadius: 999, padding: "2px 8px", fontSize: 10, fontWeight: 700, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace"
                          }}
                        >
                          No
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
              {scheme.passed.map((req, i) => (
                <AuditBadge key={`p-${i}`} type="passed" text={req} />
              ))}
            </div>
          )}

          {displayReason && (
            <div
              style={{
                fontSize: 13,
                color: "#44403c",
                lineHeight: 1.7,
                marginBottom: 14,
                fontStyle: "italic",
                borderLeft: `3px solid ${isFailed ? "#ef4444" : "#d4a843"}`,
                paddingLeft: 12,
              }}
            >
              {displayReason}
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
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// NEW: Sub-component to render beautiful status chips
function AuditBadge({ type, text }) {
  const colors = {
    passed: { bg: "#dcfce7", text: "#166534", border: "#86efac", icon: "✓" },
    failed: { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5", icon: "✕" },
    missing: { bg: "#fef9c3", text: "#854d0e", border: "#fde047", icon: "?" }
  }
  const theme = colors[type]

  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      background: theme.bg,
      color: theme.text,
      border: `1px solid ${theme.border}`,
      padding: "4px 10px",
      borderRadius: 999,
      fontSize: 11,
      fontFamily: "'IBM Plex Mono', monospace",
      fontWeight: 600,
    }}>
      <span style={{ fontWeight: 800 }}>{theme.icon}</span>
      {text}
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