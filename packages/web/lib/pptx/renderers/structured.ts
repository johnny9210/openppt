/**
 * Structured slide renderers: comparison, process_flow, timeline, action_plan.
 * Ported from Python pptx_exporter layout logic to PptxGenJS.
 */

import type PptxGenJS from "pptxgenjs";
import {
  SLIDE_W,
  SLIDE_H,
  MARGIN,
  CONTENT_W,
  BODY_Y,
  BODY_H,
  FONT,
  addTitle,
  addSubtitle,
  addAccentBar,
  addCard,
  addIconBadge,
  type PptxTheme,
  type SlideData,
} from "../theme";

// ────────────────────────────────────────────────────────────
// Comparison
// ────────────────────────────────────────────────────────────

export function renderComparison(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content ?? {};
  const title = content.title ?? "";
  const left = content.left ?? { label: "", items: [] };
  const right = content.right ?? { label: "", items: [] };

  // Title (centered)
  addTitle(slide, title, theme, { align: "center", fontSize: 32 });

  const GAP = 0.4;
  const colW = (CONTENT_W - GAP) / 2;
  const colH = BODY_H;
  const leftX = MARGIN;
  const rightX = MARGIN + colW + GAP;
  const colY = BODY_Y;

  // ── Left column (Red / Before) ──
  renderComparisonColumn(slide, leftX, colY, colW, colH, left, theme.red, "\u2715", theme);

  // ── Right column (Green / After) ──
  renderComparisonColumn(slide, rightX, colY, colW, colH, right, theme.green, "\u2713", theme);
}

function renderComparisonColumn(
  slide: any,
  x: number,
  y: number,
  w: number,
  h: number,
  data: { label?: string; items?: string[] },
  color: string,
  icon: string,
  theme: PptxTheme,
): void {
  const items: string[] = (data.items ?? []).slice(0, 10);

  // Card background
  addCard(slide, x, y, w, h, theme);

  // Circle badge at top-center
  const badgeSize = 0.45;
  const badgeX = x + (w - badgeSize) / 2;
  const badgeY = y + 0.25;
  addIconBadge(slide, badgeX, badgeY, badgeSize, color, icon);

  // Label below badge
  slide.addText(data.label ?? "", {
    x: x + 0.2,
    y: badgeY + badgeSize + 0.15,
    w: w - 0.4,
    h: 0.4,
    fontSize: 18,
    fontFace: FONT,
    color: theme.heading,
    bold: true,
    align: "center",
    valign: "middle",
  });

  // Bullet items
  const itemStartY = badgeY + badgeSize + 0.7;
  const dotChar = icon === "\u2713" ? "\u25CF" : "\u25CF"; // filled circle for both
  const bulletText = items.map((item) => ({
    text: `${dotChar}  ${item}\n`,
    options: {
      fontSize: 13,
      color: theme.body,
      fontFace: FONT,
      lineSpacingMultiple: 1.6,
      bullet: false,
    },
  }));

  // Prepend a colored dot indicator per item by using separate text runs
  const runs: any[] = [];
  for (const item of items) {
    runs.push({
      text: `${dotChar} `,
      options: { fontSize: 13, color, fontFace: FONT, bold: true },
    });
    runs.push({
      text: `${item}\n`,
      options: {
        fontSize: 13,
        color: theme.body,
        fontFace: FONT,
        lineSpacingMultiple: 1.6,
      },
    });
  }

  if (runs.length > 0) {
    slide.addText(runs, {
      x: x + 0.35,
      y: itemStartY,
      w: w - 0.7,
      h: h - (itemStartY - y) - 0.2,
      valign: "top",
      lineSpacingMultiple: 1.6,
    });
  }
}

// ────────────────────────────────────────────────────────────
// Process Flow
// ────────────────────────────────────────────────────────────

