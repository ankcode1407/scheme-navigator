import { languageLabel } from "../api"

export default function StatusBanner({ userContext, caseContext, awaitingLanguageSelection, preferredLanguage }) {
  const problem = userContext?.problem_statement || userContext?.specific_problem
  const category = userContext?.problem_category
  const district = userContext?.district
  const status = caseContext?.application_status
  const reason = caseContext?.rejection_reason

  if (!problem && !category && !district && !status && !reason && !awaitingLanguageSelection && preferredLanguage) {
    return null
  }

  return (
    <div
      style={{
        background: "#fffdf5",
        border: "1px solid #ead7b6",
        borderRadius: 16,
        padding: 14,
        marginBottom: 14,
        boxShadow: "0 8px 24px rgba(180,120,0,0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        {preferredLanguage && <Badge active>Language: {languageLabel(preferredLanguage)}</Badge>}
        {category && <Badge>Problem: {category}</Badge>}
        {district && <Badge>District: {district}</Badge>}
        {status && <Badge active>Case: {status}</Badge>}
      </div>

      {!preferredLanguage && (
        <div style={{ fontSize: 13, color: "#57534e", lineHeight: 1.65 }}>
          Pick a language first. Then tell me the problem you are facing.
        </div>
      )}

      {problem && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65 }}>
          <strong>Problem:</strong> {problem}
        </div>
      )}

      {reason && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65, marginTop: 6 }}>
          <strong>Rejection reason:</strong> {reason}
        </div>
      )}

      {awaitingLanguageSelection && (
        <div style={{ fontSize: 13, color: "#292524", lineHeight: 1.65, marginTop: 6 }}>
          Choose a language to continue.
        </div>
      )}
    </div>
  )
}

function Badge({ active = false, children }) {
  return (
    <span
      style={{
        fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace",
        border: "1px solid #e7d5b0",
        borderRadius: 999,
        padding: "4px 10px",
        background: active ? "#fef3c7" : "white",
        color: active ? "#92400e" : "#1c1917",
        fontWeight: 700,
      }}
    >
      {children}
    </span>
  )
}
