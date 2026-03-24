// Reference Component: Action Plan Slide
// slots.timeline_layout → item_count에 따라 horizontal_timeline
// slots.owner_tag       → owner 존재 시 렌더링

const ActionPlanSlide = ({ content }) => (
  <div style={{ background: THEME.background, padding: 32, height: "100%" }}>
    <h2 style={{ color: THEME.text, fontSize: 24, fontWeight: "bold", marginBottom: 32 }}>
      {content.title}
    </h2>
    {/* {{timeline_layout_slot}} - horizontal timeline */}
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
          {/* {{owner_tag_slot}} - owner 존재 시 렌더링 */}
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