export function renderProcessFlow(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content ?? {};
  const title = content.title ?? "";
  const description = content.description ?? "";
  const steps: Array<{ icon?: string; title?: string; description?: string }> =
    (content.steps ?? []).slice(0, 5);

  if (steps.length === 0) return;

  // Header
  addTitle(slide, title, theme, { align: "center", fontSize: 32 });
  addAccentBar(slide, theme, { x: SLIDE_W / 2 - 0.3, w: 0.6 });
  addSubtitle(slide, description, theme, { align: "center" });

  const n = steps.length;
  const ARROW_W = 0.4;
  const totalArrows = Math.max(0, n - 1) * ARROW_W;
  const stepW = Math.min(2.0, (CONTENT_W - totalArrows) / n);
  const totalW = n * stepW + totalArrows;
  const startX = (SLIDE_W - totalW) / 2;
  const cardY = BODY_Y + 0.3;
  const cardH = BODY_H - 0.5;

  for (let i = 0; i < n; i++) {
    const step = steps[i];
    const x = startX + i * (stepW + ARROW_W);

    // Card
    addCard(slide, x, cardY, stepW, cardH, theme);

    // Icon badge centered at top of card
    const badgeSize = 0.45;
    const badgeX = x + (stepW - badgeSize) / 2;
    const badgeY = cardY + 0.2;
    const badgeColor = i % 2 === 0 ? theme.primary : theme.accent;
    addIconBadge(slide, badgeX, badgeY, badgeSize, badgeColor, step.icon || String(i + 1));

    // Step title
    slide.addText(step.title ?? "", {
      x: x + 0.1,
      y: badgeY + badgeSize + 0.15,
      w: stepW - 0.2,
      h: 0.5,
      fontSize: 14,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      align: "center",
      valign: "middle",
    });

    // Step description
    if (step.description) {
      slide.addText(step.description, {
        x: x + 0.1,
        y: badgeY + badgeSize + 0.7,
        w: stepW - 0.2,
        h: cardH - badgeSize - 1.1,
        fontSize: 11,
        fontFace: FONT,
        color: theme.body,
        align: "center",
        valign: "top",
        lineSpacingMultiple: 1.3,
      });
    }

    // Arrow between steps
    if (i < n - 1) {
      const arrowX = x + stepW + 0.02;
      const arrowY = cardY + cardH / 2 - 0.2;
      slide.addText("\u2192", {
        x: arrowX,
        y: arrowY,
        w: ARROW_W - 0.04,
        h: 0.4,
        fontSize: 24,
        color: theme.primary,
        fontFace: FONT,
        bold: true,
        align: "center",
        valign: "middle",
      });
    }
  }
}

// ────────────────────────────────────────────────────────────
// Timeline
// ────────────────────────────────────────────────────────────

