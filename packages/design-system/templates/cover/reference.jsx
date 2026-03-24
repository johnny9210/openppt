// Reference Component: Cover Slide
// slots.title_size → title 길이에 따라 font size 조정
// slots.subtitle   → subtitle 존재 시 렌더링
// slots.background → gradient dark 배경

const CoverSlide = ({ content }) => {
  // {{title_size_slot}} - title 길이 30자 초과 시 font_size_down
  const titleSize = content.title.length > 30 ? 32 : 44;

  return (
    <div style={{
      background: THEME.background, padding: 48, height: "100%",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 16
    }}>
      <h1 style={{ color: THEME.text, fontSize: titleSize,
        fontWeight: "bold", textAlign: "center", margin: 0 }}>
        {content.title}
      </h1>
      {/* {{subtitle_slot}} - subtitle 존재 시 렌더링 */}
      {content.subtitle && (
        <p style={{ color: THEME.accent, fontSize: 18, margin: 0 }}>
          {content.subtitle}
        </p>
      )}
      <p style={{ color: THEME.text, opacity: 0.5, fontSize: 13, margin: 0 }}>
        {content.department} · {content.date}
      </p>
    </div>
  );
};
