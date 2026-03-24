// Reference Component: Timeline Slide
// Horizontal timeline with event markers

const TimelineSlide = ({ content }) => {
  const events = content.events || [];

  return (
    <div style={{
      height: "100%", background: THEME.background,
      padding: "48px 50px",
    }}>
      <h2 style={{
        color: THEME.text, fontSize: 28, fontWeight: 800,
        margin: "0 0 8px", textAlign: "center",
      }}>
        {content.title}
      </h2>
      {content.description && (
        <p style={{
          color: THEME.text, opacity: 0.5, fontSize: 14,
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
              {/* Time label */}
              <p style={{
                color: THEME.accent, fontSize: 12, fontWeight: 600,
                margin: "0 0 8px", textAlign: "center",
              }}>
                {evt.time}
              </p>
              {/* Circle marker */}
              <div style={{
                width: 40, height: 40, borderRadius: "50%",
                background: THEME.background,
                border: `3px solid ${THEME.accent}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, marginBottom: 12, zIndex: 1,
              }}>
                {evt.emoji}
              </div>
              {/* Card */}
              <div style={{
                background: THEME.glass, border: `1px solid ${THEME.glassBorder}`,
                borderRadius: 12, padding: "12px 10px",
                textAlign: "center", width: "100%",
              }}>
                <p style={{
                  color: THEME.text, fontSize: 13, fontWeight: 600,
                  margin: "0 0 4px",
                }}>
                  {evt.title}
                </p>
                <p style={{
                  color: THEME.text, opacity: 0.5, fontSize: 11,
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
