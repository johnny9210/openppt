// Reference Component: Table of Contents Slide (Light Theme)

const TocSlide = ({ content }) => {
  const items = content.items || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 32, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title || "목차"}
      </h2>
      <div style={{
        width: 48, height: 4, borderRadius: 2,
        background: THEME.primary, margin: "0 auto 36px",
      }} />

      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        {items.map((item, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 20,
            marginBottom: 16, padding: "16px 20px",
            background: THEME.card, borderRadius: 12,
            boxShadow: THEME.cardShadow,
            border: `1px solid ${THEME.cardBorder}`,
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: "50%", flexShrink: 0,
              background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, color: "#fff",
            }}>
              {item.number || i + 1}
            </div>
            <div>
              <p style={{
                color: THEME.text, fontSize: 17, fontWeight: 600, margin: "0 0 2px",
              }}>
                {item.title}
              </p>
              {item.description && (
                <p style={{
                  color: THEME.textSecondary, fontSize: 13, margin: 0,
                }}>
                  {item.description}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
