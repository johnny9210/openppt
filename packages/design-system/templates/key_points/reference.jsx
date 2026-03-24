// Reference Component: Key Points Slide
// slots.grid_layout  → item_count에 따라 grid columns 결정
// slots.metric_color → metric 부호에 따라 색상 분기

const KeyPointsSlide = ({ content }) => {
  // {{grid_layout_slot}} - item_count에 따라 column 수 결정
  const gridCols = { 1: 1, 2: 2, 3: 3 }[content.items.length] ?? 2;

  return (
    <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
      <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 24 }}>
        {content.title}
      </h2>
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
        gap: 24
      }}>
        {content.items.map((item, i) => {
          // {{metric_color_slot}} - +green / -red 분기
          const metricColor = item.metric.startsWith("-") ? THEME.red
            : item.metric.startsWith("+") ? THEME.green
            : THEME.accent;
          return (
            <div key={i} style={{
              background: "rgba(255,255,255,0.05)",
              borderRadius: 12, padding: 24,
              border: `1px solid ${THEME.accent}33`
            }}>
              <p style={{ color: THEME.text, opacity: 0.6, fontSize: 13, margin: "0 0 8px" }}>
                {item.headline}
              </p>
              <p style={{ color: THEME.text, fontSize: 14, margin: "0 0 16px" }}>
                {item.body}
              </p>
              <p style={{ color: metricColor, fontSize: 32, fontWeight: "bold", margin: 0 }}>
                {item.metric}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
