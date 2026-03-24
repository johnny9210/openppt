// Reference Component: Key Points Slide (Light Theme)

const KeyPointsSlide = ({ content }) => {
  const points = content.points || content.items || [];
  const cols = points.length <= 2 ? 2 : points.length <= 4 ? 2 : 3;

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
          textAlign: "center", margin: "0 0 32px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 20, maxWidth: 800, margin: "0 auto",
      }}>
        {points.map((pt, i) => (
          <div key={i} style={{
            background: THEME.card,
            borderRadius: 16, padding: "24px 20px",
            boxShadow: THEME.cardShadow,
            border: `1px solid ${THEME.cardBorder}`,
            display: "flex", alignItems: "flex-start", gap: 16,
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: "50%", flexShrink: 0,
              background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 24, color: "#fff",
            }}>
              {pt.emoji || "●"}
            </div>
            <div>
              <p style={{
                color: THEME.text, fontSize: 17, fontWeight: 600, margin: "0 0 4px",
              }}>
                {pt.title}
              </p>
              <p style={{
                color: THEME.textSecondary, fontSize: 13, lineHeight: 1.5, margin: 0,
              }}>
                {pt.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
