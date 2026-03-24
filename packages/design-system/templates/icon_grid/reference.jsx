// Reference Component: Icon Grid Slide
// 2x3 or 3x2 grid of icon + label items

const IconGridSlide = ({ content }) => {
  const items = content.items || [];
  const cols = items.length <= 4 ? 2 : 3;

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
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
          textAlign: "center", margin: "0 0 36px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 20, maxWidth: 700, margin: "0 auto",
      }}>
        {items.map((item, i) => (
          <div key={i} style={{
            background: THEME.glass, border: `1px solid ${THEME.glassBorder}`,
            borderRadius: 16, padding: "24px 16px",
            textAlign: "center",
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: 16,
              background: i % 2 === 0 ? `${THEME.primary}22` : `${THEME.accent}22`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26, margin: "0 auto 12px",
            }}>
              {item.emoji}
            </div>
            <p style={{
              color: THEME.text, fontSize: 15, fontWeight: 600, margin: "0 0 4px",
            }}>
              {item.label}
            </p>
            {item.description && (
              <p style={{
                color: THEME.text, opacity: 0.5, fontSize: 12,
                lineHeight: 1.4, margin: 0,
              }}>
                {item.description}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
