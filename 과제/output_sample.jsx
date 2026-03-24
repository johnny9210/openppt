import { useState } from "react";
import {
  BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

// ── Design System Theme ──────────────────────────────
const THEME = {
  primary:    "#1B3A6B",
  accent:     "#2E86AB",
  background: "#0A0F1E",
  text:       "#F0F4FF",
  red:        "#E53E3E",
  yellow:     "#F6C90E",
  green:      "#38A169",
};

// ── SlideFactory: type → 컴포넌트 dispatch ────────────
const SlideFactory = ({ slide }) => {
  const map = {
    cover:              CoverSlide,
    table_of_contents:  TocSlide,
    data_visualization: DataVizSlide,
    key_points:         KeyPointsSlide,
    risk_analysis:      RiskSlide,
    action_plan:        ActionPlanSlide,
  };
  const Component = map[slide.type];
  return Component ? <Component {...slide} /> : null;
};

// ── [slide_001] cover ─────────────────────────────────
// slots.title_size → title 길이에 따라 font size 조정
// slots.subtitle   → subtitle 존재 시 렌더링
const CoverSlide = ({ content }) => {
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

// ── [slide_002] table_of_contents ─────────────────────
// slots.list_layout → item_count <= 5 이므로 single_column 적용
const TocSlide = ({ content }) => (
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

// ── [slide_003] data_visualization ───────────────────
// slots.chart_renderer → chart_type=bar 이므로 BarChart 선택
// slots.callout_box    → insight_text 존재 시 CalloutBox 렌더링
// slots.bar_highlight  → 마지막 bar에 accent 색상 적용
const DataVizSlide = ({ content }) => {
  const ChartComponent = {
    bar:  BarChartRenderer,
    // line: LineChartRenderer,  (미구현 슬롯)
    // pie:  PieChartRenderer,   (미구현 슬롯)
  }[content.chart.chart_type] ?? BarChartRenderer;

  return (
    <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
      <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
        {content.title}
      </h2>
      <div style={{ position: "relative" }}>
        <ChartComponent chart={content.chart} />
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

// ── [slide_004] key_points ────────────────────────────
// slots.grid_layout  → item_count=3 이므로 three_column_slot 적용
// slots.metric_color → metric 부호에 따라 색상 분기 (+green / -red)
const KeyPointsSlide = ({ content }) => {
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

// ── [slide_005] risk_analysis ─────────────────────────
// slots.severity_badge → severity 값에 따라 배지 색상 분기
//   high   → THEME.red
//   medium → THEME.yellow
//   low    → THEME.green
const RiskSlide = ({ content }) => {
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

// ── [slide_006] action_plan ───────────────────────────
// slots.timeline_layout → item_count=3 이므로 horizontal_timeline_slot 적용
// slots.owner_tag       → owner 존재 시 렌더링
const ActionPlanSlide = ({ content }) => (
  <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
    <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 32 }}>
      {content.title}
    </h2>
    <div style={{ display: "flex", gap: 0 }}>
      {content.timeline_items.map((item, i) => (
        <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ width: "100%", height: 2, background: THEME.accent, marginBottom: 16 }} />
          <div style={{
            background: THEME.accent, color: THEME.text,
            borderRadius: 20, padding: "4px 14px",
            fontSize: 13, fontWeight: "bold", marginBottom: 12
          }}>
            {item.month}
          </div>
          <p style={{ color: THEME.text, fontSize: 14, textAlign: "center", margin: "0 0 8px" }}>
            {item.action}
          </p>
          {item.owner && (
            <span style={{
              color: THEME.accent, fontSize: 12,
              border: `1px solid ${THEME.accent}`,
              borderRadius: 4, padding: "2px 8px"
            }}>
              {item.owner}
            </span>
          )}
        </div>
      ))}
    </div>
  </div>
);

// ── Presentation Root ─────────────────────────────────
export default function Presentation({ spec }) {
  const [current, setCurrent] = useState(0);
  const slides = spec.ppt_state.presentation.slides;

  return (
    <div style={{
      background: "#050810", width: "100vw", height: "100vh",
      display: "flex", flexDirection: "column"
    }}>
      <div style={{
        flex: 1, display: "flex",
        alignItems: "center", justifyContent: "center", padding: 32
      }}>
        <div style={{
          width: "100%", maxWidth: 900,
          aspectRatio: "16/9", borderRadius: 16, overflow: "hidden",
          boxShadow: "0 25px 60px rgba(0,0,0,0.5)"
        }}>
          <SlideFactory slide={slides[current]} />
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: 8, paddingBottom: 16 }}>
        {slides.map((_, i) => (
          <button key={i} onClick={() => setCurrent(i)} style={{
            width: 8, height: 8, borderRadius: "50%", border: "none",
            background: i === current ? THEME.accent : "rgba(255,255,255,0.2)",
            cursor: "pointer"
          }} />
        ))}
      </div>
    </div>
  );
}
