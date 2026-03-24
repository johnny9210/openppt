// Reference Component: Cover Slide (Light Theme)

const CoverSlide = ({ content }) => {
  const titleSize = content.title && content.title.length > 30 ? 32 : 44;

  return (
    <div style={{
      background: THEME.background, padding: "60px 80px", height: "100%",
      display: "flex", alignItems: "center", position: "relative", overflow: "hidden",
    }}>
      {/* Left: Title area (60%) */}
      <div style={{ flex: "0 0 58%", zIndex: 1 }}>
        <h1 style={{
          color: THEME.text, fontSize: titleSize, fontWeight: 800,
          lineHeight: 1.15, margin: "0 0 16px",
        }}>
          {content.title}
        </h1>
        {content.subtitle && (
          <p style={{
            color: THEME.textSecondary, fontSize: 18, lineHeight: 1.5,
            margin: "0 0 32px", maxWidth: 420,
          }}>
            {content.subtitle}
          </p>
        )}
        <div style={{
          color: THEME.textSecondary, fontSize: 13, display: "flex", gap: 16,
        }}>
          {content.presenter && <span>{content.presenter}</span>}
          {content.date && <span>{content.date}</span>}
        </div>
      </div>
      {/* Right: decorative area placeholder */}
      <div style={{ flex: 1 }} />
    </div>
  );
};
