// Reference Component: Summary Slide (Light Theme)

const SummarySlide = ({ content }) => {
  const points = content.points || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 80px",
      display: "flex", flexDirection: "column", justifyContent: "center",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 32, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      <div style={{
        width: 48, height: 4, borderRadius: 2,
        background: THEME.primary, margin: "0 auto 32px",
      }} />

      <div style={{
        display: "flex", flexDirection: "column", gap: 16,
        maxWidth: 600, margin: "0 auto", width: "100%",
      }}>
        {points.map((pt, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "flex-start", gap: 20,
            background: THEME.card, borderRadius: 12, padding: "16px 20px",
            boxShadow: THEME.cardShadow, border: `1px solid ${THEME.cardBorder}`,
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: "50%",
              background: THEME.primary, flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, fontWeight: 800, color: "#fff",
            }}>
              {pt.number || i + 1}
            </div>
            <div>
              <p style={{
                color: THEME.text, fontSize: 17, fontWeight: 700,
                margin: "0 0 4px",
              }}>
                {pt.title}
              </p>
              {pt.description && (
                <p style={{
                  color: THEME.textSecondary, fontSize: 13,
                  lineHeight: 1.5, margin: 0,
                }}>
                  {pt.description}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
