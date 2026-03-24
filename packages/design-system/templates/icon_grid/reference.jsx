// Reference Component: Icon Grid Slide (Light Theme)

const IconGridSlide = ({ content }) => {
  const items = content.items || [];
  const cols = items.length <= 4 ? 2 : 3;

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
        gap: 20, maxWidth: 780, margin: "0 auto",
      }}>
        {items.map((item, i) => (
          <div key={i} style={{
            background: THEME.card,
            border: `1px solid ${THEME.cardBorder}`,
            borderRadius: 16, padding: "24px 16px",
            boxShadow: THEME.cardShadow,
            textAlign: "center",
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: "50%",
              background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26, color: "#fff", margin: "0 auto 12px",
            }}>
              {item.emoji}
            </div>
            <p style={{
              color: THEME.text, fontSize: 16, fontWeight: 600, margin: "0 0 4px",
            }}>
              {item.label}
            </p>
            {item.description && (
              <p style={{
                color: THEME.textSecondary, fontSize: 13,
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
