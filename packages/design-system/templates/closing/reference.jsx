// Reference Component: Closing Slide (Light Theme)

const ClosingSlide = ({ content }) => {
  const resources = content.resources || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 36, fontWeight: 800,
        margin: "0 0 16px", textAlign: "center",
      }}>
        {content.title}
      </h2>

      {content.message && (
        <p style={{
          color: THEME.textSecondary, fontSize: 16,
          textAlign: "center", margin: "0 0 40px",
          lineHeight: 1.6, maxWidth: 500,
        }}>
          {content.message}
        </p>
      )}

      {resources.length > 0 && (
        <div style={{
          display: "flex", gap: 20, flexWrap: "wrap",
          justifyContent: "center",
        }}>
          {resources.map((res, i) => (
            <div key={i} style={{
              background: THEME.card, border: `1px solid ${THEME.cardBorder}`,
              borderRadius: 16, padding: "20px 24px", boxShadow: THEME.cardShadow,
              textAlign: "center", minWidth: 120,
            }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                {res.emoji}
              </div>
              <p style={{
                color: THEME.text, fontSize: 14, fontWeight: 600,
                margin: "0 0 4px",
              }}>
                {res.label}
              </p>
              {res.description && (
                <p style={{
                  color: THEME.textSecondary, fontSize: 11,
                  margin: 0,
                }}>
                  {res.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
