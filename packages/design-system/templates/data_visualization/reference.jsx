// Reference Component: Data Visualization Slide (Light Theme)

const DataVizSlide = ({ content }) => {
  const data = (content.data || []).map((d) => ({
    name: d.name, value: d.value,
  }));
  const CHART_COLORS = [THEME.primary, THEME.accent, "#F59E0B", THEME.green, "#EC4899", "#8B5CF6"];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 60px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 32, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      <div style={{
        width: 48, height: 4, borderRadius: 2,
        background: THEME.primary, margin: "0 auto 12px",
      }} />
      {content.description && (
        <p style={{
          color: THEME.textSecondary, fontSize: 14,
          textAlign: "center", margin: "0 0 24px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{
        background: THEME.card, borderRadius: 16, padding: 24,
        boxShadow: THEME.cardShadow, border: `1px solid ${THEME.cardBorder}`,
      }}>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={THEME.divider} />
            <XAxis dataKey="name" stroke={THEME.textSecondary} fontSize={12} />
            <YAxis stroke={THEME.textSecondary} fontSize={12} />
            <Tooltip />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {content.insight && (
        <p style={{
          color: THEME.primary, fontSize: 14, fontWeight: 600,
          textAlign: "center", margin: "16px 0 0",
        }}>
          {content.insight}
        </p>
      )}
    </div>
  );
};
