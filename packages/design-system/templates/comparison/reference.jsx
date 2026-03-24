// Reference Component: Comparison Slide
// Left/Right two-column contrast layout

const ComparisonSlide = ({ content }) => {
  const left = content.left || { label: "", items: [] };
  const right = content.right || { label: "", items: [] };

  const Column = ({ data, color, icon }) => (
    <div style={{
      flex: 1, background: `${color}08`,
      border: `1px solid ${color}20`,
      borderRadius: 16, padding: "28px 24px",
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 10, marginBottom: 20,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `${color}20`, display: "flex",
          alignItems: "center", justifyContent: "center", fontSize: 18,
        }}>{icon}</div>
        <h3 style={{
          color, fontSize: 18, fontWeight: 700, margin: 0,
        }}>{data.label}</h3>
      </div>
      {data.items.map((item, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "flex-start", gap: 8,
          marginBottom: 12,
        }}>
          <span style={{ color, fontSize: 14, marginTop: 2 }}>
            {color === THEME.red ? "✕" : "✓"}
          </span>
          <p style={{
            color: THEME.text, opacity: 0.8, fontSize: 14,
            lineHeight: 1.5, margin: 0,
          }}>{item}</p>
        </div>
      ))}
    </div>
  );

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 28, fontWeight: 800,
        margin: "0 0 32px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      <div style={{ display: "flex", gap: 24 }}>
        <Column data={left} color={THEME.red} icon="✕" />
        <Column data={right} color={THEME.green} icon="✓" />
      </div>
    </div>
  );
};
