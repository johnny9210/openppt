// Reference Component: Action Plan Slide (Light Theme)

const ActionPlanSlide = ({ content }) => {
  const actions = content.actions || [];

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
          textAlign: "center", margin: "0 0 32px",
        }}>
          {content.description}
        </p>
      )}

      <div style={{ maxWidth: 660, margin: "0 auto", position: "relative" }}>
        {/* Vertical timeline line */}
        <div style={{
          position: "absolute", left: 19, top: 8, bottom: 8,
          width: 3, background: THEME.divider, borderRadius: 2,
        }} />

        {actions.map((action, i) => (
          <div key={i} style={{
            display: "flex", gap: 20, marginBottom: 20, position: "relative",
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: "50%", flexShrink: 0,
              background: i % 2 === 0 ? THEME.iconBg1 : THEME.iconBg2,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, color: "#fff", zIndex: 1,
            }}>
              {i + 1}
            </div>
            <div style={{
              flex: 1, background: THEME.card, borderRadius: 12,
              padding: "16px 20px", boxShadow: THEME.cardShadow,
              border: `1px solid ${THEME.cardBorder}`,
            }}>
              <div style={{
                display: "flex", alignItems: "center", gap: 8, marginBottom: 8,
              }}>
                <p style={{
                  color: THEME.text, fontSize: 16, fontWeight: 700, margin: 0,
                }}>
                  {action.phase}: {action.title}
                </p>
                {action.period && (
                  <span style={{
                    color: THEME.primary, fontSize: 12, fontWeight: 600,
                    background: THEME.subtleBg, padding: "2px 8px",
                    borderRadius: 4,
                  }}>
                    {action.period}
                  </span>
                )}
              </div>
              {(action.tasks || []).map((task, j) => (
                <p key={j} style={{
                  color: THEME.textSecondary, fontSize: 13, margin: "4px 0 0",
                  paddingLeft: 12,
                }}>
                  • {task}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
