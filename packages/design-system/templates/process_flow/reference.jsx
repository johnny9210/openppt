// Reference Component: Process Flow Slide
// Horizontal steps connected by arrows

const ProcessFlowSlide = ({ content }) => {
  const steps = content.steps || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 40px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 28, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      {content.description && (
        <p style={{
          color: THEME.text, opacity: 0.5, fontSize: 14,
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
              background: THEME.glass, border: `1px solid ${THEME.glassBorder}`,
              borderRadius: 16, padding: "20px 16px",
              textAlign: "center", minWidth: 130, maxWidth: 160,
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 12,
                background: `${THEME.primary}22`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 20, margin: "0 auto 10px",
              }}>
                {step.emoji || step.step}
              </div>
              <p style={{
                color: THEME.text, fontSize: 14, fontWeight: 600, margin: "0 0 4px",
              }}>
                {step.title}
              </p>
              <p style={{
                color: THEME.text, opacity: 0.5, fontSize: 11,
                lineHeight: 1.3, margin: 0,
              }}>
                {step.description}
              </p>
            </div>
            {i < steps.length - 1 && (
              <div style={{
                color: THEME.accent, fontSize: 24, fontWeight: 700,
              }}>→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
