function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

function printVisitSlip(slip) {
  if (typeof window === "undefined" || !slip) return

  const title = escapeHtml(slip.title)
  const status = escapeHtml(slip.status)
  const reason = escapeHtml(slip.reason)
  const where = escapeHtml(slip.where)
  const ask = escapeHtml(slip.ask)
  const carry = escapeHtml(slip.carry)
  const steps = (slip.steps || []).map(escapeHtml)

  const html = `
    <html>
      <head>
        <title>Visit Slip</title>
        <style>
          body { font-family: Georgia, serif; padding: 24px; color: #1c1917; }
          h1 { font-size: 22px; margin: 0 0 12px; }
          .row { margin: 12px 0; }
          .label { font-weight: 700; font-size: 12px; text-transform: uppercase; color: #92400e; }
          .value { font-size: 16px; line-height: 1.6; margin-top: 3px; }
          li { margin: 7px 0; line-height: 1.5; }
        </style>
      </head>
      <body>
        <h1>Scheme Navigator Visit Slip</h1>
        <div class="row"><div class="label">Case</div><div class="value">${title}</div></div>
        ${status ? `<div class="row"><div class="label">Status</div><div class="value">${status}</div></div>` : ""}
        ${reason ? `<div class="row"><div class="label">Verify</div><div class="value">${reason}</div></div>` : ""}
        ${where ? `<div class="row"><div class="label">Where to go</div><div class="value">${where}</div></div>` : ""}
        ${ask ? `<div class="row"><div class="label">What to ask</div><div class="value">${ask}</div></div>` : ""}
        ${carry ? `<div class="row"><div class="label">What to carry</div><div class="value">${carry}</div></div>` : ""}
        ${
          steps.length
            ? `<div class="row"><div class="label">Next steps</div><ul>${steps.map((step) => `<li>${step}</li>`).join("")}</ul></div>`
            : ""
        }
      </body>
    </html>
  `

  const win = window.open("", "_blank", "width=720,height=900")
  if (!win) return
  win.document.write(html)
  win.document.close()
  win.focus()
  win.print()
}

export default function VisitSlip({ slip }) {
  if (!slip) return null

  const rows = [
    ["Where to go", slip.where],
    ["What to ask", slip.ask],
    ["What to carry", slip.carry],
  ].filter(([, value]) => value)

  return (
    <div
      style={{
        background: "#fef3c7",
        border: "1px solid #d4a843",
        borderRadius: 12,
        padding: 14,
        marginBottom: 14,
        color: "#1c1917",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <Label>Visit slip</Label>
          <div
            style={{
              fontFamily: "'Libre Baskerville', Georgia, serif",
              fontWeight: 700,
              fontSize: 15,
              lineHeight: 1.35,
            }}
          >
            {slip.title}
          </div>
          {slip.status && (
            <div style={{ fontSize: 12, color: "#57534e", marginTop: 4, lineHeight: 1.5 }}>
              Status: {slip.status}
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => printVisitSlip(slip)}
          style={{
            border: "1px solid #92400e",
            background: "#92400e",
            color: "#fef3c7",
            borderRadius: 10,
            padding: "7px 10px",
            cursor: "pointer",
            fontSize: 11,
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 700,
            whiteSpace: "nowrap",
          }}
        >
          Print slip
        </button>
      </div>

      <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
        {rows.map(([label, value]) => (
          <div key={label}>
            <Label>{label}</Label>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: "#292524" }}>{value}</div>
          </div>
        ))}

        {slip.steps.length > 0 && (
          <div>
            <Label color="#166534">Next steps</Label>
            {slip.steps.map((step, index) => (
              <div key={index} style={{ fontSize: 13, lineHeight: 1.55, color: "#292524", padding: "2px 0" }}>
                {index + 1}. {step}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Label({ color = "#92400e", children }) {
  return (
    <div
      style={{
        fontSize: 10,
        fontFamily: "'IBM Plex Mono', monospace",
        color,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 700,
        marginBottom: 3,
      }}
    >
      {children}
    </div>
  )
}