export function renderTimeline(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content ?? {};
  const title = content.title ?? "";
  const description = content.description ?? "";
  const events: Array<{ date?: string; title?: string; description?: string }> =
    (content.events ?? []).slice(0, 6);

  if (events.length === 0) return;

  // Header
  addTitle(slide, title, theme, { align: "center", fontSize: 32 });
  addAccentBar(slide, theme, { x: SLIDE_W / 2 - 0.3, w: 0.6 });
  addSubtitle(slide, description, theme, { align: "center" });

  const n = events.length;
  const lineY = 3.4;
  const lineX = MARGIN + 0.3;
  const lineW = CONTENT_W - 0.6;

  // Horizontal timeline line
  slide.addShape("rect", {
    x: lineX,
    y: lineY,
    w: lineW,
    h: 0.04,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  const spacing = lineW / Math.max(n, 1);

  for (let i = 0; i < n; i++) {
    const evt = events[i];
    const centerX = lineX + i * spacing + spacing / 2;
    const circleSize = 0.4;
    const circleX = centerX - circleSize / 2;
    const circleColor = i % 2 === 0 ? theme.primary : theme.accent;

    // Date label above
    slide.addText(evt.date ?? "", {
      x: centerX - 0.7,
      y: lineY - 0.9,
      w: 1.4,
      h: 0.3,
      fontSize: 11,
      fontFace: FONT,
      color: theme.primary,
      bold: true,
      align: "center",
      valign: "middle",
    });

    // Circle on timeline
    addIconBadge(slide, circleX, lineY - circleSize / 2 + 0.02, circleSize, circleColor, "\u25CF");

    // Card below timeline
    const cardX = centerX - 0.7;
    const cardY = lineY + 0.35;
    const cardW = 1.4;
    const cardH = SLIDE_H - cardY - 0.4;

    addCard(slide, cardX, cardY, cardW, cardH, theme);

    // Event title
    slide.addText(evt.title ?? "", {
      x: cardX + 0.08,
      y: cardY + 0.1,
      w: cardW - 0.16,
      h: 0.35,
      fontSize: 12,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      align: "center",
      valign: "middle",
    });

    // Event description
    if (evt.description) {
      slide.addText(evt.description, {
        x: cardX + 0.08,
        y: cardY + 0.45,
        w: cardW - 0.16,
        h: cardH - 0.6,
        fontSize: 10,
        fontFace: FONT,
        color: theme.body,
        align: "center",
        valign: "top",
        lineSpacingMultiple: 1.3,
      });
    }
  }
}

// ────────────────────────────────────────────────────────────
// Action Plan
// ────────────────────────────────────────────────────────────

export function renderActionPlan(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content ?? {};
  const title = content.title ?? "";
  const description = content.description ?? "";
  const actions: Array<{
    icon?: string;
    title?: string;
    description?: string;
    timeline?: string;
  }> = (content.actions ?? []).slice(0, 5);

  if (actions.length === 0) return;

  // Header
  addTitle(slide, title, theme, { align: "center", fontSize: 28 });
  addAccentBar(slide, theme, { x: SLIDE_W / 2 - 0.3, w: 0.6 });
  addSubtitle(slide, description, theme, { align: "center" });

  const n = actions.length;
  const lineX = MARGIN + 0.5;
  const cardLeftX = lineX + 0.6;
  const cardW = CONTENT_W - 1.4;
  const availableH = BODY_H - 0.2;
  const itemH = Math.min(1.0, availableH / n);
  const startY = BODY_Y + 0.2;

  // Vertical timeline line
  const lineTopY = startY + 0.15;
  const lineBottomY = startY + (n - 1) * itemH + 0.15;
  slide.addShape("rect", {
    x: lineX + 0.17,
    y: lineTopY,
    w: 0.04,
    h: lineBottomY - lineTopY + 0.1,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  for (let i = 0; i < n; i++) {
    const action = actions[i];
    const y = startY + i * itemH;

    // Numbered circle milestone
    const circleSize = 0.38;
    const circleY = y + (itemH - circleSize) / 2 - 0.05;
    const circleColor = i % 2 === 0 ? theme.primary : theme.accent;
    addIconBadge(slide, lineX, circleY, circleSize, circleColor, String(i + 1));

    // Card to the right
    const cardH = itemH - 0.1;
    addCard(slide, cardLeftX, y, cardW, cardH, theme);

    // Title (+ timeline label if present)
    let titleText = action.title ?? "";
    if (action.timeline) {
      titleText += `  (${action.timeline})`;
    }

    slide.addText(titleText, {
      x: cardLeftX + 0.2,
      y: y + 0.08,
      w: cardW - 0.4,
      h: 0.35,
      fontSize: 16,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      valign: "middle",
    });

    // Description
    if (action.description) {
      slide.addText(action.description, {
        x: cardLeftX + 0.2,
        y: y + 0.42,
        w: cardW - 0.4,
        h: cardH - 0.52,
        fontSize: 12,
        fontFace: FONT,
        color: theme.body,
        valign: "top",
        lineSpacingMultiple: 1.3,
      });
    }
  }
}
