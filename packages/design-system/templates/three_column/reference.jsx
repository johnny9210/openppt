// Reference Component: Three Column Slide (Light Theme)

const ThreeColumnSlide = ({ content }) => {
  const columns = content.columns || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 50px",
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
      <div style={{ display: "flex", gap: 20 }}>
        {columns.map((col, i) => (
          <div key={i} style={{
            flex: 1, background: THEME.card,
            border: `1px solid ${THEME.cardBorder}`,
            borderRadius: 16, padding: "28px 20px",
            boxShadow: THEME.cardShadow,
            textAlign: "center",
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: "50%",
              background: i % 3 === 0 ? THEME.iconBg1 : i % 3 === 1 ? THEME.iconBg2 : THEME.green,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26, color: "#fff", margin: "0 auto 16px",
            }}>
              {col.emoji}
            </div>
            <h3 style={{
              color: THEME.text, fontSize: 17, fontWeight: 700,
              margin: "0 0 8px",
            }}>
              {col.title}
            </h3>
            <p style={{
              color: THEME.textSecondary, fontSize: 13,
              lineHeight: 1.5, margin: "0 0 16px",
            }}>
              {col.description}
            </p>
            {col.metric && (
              <p style={{
                color: THEME.primary, fontSize: 20, fontWeight: 800, margin: 0,
              }}>
                {col.metric}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
