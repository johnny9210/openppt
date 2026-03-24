// Reference Component: Data Visualization Slide
// slots.chart_renderer → chart_type에 따라 차트 컴포넌트 선택
// slots.callout_box    → insight_text 존재 시 CalloutBox 렌더링
// slots.bar_highlight  → 마지막 bar에 accent 색상 적용

const DataVizSlide = ({ content }) => {
  // {{chart_renderer_slot}} - chart_type에 따라 분기
  const ChartComponent = {
    bar: BarChartRenderer,
  }[content.chart.chart_type] ?? BarChartRenderer;

  return (
    <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
      <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
        {content.title}
      </h2>
      <div style={{ position: "relative" }}>
        <ChartComponent chart={content.chart} />
        {/* {{callout_box_slot}} - insight_text 존재 시 렌더링 */}
        {content.insight_text && (
          <div style={{
            position: "absolute", top: 0, right: 0,
            background: THEME.accent, color: THEME.text,
            padding: "6px 12px", borderRadius: 8,
            fontSize: 13, fontWeight: "bold"
          }}>
            {content.insight_text}
          </div>
        )}
      </div>
    </div>
  );
};

const BarChartRenderer = ({ chart }) => {
  const data = chart.data.labels.map((label, i) => ({
    name: label,
    value: chart.data.series[0].values[i],
  }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
        <XAxis dataKey="name" stroke={THEME.text} />
        <YAxis stroke={THEME.text} />
        <Tooltip />
        {/* {{bar_highlight_slot}} - 마지막 bar에 accent 색상 */}
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i}
              fill={i === data.length - 1 ? THEME.text : THEME.accent} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
