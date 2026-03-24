// Reference Component: Process Flow Slide (Light Theme)

const ProcessFlowSlide = ({ content }) => {
  const steps = content.steps || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 40px",
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
          textAlign: "center", margin: "0 0 40px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        gap: 8, flexWrap: "nowrap",
      }}>
        {steps.map((step, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              background: THEME.card, border: `1px solid ${THEME.cardBorder}`,
              borderRadius: 16, padding: "20px 16px", boxShadow: THEME.cardShadow,
              textAlign: "center", minWidth: 130, maxWidth: 160,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: "50%",
                background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, fontWeight: 700, color: "#fff", margin: "0 auto 10px",
              }}>
                {step.emoji || i + 1}
              </div>
              <p style={{
                color: THEME.text, fontSize: 14, fontWeight: 600, margin: "0 0 4px",
              }}>
                {step.title}
              </p>
              <p style={{
                color: THEME.textSecondary, fontSize: 11,
                lineHeight: 1.3, margin: 0,
              }}>
                {step.description}
              </p>
            </div>
            {i < steps.length - 1 && (
              <div style={{
                color: THEME.primary, fontSize: 24, fontWeight: 700,
              }}>→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
