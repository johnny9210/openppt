// Reference Component: Hero Slide (Light Theme)

const HeroSlide = ({ content }) => {
  const title = content.title || "";
  const accent = content.accent_word || "";

  const renderTitle = () => {
    if (!accent || !title.includes(accent)) {
      return <span>{title}</span>;
    }
    const parts = title.split(accent);
    return (
      <>
        {parts[0]}
        <span style={{ color: THEME.primary }}>{accent}</span>
        {parts.slice(1).join(accent)}
      </>
    );
  };

  return (
    <div style={{
      height: "100%", background: THEME.background,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: "60px 80px", textAlign: "center",
    }}>
      <h1 style={{
        color: THEME.text, fontSize: 52, fontWeight: 800,
        lineHeight: 1.2, margin: "0 0 24px", maxWidth: 700,
      }}>
        {renderTitle()}
      </h1>
      {content.subtitle && (
        <p style={{
          color: THEME.textSecondary, fontSize: 20,
          lineHeight: 1.6, margin: 0, maxWidth: 600,
        }}>
          {content.subtitle}
        </p>
      )}
    </div>
  );
};
