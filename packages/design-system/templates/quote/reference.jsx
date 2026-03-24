// Reference Component: Quote Slide
// Large quote with decorative quotation marks

const QuoteSlide = ({ content }) => {
  return (
    <div style={{
      height: "100%", background: THEME.background,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "60px 80px", position: "relative",
    }}>
      {/* Decorative quote mark */}
      <div style={{
        fontSize: 120, color: THEME.accent, opacity: 0.15,
        position: "absolute", top: 40, left: 60, lineHeight: 1,
        fontFamily: "Georgia, serif",
      }}>"</div>

      {/* Accent bar */}
      <div style={{
        width: 4, height: 60, background: THEME.accent,
        borderRadius: 2, marginBottom: 32,
      }} />

      <blockquote style={{
        color: THEME.text, fontSize: 32, fontWeight: 700,
        lineHeight: 1.5, textAlign: "center",
        margin: "0 0 24px", maxWidth: 650,
      }}>
        {content.quote}
      </blockquote>

      {content.attribution && (
        <p style={{
          color: THEME.text, opacity: 0.4, fontSize: 16, margin: "0 0 8px",
        }}>
          — {content.attribution}
        </p>
      )}
      {content.context && (
        <p style={{
          color: THEME.text, opacity: 0.3, fontSize: 14, margin: 0,
        }}>
          {content.context}
        </p>
      )}
    </div>
  );
};
