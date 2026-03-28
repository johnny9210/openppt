/**
 * PptxGenJS renderers for data-oriented slide types:
 *   - data_visualization  (bar / pie / doughnut / line charts)
 *   - risk_analysis        (severity-coded risk cards)
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

// ── Helpers ──────────────────────────────────────────────────────

const SEVERITY_COLOR = (theme: PptxTheme) =>
  ({
    high: theme.red,
    medium: theme.yellow,
    low: theme.green,
  }) as Record<string, string>;

/** Map chart_type string to PptxGenJS CHART_NAME literal */
const CHART_MAP: Record<string, string> = {
  bar: "bar",
  pie: "pie",
  doughnut: "doughnut",
  line: "line",
};

// ── data_visualization ───────────────────────────────────────────

export function renderDataViz(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const title: string = c.title ?? "";
  const description: string | undefined = c.description;
  const chartType: string = (c.chart_type ?? "bar").toLowerCase().trim();
  const rawData: Array<{ label: string; value: number; color?: string }> =
    c.data ?? [];
  const insight: string | undefined = c.insight;

  // ── Title + accent bar ──
  addTitle(slide, title, theme, { align: "center" });
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.3,
    y: 1.05,
    w: 0.6,
  });

  if (description) {
    addSubtitle(slide, description, theme, { align: "center" });
  }

  // ── Prepare data points (skip non-numeric) ──
  const labels: string[] = [];
  const values: number[] = [];

  for (const item of rawData) {
    const label = String(item.label ?? "");
    const num = Number(item.value);
    if (Number.isFinite(num)) {
      labels.push(label);
      values.push(num);
    }
  }

  // ── Chart area positioning ──
  const chartX = (SLIDE_W - 8) / 2; // centred 8" wide
  const chartY = description ? 1.9 : 1.7;
  const chartW = 8;
  const chartH = insight ? 3.6 : 4.2;

  if (labels.length > 0 && values.length > 0) {
    const chartData = [
      {
        name: title || "Values",
        labels,
        values,
      },
    ];

    // Collect per-item colors or fall back to theme palette
    const defaultPalette = [
      theme.primary,
      theme.accent,
      theme.green,
      theme.yellow,
      theme.red,
    ];

    const itemColors = rawData
      .filter((_d, i) => i < labels.length)
      .map((d, i) =>
        d.color
          ? String(d.color).replace("#", "")
          : defaultPalette[i % defaultPalette.length],
      );

    const resolvedType = CHART_MAP[chartType] ?? "bar";

    if (resolvedType === "pie" || resolvedType === "doughnut") {
      // ── Pie / Doughnut ──
      slide.addChart(resolvedType, chartData, {
        x: chartX,
        y: chartY,
        w: chartW,
        h: chartH,
        showPercent: true,
        showTitle: false,
        showLegend: true,
        legendPos: "r",
        legendFontSize: 9,
        legendColor: theme.body,
        chartColors: itemColors,
      });
    } else if (resolvedType === "line") {
      // ── Line chart ──
      slide.addChart("line", chartData, {
        x: chartX,
        y: chartY,
        w: chartW,
        h: chartH,
        showValue: false,
        showTitle: false,
        showLegend: false,
        lineSize: 2.5,
        lineSmooth: true,
        chartColors: [theme.primary],
        catAxisLabelFontSize: 9,
        catAxisLabelColor: theme.body,
        valAxisLabelFontSize: 9,
        valAxisLabelColor: theme.body,
        catAxisOrientation: "minMax",
        valAxisOrientation: "minMax",
      });
    } else {
      // ── Bar (default) ── vertical columns
      slide.addChart("bar", chartData, {
        x: chartX,
        y: chartY,
        w: chartW,
        h: chartH,
        barDir: "col",
        showValue: true,
        valueFontSize: 10,
        showTitle: false,
        showLegend: false,
        chartColors: itemColors,
        catAxisLabelFontSize: 9,
        catAxisLabelColor: theme.body,
        valAxisLabelFontSize: 9,
        valAxisLabelColor: theme.body,
        catAxisOrientation: "minMax",
        valAxisOrientation: "minMax",
      });
    }
  } else {
    // ── No data fallback — placeholder card ──
    const placeholderW = 6;
    const placeholderH = 2.5;
    const px = (SLIDE_W - placeholderW) / 2;
    const py = (SLIDE_H - placeholderH) / 2;

    addCard(slide, px, py, placeholderW, placeholderH, theme);

    slide.addText("\uB370\uC774\uD130 \uC5C6\uC74C", {
      x: px,
      y: py,
      w: placeholderW,
      h: placeholderH,
      fontSize: 18,
      fontFace: FONT,
      color: theme.body,
      align: "center",
      valign: "middle",
    });
  }

  // ── Insight text ──
  if (insight) {
    slide.addText(insight, {
      x: MARGIN,
      y: chartY + chartH + 0.2,
      w: CONTENT_W,
      h: 0.5,
      fontSize: 14,
      fontFace: FONT,
      color: theme.primary,
      bold: true,
      align: "center",
      valign: "middle",
    });
  }
}

