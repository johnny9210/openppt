// Reference Component: Risk Analysis Slide (Light Theme)

const RiskSlide = ({ content }) => {
  const risks = content.risks || [];
  const LEVEL_COLORS = { high: THEME.red, medium: THEME.yellow, low: THEME.green };

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 32, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      <div style={{
        width: 48, height: 4, borderRadius: 2,
        background: THEME.primary, margin: "0 auto 12px",
      }} />
      {content.description && (
        <p style={{
          color: THEME.textSecondary, fontSize: 14,
          textAlign: "center", margin: "0 0 28px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
        {risks.map((risk, i) => {
          const levelColor = LEVEL_COLORS[risk.level] || THEME.accent;
          return (
            <div key={i} style={{
              background: THEME.card, borderRadius: 12,
              padding: "16px 20px", boxShadow: THEME.cardShadow,
              border: `1px solid ${THEME.cardBorder}`,
              borderLeft: `4px solid ${levelColor}`,
              display: "flex", alignItems: "flex-start", gap: 16,
            }}>
              <span style={{
                background: levelColor, color: "#fff",
                padding: "3px 10px", borderRadius: 6,
                fontSize: 11, fontWeight: 700, flexShrink: 0,
              }}>
                {(risk.level || "").toUpperCase()}
              </span>
              <div style={{ flex: 1 }}>
                <p style={{
                  color: THEME.text, fontSize: 15, fontWeight: 600, margin: "0 0 4px",
                }}>
                  {risk.title}
                </p>
                <p style={{
                  color: THEME.textSecondary, fontSize: 13, margin: "0 0 6px",
                }}>
                  {risk.description}
                </p>
                {risk.mitigation && (
                  <p style={{
                    color: THEME.primary, fontSize: 12, fontWeight: 600, margin: 0,
                  }}>
                    → {risk.mitigation}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
