// Reference Component: Risk Analysis Slide
// slots.severity_badge → severity 값에 따라 배지 색상 분기
//   high   → THEME.red
//   medium → THEME.yellow
//   low    → THEME.green

const RiskSlide = ({ content }) => {
  // {{severity_badge_slot}} - severity에 따른 색상 매핑
  const badgeColor = {
    high:   THEME.red,
    medium: THEME.yellow,
    low:    THEME.green,
  };

  return (
    <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
      <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 24 }}>
        {content.title}
      </h2>
      {content.risks.map((risk, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "center",
          gap: 16, marginBottom: 16
        }}>
          <span style={{
            background: badgeColor[risk.severity], color: "#fff",
            padding: "4px 10px", borderRadius: 6,
            fontSize: 11, fontWeight: "bold",
            minWidth: 44, textAlign: "center"
          }}>
            {risk.severity.toUpperCase()}
          </span>
          <span style={{ color: THEME.text, flex: 1, fontSize: 14 }}>
            {risk.description}
          </span>
          <span style={{ color: THEME.accent, fontSize: 13 }}>
            → {risk.mitigation}
          </span>
        </div>
      ))}
    </div>
  );
};
