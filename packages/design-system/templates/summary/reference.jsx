// Reference Component: Summary Slide
// Numbered key takeaways

const SummarySlide = ({ content }) => {
  const points = content.points || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 80px",
      display: "flex", flexDirection: "column", justifyContent: "center",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 28, fontWeight: 800,
        margin: "0 0 36px", textAlign: "center",
      }}>
        {content.title}
      </h2>

      <div style={{
        display: "flex", flexDirection: "column", gap: 20,
        maxWidth: 600, margin: "0 auto", width: "100%",
      }}>
        {points.map((pt, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "flex-start", gap: 20,
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: 14,
              background: `${THEME.primary}20`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, fontWeight: 800, color: THEME.primary,
              flexShrink: 0,
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
                  color: THEME.text, opacity: 0.5, fontSize: 13,
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
