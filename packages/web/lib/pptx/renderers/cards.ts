/**
 * Card-based slide renderers for PptxGenJS.
 *
 * Covers: table_of_contents, key_points, icon_grid, three_column, summary.
 * Layout values ported from the Python pptx_exporter to match the preview.
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

// ── Table of Contents ────────────────────────────────────────────

export function renderToc(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content || {};
  const items = (content.items || []) as Array<{
    number?: string | number;
    title?: string;
    description?: string;
  }>;

  // Title (centered)
  addTitle(slide, content.title || "Contents", theme, {
    fontSize: 32,
    align: "center",
  });

  // Accent bar (centered)
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.25,
    y: 1.15,
    w: 0.5,
  });

  // Numbered items – staggered vertically
  let y = BODY_Y;
  const circleX = 1.5;
  const circleSize = 0.45;
  const textX = circleX + circleSize + 0.25; // 2.2
  const textW = SLIDE_W - textX - MARGIN; // ~9.63

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const number = String(item.number ?? i + 1);
    const circleColor = i % 2 === 0 ? theme.primary : theme.accent;

    // Number circle
    addIconBadge(slide, circleX, y, circleSize, circleColor, number);

    // Item title
    slide.addText(item.title || "", {
      x: textX,
      y,
      w: textW,
      h: 0.35,
      fontSize: 20,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      valign: "middle",
    });

    // Optional description
    if (item.description) {
      slide.addText(item.description, {
        x: textX,
        y: y + 0.35,
        w: textW,
        h: 0.3,
        fontSize: 14,
        fontFace: FONT,
        color: theme.body,
        lineSpacingMultiple: 1.3,
      });
    }

    y += 0.85;
  }
}

// ── Key Points ───────────────────────────────────────────────────

export function renderKeyPoints(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content || {};
  const points = (
    content.points || content.items || []
  ).slice(0, 6) as Array<{
    icon?: string;
    emoji?: string;
    title?: string;
    description?: string;
    metric?: string;
  }>;

  // Title (centered)
  addTitle(slide, content.title || "", theme, {
    fontSize: 32,
    align: "center",
  });

  // Accent bar (centered)
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.25,
    y: 1.05,
    w: 0.5,
  });

  // Description
  if (content.description) {
    addSubtitle(slide, content.description, theme, {
      y: 1.25,
      align: "center",
    });
  }

  if (points.length === 0) return;

  // Grid layout matching Python: up to 3 columns, wrapping rows
  const cols = Math.min(points.length, 3);
  const gap = 0.35;
  const cardW = (11.0 - (cols - 1) * gap) / cols;
  const startX = (SLIDE_W - (cardW * cols + gap * (cols - 1))) / 2;
  const startY = 1.9;
  const cardH = 3.2;
  const iconSize = 0.65;

  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * (cardW + gap);
    const y = startY + row * (cardH + 0.3);

    // Card background
    addCard(slide, x, y, cardW, cardH, theme);

    // Icon badge (centered at top of card)
    const emoji = pt.icon || pt.emoji || "●";
    const circleColor = i % 2 === 0 ? theme.primary : theme.accent;
    const cx = x + (cardW - iconSize) / 2;
    addIconBadge(slide, cx, y + 0.3, iconSize, circleColor, emoji);

    // Title (centered below icon)
    slide.addText(pt.title || "", {
      x: x + 0.2,
      y: y + 1.15,
      w: cardW - 0.4,
      h: 0.4,
      fontSize: 17,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      align: "center",
      valign: "top",
    });

    // Description (centered below title)
    if (pt.description) {
      slide.addText(pt.description, {
        x: x + 0.2,
        y: y + 1.6,
        w: cardW - 0.4,
        h: 1.0,
        fontSize: 12,
        fontFace: FONT,
        color: theme.body,
        align: "center",
        lineSpacingMultiple: 1.3,
        valign: "top",
      });
    }

    // Metric (centered at bottom of card)
    if (pt.metric) {
      slide.addText(pt.metric, {
        x: x + 0.2,
        y: y + 2.65,
        w: cardW - 0.4,
        h: 0.35,
        fontSize: 14,
        fontFace: FONT,
        color: theme.primary,
        bold: true,
        align: "center",
        valign: "middle",
      });
    }
  }
}

// ── Icon Grid ────────────────────────────────────────────────────

export function renderIconGrid(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content || {};
  const items = (content.items || []).slice(0, 6) as Array<{
    icon?: string;
    emoji?: string;
    label?: string;
    title?: string;
    description?: string;
  }>;

  // Title (centered)
  addTitle(slide, content.title || "", theme, {
    fontSize: 32,
    align: "center",
  });

  // Accent bar (centered)
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.25,
    y: 1.05,
    w: 0.5,
  });

  // Description
  if (content.description) {
    addSubtitle(slide, content.description, theme, {
      y: 1.25,
      align: "center",
    });
  }

  if (items.length === 0) return;

  // Grid: <=4 items → 2 cols, else 3 cols (matches Python)
  const cols = items.length <= 4 ? 2 : 3;
  const gap = 0.25;
  const cardW = (10.5 - (cols - 1) * gap) / cols;
  const startX = (SLIDE_W - (cardW * cols + gap * (cols - 1))) / 2;
  const startY = 1.9;
  const cardH = 1.6;
  const rowGap = 1.8;
  const iconSize = 0.55;

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * (cardW + gap);
    const y = startY + row * rowGap;

    // Card background
    addCard(slide, x, y, cardW, cardH, theme);

    // Icon badge (centered at top of card)
    const emoji = item.icon || item.emoji || "●";
    const circleColor = i % 2 === 0 ? theme.primary : theme.accent;
    const cx = x + (cardW - iconSize) / 2;
    addIconBadge(slide, cx, y + 0.15, iconSize, circleColor, emoji);

    // Label (centered below icon)
    slide.addText(item.label || item.title || "", {
      x: x + 0.2,
      y: y + 0.8,
      w: cardW - 0.4,
      h: 0.3,
      fontSize: 16,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      align: "center",
      valign: "top",
    });

    // Description
    if (item.description) {
      slide.addText(item.description, {
        x: x + 0.2,
        y: y + 1.1,
        w: cardW - 0.4,
        h: 0.4,
        fontSize: 12,
        fontFace: FONT,
        color: theme.body,
        align: "center",
        lineSpacingMultiple: 1.3,
        valign: "top",
      });
    }
  }
}

// ── Three Column ─────────────────────────────────────────────────

export function renderThreeColumn(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content || {};
  const columns = (content.columns || []).slice(0, 3) as Array<{
    icon?: string;
    emoji?: string;
    title?: string;
    description?: string;
    metric?: string;
  }>;

  // Title (centered)
  addTitle(slide, content.title || "", theme, {
    fontSize: 32,
    align: "center",
  });

  // Accent bar (centered)
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.25,
    y: 1.05,
    w: 0.5,
  });

  // Description
  if (content.description) {
    addSubtitle(slide, content.description, theme, {
      y: 1.25,
      align: "center",
    });
  }

  if (columns.length === 0) return;

  // Layout: equal-width tall cards (matches Python)
  const cols = columns.length;
  const gap = 0.3;
  const cardW = (11.0 - (cols - 1) * gap) / cols;
  const startX = (SLIDE_W - (cardW * cols + gap * (cols - 1))) / 2;
  const y = 1.9;
  const cardH = 4.5;
  const iconSize = 0.55;

  // Alternating colors for columns (primary, accent, green)
  const colColors = [theme.primary, theme.accent, theme.green];

  for (let i = 0; i < columns.length; i++) {
    const col = columns[i];
    const x = startX + i * (cardW + gap);

    // Card background
    addCard(slide, x, y, cardW, cardH, theme);

    // Icon badge (centered at top)
    const emoji = col.icon || col.emoji || "●";
    const circleColor = colColors[i % colColors.length];
    const cx = x + (cardW - iconSize) / 2;
    addIconBadge(slide, cx, y + 0.25, iconSize, circleColor, emoji);

    // Title (centered below icon)
    slide.addText(col.title || "", {
      x: x + 0.2,
      y: y + 0.95,
      w: cardW - 0.4,
      h: 0.35,
      fontSize: 17,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      align: "center",
      valign: "top",
    });

    // Description
    if (col.description) {
      slide.addText(col.description, {
        x: x + 0.2,
        y: y + 1.4,
        w: cardW - 0.4,
        h: 1.5,
        fontSize: 13,
        fontFace: FONT,
        color: theme.body,
        align: "center",
        lineSpacingMultiple: 1.3,
        valign: "top",
      });
    }

    // Metric at bottom (large bold primary)
    if (col.metric) {
      slide.addText(col.metric, {
        x: x + 0.2,
        y: y + 3.5,
        w: cardW - 0.4,
        h: 0.5,
        fontSize: 20,
        fontFace: FONT,
        color: theme.primary,
        bold: true,
        align: "center",
        valign: "middle",
      });
    }
  }
}

// ── Summary ──────────────────────────────────────────────────────

export function renderSummary(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const content = data.content || {};
  const points = (content.points || []).slice(0, 7) as Array<{
    number?: string | number;
    title?: string;
    description?: string;
  }>;

  // Title (centered)
  addTitle(slide, content.title || "", theme, {
    fontSize: 32,
    align: "center",
  });

  // Accent bar (centered)
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.25,
    y: 1.05,
    w: 0.5,
  });

  if (points.length === 0) return;

  // Stacked numbered cards (matches Python)
  const cardX = 2.5;
  const cardW = 8.3;
  const cardH = 0.8;
  const circleSize = 0.5;
  let y = 1.5;

  for (let i = 0; i < points.length; i++) {
    const pt = points[i];

    // Card background
    addCard(slide, cardX, y, cardW, cardH, theme);

    // Number circle
    addIconBadge(
      slide,
      cardX + 0.2,
      y + 0.15,
      circleSize,
      theme.primary,
      String(pt.number ?? i + 1),
    );

    // Title
    slide.addText(pt.title || "", {
      x: cardX + 0.9,
      y: y + 0.1,
      w: 7.0,
      h: 0.35,
      fontSize: 17,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      valign: "middle",
    });

    // Description
    if (pt.description) {
      slide.addText(pt.description, {
        x: cardX + 0.9,
        y: y + 0.45,
        w: 7.0,
        h: 0.3,
        fontSize: 13,
        fontFace: FONT,
        color: theme.body,
        lineSpacingMultiple: 1.3,
        valign: "top",
      });
    }

    y += 0.95;
  }
}
