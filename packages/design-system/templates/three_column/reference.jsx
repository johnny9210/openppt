// Reference Component: Three Column Slide
// Three equal vertical cards side by side

const ThreeColumnSlide = ({ content }) => {
  const columns = content.columns || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 50px",
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
          textAlign: "center", margin: "0 0 32px",
        }}>
          {content.description}
        </p>
      )}
      <div style={{ display: "flex", gap: 20 }}>
        {columns.map((col, i) => (
          <div key={i} style={{
            flex: 1, background: THEME.glass,
            border: `1px solid ${THEME.glassBorder}`,
            borderRadius: 16, padding: "28px 20px",
            textAlign: "center",
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: 16,
              background: `${THEME.accent}18`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 26, margin: "0 auto 16px",
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
              color: THEME.text, opacity: 0.5, fontSize: 13,
              lineHeight: 1.5, margin: "0 0 16px",
            }}>
              {col.description}
            </p>
            {col.metric && (
              <p style={{
                color: THEME.accent, fontSize: 20, fontWeight: 800, margin: 0,
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
