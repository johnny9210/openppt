// Reference Component: Comparison Slide (Light Theme)

const ComparisonSlide = ({ content }) => {
  const left = content.left || { label: "", items: [] };
  const right = content.right || { label: "", items: [] };

  const Column = ({ data, color, icon }) => (
    <div style={{
      flex: 1, background: THEME.card,
      border: `1px solid ${THEME.cardBorder}`,
      borderRadius: 16, padding: "28px 24px",
      boxShadow: THEME.cardShadow,
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 10, marginBottom: 20,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: color, display: "flex",
          alignItems: "center", justifyContent: "center",
          fontSize: 16, color: "#fff",
        }}>{icon}</div>
        <h3 style={{
          color: THEME.text, fontSize: 18, fontWeight: 700, margin: 0,
        }}>{data.label}</h3>
      </div>
      {data.items.map((item, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "flex-start", gap: 8,
          marginBottom: 10,
        }}>
          <span style={{ color, fontSize: 14, marginTop: 2 }}>
            {color === THEME.red ? "✕" : "✓"}
          </span>
          <p style={{
            color: THEME.textSecondary, fontSize: 14,
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
        color: THEME.text, fontSize: 32, fontWeight: 800,
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
