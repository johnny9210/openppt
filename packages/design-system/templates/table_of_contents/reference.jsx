// Reference Component: Table of Contents Slide
// slots.list_layout → item_count <= 5 이면 single_column

const TocSlide = ({ content }) => {
  // {{list_layout_slot}} - item_count에 따라 레이아웃 결정
  return (
    <div style={{ background: THEME.background, padding: 48, height: "100%" }}>
      <h2 style={{ color: THEME.text, fontSize: 28, fontWeight: "bold", marginBottom: 32 }}>
        목차
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {content.items.map((item) => (
          <div key={item.number} style={{
            display: "flex", alignItems: "center", gap: 16,
            borderBottom: `1px solid ${THEME.accent}33`, paddingBottom: 16
          }}>
            <span style={{
              color: THEME.accent, fontSize: 32, fontWeight: "bold",
              minWidth: 48, opacity: 0.6
            }}>
              {String(item.number).padStart(2, "0")}
            </span>
            <span style={{ color: THEME.text, fontSize: 20 }}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
