/**
 * PptxGenJS Theme & Shared Helpers
 * Design system tokens and reusable slide-building utilities.
 */

// ── Slide Dimensions (16:9 widescreen, standard PowerPoint) ──
export const SLIDE_W = 13.333;
export const SLIDE_H = 7.5;

// ── Layout Grid ──
export const MARGIN = 0.7;
export const CONTENT_W = SLIDE_W - MARGIN * 2; // ~11.93
export const TITLE_Y = 0.4;
export const BODY_Y = 1.6;
export const BODY_H = SLIDE_H - BODY_Y - 0.5; // ~5.4

export const FONT = "Malgun Gothic";

// ── Types ──
export interface PptxTheme {
  primary: string;
  accent: string;
  background: string;
  heading: string;
  body: string;
  card: string;
  cardBorder: string;
  red: string;
  yellow: string;
  green: string;
}

export interface SlideData {
  slide_id: string;
  type: string;
  content: Record<string, any>;
}

// ── Theme Builder ──
export function buildTheme(spec: Record<string, any>): PptxTheme {
  const t = spec?.ppt_state?.presentation?.meta?.theme || {};
  return {
    primary: (t.primary_color || "#6366F1").replace("#", ""),
    accent: (t.accent_color || "#818CF8").replace("#", ""),
    background: (t.background || "#F5F7FA").replace("#", ""),
    heading: (t.text_color || "#1A202C").replace("#", ""),
    body: "64748B",
    card: "FFFFFF",
    cardBorder: "E2E8F0",
    red: "E53E3E",
    yellow: "F59E0B",
    green: "38A169",
  };
}

// ── Shared Helpers ──

export function addTitle(
  slide: any,
  title: string,
  theme: PptxTheme,
  opts: {
    x?: number;
    y?: number;
    w?: number;
    h?: number;
    fontSize?: number;
    align?: "left" | "center" | "right";
    color?: string;
    bold?: boolean;
  } = {},
) {
  slide.addText(title || "", {
    x: opts.x ?? MARGIN,
    y: opts.y ?? TITLE_Y,
    w: opts.w ?? CONTENT_W,
    h: opts.h ?? 0.7,
    fontSize: opts.fontSize ?? 28,
    fontFace: FONT,
    color: opts.color ?? theme.heading,
    bold: opts.bold ?? true,
    align: opts.align ?? "left",
    valign: "middle",
  });
}

export function addSubtitle(
  slide: any,
  text: string,
  theme: PptxTheme,
  opts: {
    x?: number;
    y?: number;
    w?: number;
    h?: number;
    fontSize?: number;
    align?: "left" | "center" | "right";
  } = {},
) {
  if (!text) return;
  slide.addText(text, {
    x: opts.x ?? MARGIN,
    y: opts.y ?? 1.15,
    w: opts.w ?? CONTENT_W,
    h: opts.h ?? 0.4,
    fontSize: opts.fontSize ?? 14,
    fontFace: FONT,
    color: theme.body,
    lineSpacingMultiple: 1.3,
    align: opts.align ?? "left",
    valign: "top",
  });
}

export function addAccentBar(
  slide: any,
  theme: PptxTheme,
  opts: { x?: number; y?: number; w?: number } = {},
) {
  slide.addShape("rect", {
    x: opts.x ?? MARGIN,
    y: opts.y ?? 1.05,
    w: opts.w ?? 0.6,
    h: 0.05,
    fill: { color: theme.primary },
    line: { width: 0 },
  });
}

export function addCard(
  slide: any,
  x: number,
  y: number,
  w: number,
  h: number,
  theme: PptxTheme,
) {
  slide.addShape("roundRect", {
    x,
    y,
    w,
    h,
    fill: { color: theme.card },
    shadow: {
      type: "outer",
      blur: 4,
      offset: 1.5,
      angle: 270,
      color: "000000",
      opacity: 0.06,
    },
    rectRadius: 0.15,
    line: { color: theme.cardBorder, width: 0.5 },
  });
}

export function addIconBadge(
  slide: any,
  x: number,
  y: number,
  size: number,
  color: string,
  emoji: string,
) {
  slide.addShape("ellipse", {
    x,
    y,
    w: size,
    h: size,
    fill: { color },
    line: { width: 0 },
  });
  slide.addText(emoji || "●", {
    x,
    y,
    w: size,
    h: size,
    fontSize: Math.round(size * 24),
    fontFace: "Segoe UI Emoji",
    color: "FFFFFF",
    align: "center",
    valign: "middle",
  });
}

export function addSlideNumber(
  slide: any,
  num: number,
  total: number,
  theme: PptxTheme,
) {
  slide.addText(`${num} / ${total}`, {
    x: SLIDE_W - 1.5,
    y: SLIDE_H - 0.4,
    w: 1,
    h: 0.3,
    fontSize: 9,
    fontFace: FONT,
    color: theme.body,
    align: "right",
  });
}
