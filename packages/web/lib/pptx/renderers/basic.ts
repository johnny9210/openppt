/**
 * Basic slide renderers: Cover, Hero, Quote, Closing.
 * Ported from Python pptx_exporter with PptxGenJS API.
 */
import type PptxGenJS from "pptxgenjs";
import {
  SLIDE_W,
  SLIDE_H,
  MARGIN,
  CONTENT_W,
  FONT,
  addTitle,
  addSubtitle,
  addAccentBar,
  addCard,
  addIconBadge,
  type PptxTheme,
  type SlideData,
} from "../theme";

// ── Cover Slide ──────────────────────────────────────────────────────────────

export function renderCover(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const title = c.title || "";
  const subtitle = c.subtitle || "";
  const presenter = c.presenter || "";
  const date = c.date || "";

  // Right-side gradient panel (right 40%)
  const panelX = SLIDE_W * 0.6;
  const panelW = SLIDE_W * 0.4;
  slide.addShape("rect", {
    x: panelX,
    y: 0,
    w: panelW,
    h: SLIDE_H,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  // Secondary accent strip inside the panel
  slide.addShape("rect", {
    x: panelX,
    y: 0,
    w: 0.15,
    h: SLIDE_H,
    fill: { color: theme.accent },
    line: { width: 0 },
  });

  // Decorative left vertical accent bar
  slide.addShape("rect", {
    x: 0,
    y: 1.6,
    w: 0.15,
    h: 4.2,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  // Title — large, left-aligned
  const titleSize = title.length > 30 ? 32 : 36;
  slide.addText(title, {
    x: 1.0,
    y: 2.0,
    w: SLIDE_W * 0.55 - 1.0,
    h: 2.0,
    fontSize: titleSize,
    fontFace: FONT,
    color: theme.heading,
    bold: true,
    align: "left",
    valign: "middle",
    lineSpacingMultiple: 1.1,
  });

  // Accent bar under title
  addAccentBar(slide, theme, { x: 1.0, y: 4.0, w: 0.6 });

  // Subtitle
  if (subtitle) {
    slide.addText(subtitle, {
      x: 1.0,
      y: 4.3,
      w: SLIDE_W * 0.55 - 1.0,
      h: 0.8,
      fontSize: 16,
      fontFace: FONT,
      color: theme.body,
      align: "left",
      valign: "top",
      lineSpacingMultiple: 1.3,
    });
  }

  // Presenter + Date (bottom left)
  const parts = [presenter, date].filter(Boolean);
  if (parts.length > 0) {
    slide.addText(parts.join("  |  "), {
      x: 1.0,
      y: 6.2,
      w: SLIDE_W * 0.55 - 1.0,
      h: 0.4,
      fontSize: 11,
      fontFace: FONT,
      color: theme.body,
      align: "left",
      valign: "middle",
    });
  }
}

// ── Hero Slide ───────────────────────────────────────────────────────────────

export function renderHero(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const title = c.title || "";
  const subtitle = c.subtitle || "";

  // Decorative large circle (accent at 10% opacity) — behind text
  const circleSize = 5.0;
  slide.addShape("ellipse", {
    x: (SLIDE_W - circleSize) / 2,
    y: (SLIDE_H - circleSize) / 2 - 0.3,
    w: circleSize,
    h: circleSize,
    fill: { color: theme.accent, transparency: 90 },
    line: { width: 0 },
  });

  // Title — ultra-large, centered
  slide.addText(title, {
    x: 1.5,
    y: 2.0,
    w: SLIDE_W - 3.0,
    h: 2.0,
    fontSize: 44,
    fontFace: FONT,
    color: theme.heading,
    bold: true,
    align: "center",
    valign: "middle",
    lineSpacingMultiple: 1.1,
  });

  // Subtitle — below title
  if (subtitle) {
    slide.addText(subtitle, {
      x: 2.0,
      y: 4.2,
      w: SLIDE_W - 4.0,
      h: 1.0,
      fontSize: 18,
      fontFace: FONT,
      color: theme.body,
      align: "center",
      valign: "top",
      lineSpacingMultiple: 1.3,
    });
  }
}

// ── Quote Slide ──────────────────────────────────────────────────────────────

export function renderQuote(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const quote = c.quote || "";
  const attribution = c.attribution || "";

  // Large decorative opening quotation mark (accent, 15% opacity)
  slide.addText("\u275D", {
    x: 1.5,
    y: 0.5,
    w: 2.0,
    h: 2.0,
    fontSize: 80,
    fontFace: FONT,
    color: theme.accent,
    transparency: 85,
    align: "left",
    valign: "top",
  });

  // Vertical accent bar centered above quote
  const barW = 0.05;
  const barH = 0.6;
  slide.addShape("rect", {
    x: (SLIDE_W - barW) / 2,
    y: 1.5,
    w: barW,
    h: barH,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  // Quote text — centered, italic
  slide.addText(quote, {
    x: 2.0,
    y: 2.5,
    w: SLIDE_W - 4.0,
    h: 2.0,
    fontSize: 20,
    fontFace: FONT,
    color: theme.heading,
    bold: true,
    italic: true,
    align: "center",
    valign: "middle",
    lineSpacingMultiple: 1.4,
  });

  // Attribution
  if (attribution) {
    slide.addText(`\u2014 ${attribution}`, {
      x: 2.0,
      y: 4.8,
      w: SLIDE_W - 4.0,
      h: 0.4,
      fontSize: 14,
      fontFace: FONT,
      color: theme.body,
      align: "center",
      valign: "top",
    });
  }
}

// ── Closing Slide ────────────────────────────────────────────────────────────

export function renderClosing(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const title = c.title || "Thank You";
  const message = c.message || "";
  const resources: Array<{
    icon?: string;
    emoji?: string;
    label?: string;
    description?: string;
  }> = c.resources || [];

  // Top decorative accent bar (centered)
  const topBarW = 1.0;
  slide.addShape("rect", {
    x: (SLIDE_W - topBarW) / 2,
    y: 1.1,
    w: topBarW,
    h: 0.05,
    fill: { color: theme.primary },
    line: { width: 0 },
  });

  // Title — large, centered
  slide.addText(title, {
    x: 1.5,
    y: 1.5,
    w: SLIDE_W - 3.0,
    h: 1.0,
    fontSize: 36,
    fontFace: FONT,
    color: theme.heading,
    bold: true,
    align: "center",
    valign: "middle",
  });

  // Message
  if (message) {
    slide.addText(message, {
      x: 2.5,
      y: 2.8,
      w: SLIDE_W - 5.0,
      h: 1.0,
      fontSize: 16,
      fontFace: FONT,
      color: theme.body,
      align: "center",
      valign: "top",
      lineSpacingMultiple: 1.3,
    });
  }

  // Resource cards at bottom
  if (resources.length > 0) {
    const n = resources.length;
    const gap = 0.25;
    const cardW = Math.min(2.0, (10.0 - (n - 1) * gap) / n);
    const totalW = n * cardW + (n - 1) * gap;
    const startX = (SLIDE_W - totalW) / 2;
    const cardY = 4.2;
    const cardH = 1.5;

    for (let i = 0; i < n; i++) {
      const res = resources[i];
      const x = startX + i * (cardW + gap);

      // Card background
      addCard(slide, x, cardY, cardW, cardH, theme);

      // Icon / emoji
      const icon = res.icon || res.emoji || "";
      if (icon) {
        slide.addText(icon, {
          x,
          y: cardY + 0.15,
          w: cardW,
          h: 0.45,
          fontSize: 24,
          fontFace: "Segoe UI Emoji",
          color: theme.heading,
          align: "center",
          valign: "middle",
        });
      }

      // Label
      if (res.label) {
        slide.addText(res.label, {
          x: x + 0.1,
          y: cardY + 0.65,
          w: cardW - 0.2,
          h: 0.35,
          fontSize: 13,
          fontFace: FONT,
          color: theme.heading,
          bold: true,
          align: "center",
          valign: "middle",
        });
      }

      // Description
      if (res.description) {
        slide.addText(res.description, {
          x: x + 0.1,
          y: cardY + 1.0,
          w: cardW - 0.2,
          h: 0.4,
          fontSize: 10,
          fontFace: FONT,
          color: theme.body,
          align: "center",
          valign: "top",
        });
      }
    }
  }

  // Bottom decorative accent bar
  const bottomBarW = 2.0;
  slide.addShape("rect", {
    x: (SLIDE_W - bottomBarW) / 2,
    y: 6.5,
    w: bottomBarW,
    h: 0.04,
    fill: { color: theme.accent },
    line: { width: 0 },
  });
}
