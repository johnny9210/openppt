// Reference Component: Timeline Slide (Light Theme)

const TimelineSlide = ({ content }) => {
  const events = content.events || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 50px",
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
          textAlign: "center", margin: "0 0 40px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{ position: "relative", padding: "20px 0" }}>
        {/* Timeline line */}
        <div style={{
          position: "absolute", top: "50%", left: 40, right: 40,
          height: 3, background: `linear-gradient(90deg, ${THEME.primary}, ${THEME.accent})`,
          borderRadius: 2,
        }} />

        <div style={{
          display: "flex", justifyContent: "space-between",
          position: "relative", padding: "0 20px",
        }}>
          {events.map((evt, i) => (
            <div key={i} style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              width: `${100 / events.length}%`,
            }}>
              <p style={{
                color: THEME.primary, fontSize: 12, fontWeight: 600,
                margin: "0 0 8px", textAlign: "center",
              }}>
                {evt.time}
              </p>
              <div style={{
                width: 40, height: 40, borderRadius: "50%",
                background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, color: "#fff", marginBottom: 12, zIndex: 1,
              }}>
                {evt.emoji}
              </div>
              <div style={{
                background: THEME.card, border: `1px solid ${THEME.cardBorder}`,
                borderRadius: 12, padding: "12px 10px", boxShadow: THEME.cardShadow,
                textAlign: "center", width: "100%",
              }}>
                <p style={{
                  color: THEME.text, fontSize: 13, fontWeight: 600,
                  margin: "0 0 4px",
                }}>
                  {evt.title}
                </p>
                <p style={{
                  color: THEME.textSecondary, fontSize: 11,
                  lineHeight: 1.3, margin: 0,
                }}>
                  {evt.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