// ── risk_analysis ────────────────────────────────────────────────

export function renderRiskAnalysis(
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
): void {
  const c = data.content || {};
  const title: string = c.title ?? "";
  const risks: Array<{
    severity: "high" | "medium" | "low";
    title: string;
    description?: string;
    mitigation?: string;
  }> = (c.risks ?? []).slice(0, 5); // max 5 risks

  const sevColors = SEVERITY_COLOR(theme);

  // ── Title + accent bar ──
  addTitle(slide, title, theme, { align: "center" });
  addAccentBar(slide, theme, {
    x: SLIDE_W / 2 - 0.3,
    y: 1.05,
    w: 0.6,
  });

  if (risks.length === 0) return;

  // ── Layout constants ──
  const cardX = MARGIN + 0.3;
  const cardW = CONTENT_W - 0.6;
  const colorBarW = 0.08;
  const cardGap = 0.2;
  const padLeft = cardX + colorBarW + 0.2; // text start X
  const textW = cardW - colorBarW - 0.4;

  let curY = BODY_Y;

  for (const risk of risks) {
    const severity = (risk.severity ?? "medium").toLowerCase();
    const sevColor = sevColors[severity] ?? theme.primary;
    const riskTitle = risk.title ?? "";
    const desc = risk.description ?? "";
    const mitigation = risk.mitigation ?? "";

    // Calculate card height dynamically
    let cardH = 0.55; // base: padding top + severity/title row
    if (desc) cardH += 0.35;
    if (mitigation) cardH += 0.4;
    cardH += 0.1; // bottom padding

    // Clamp to available space
    if (curY + cardH > SLIDE_H - 0.4) break;

    // ── Card background ──
    addCard(slide, cardX, curY, cardW, cardH, theme);

    // ── Severity color bar (left edge) ──
    slide.addShape("rect", {
      x: cardX,
      y: curY,
      w: colorBarW,
      h: cardH,
      fill: { color: sevColor },
      line: { width: 0 },
      rectRadius: 0,
    });

    // ── Severity badge ──
    const sevLabel = severity.toUpperCase();
    slide.addText(sevLabel, {
      x: padLeft,
      y: curY + 0.1,
      w: 1.2,
      h: 0.35,
      fontSize: 11,
      fontFace: FONT,
      color: sevColor,
      bold: true,
      valign: "middle",
    });

    // ── Risk title ──
    slide.addText(riskTitle, {
      x: padLeft + 1.2,
      y: curY + 0.1,
      w: textW - 1.2,
      h: 0.35,
      fontSize: 16,
      fontFace: FONT,
      color: theme.heading,
      bold: true,
      valign: "middle",
    });

    let innerY = curY + 0.55;

    // ── Description ──
    if (desc) {
      slide.addText(desc, {
        x: padLeft,
        y: innerY,
        w: textW,
        h: 0.3,
        fontSize: 12,
        fontFace: FONT,
        color: theme.body,
        valign: "top",
      });
      innerY += 0.35;
    }

    // ── Mitigation ──
    if (mitigation) {
      slide.addText(
        [
          {
            text: "\uC644\uD654 \uBC29\uC548: ",
            options: {
              fontSize: 12,
              fontFace: FONT,
              color: theme.primary,
              bold: true,
            },
          },
          {
            text: mitigation,
            options: {
              fontSize: 12,
              fontFace: FONT,
              color: theme.body,
              bold: false,
            },
          },
        ],
        {
          x: padLeft,
          y: innerY,
          w: textW,
          h: 0.35,
          valign: "top",
        },
      );
    }

    curY += cardH + cardGap;
  }
}
