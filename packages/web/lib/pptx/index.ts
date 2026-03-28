/**
 * Client-side PPTX generator using PptxGenJS.
 *
 * Two rendering modes:
 *   1. JSON Layout (primary): Uses LLM-transpiled layout JSON from pipeline
 *   2. Fixed Renderers (fallback): Uses type-based template renderers
 */
import PptxGenJS from "pptxgenjs";
import {
  buildTheme,
  addSlideNumber,
  SLIDE_W,
  SLIDE_H,
  FONT,
  type PptxTheme,
  type SlideData,
} from "./theme";
import {
  renderCover,
  renderHero,
  renderQuote,
  renderClosing,
} from "./renderers/basic";
import {
  renderToc,
  renderKeyPoints,
  renderIconGrid,
  renderThreeColumn,
  renderSummary,
} from "./renderers/cards";
import {
  renderComparison,
  renderProcessFlow,
  renderTimeline,
  renderActionPlan,
} from "./renderers/structured";
import { renderDataViz, renderRiskAnalysis } from "./renderers/data";

type SlideRenderer = (
  pptx: PptxGenJS,
  slide: any,
  data: SlideData,
  theme: PptxTheme,
) => void;

const FALLBACK_RENDERERS: Record<string, SlideRenderer> = {
  cover: renderCover,
  table_of_contents: renderToc,
  hero: renderHero,
  quote: renderQuote,
  icon_grid: renderIconGrid,
  key_points: renderKeyPoints,
  three_column: renderThreeColumn,
  comparison: renderComparison,
  process_flow: renderProcessFlow,
  timeline: renderTimeline,
  data_visualization: renderDataViz,
  risk_analysis: renderRiskAnalysis,
  action_plan: renderActionPlan,
  summary: renderSummary,
  closing: renderClosing,
};

// ── JSON Layout Renderer ──────────────────────────────

interface PptxElement {
  type: "shape" | "text" | "chart";
  // Common
  x: number;
  y: number;
  w: number;
  h: number;
  // Shape
  shape?: string;
  fill?: string;
  border?: string;
  borderWidth?: number;
  radius?: number;
  shadow?: boolean;
  // Text
  text?: string;
  fontSize?: number;
  bold?: boolean;
  italic?: boolean;
  color?: string;
  align?: "left" | "center" | "right";
  valign?: "top" | "middle" | "bottom";
  lineSpacing?: number;
  fontFace?: string;
  // Chart
  chartType?: string;
  data?: { name: string; labels: string[]; values: number[] }[];
  colors?: string[];
}

interface LayoutJSON {
  elements: PptxElement[];
}

function renderFromJSON(
  pptx: PptxGenJS,
  slide: any,
  layout: LayoutJSON,
): void {
  for (const el of layout.elements) {
    switch (el.type) {
      case "shape":
        slide.addShape(el.shape || "rect", {
          x: el.x,
          y: el.y,
          w: el.w,
          h: el.h,
          fill: el.fill ? { color: el.fill } : undefined,
          line: el.border
            ? { color: el.border, width: el.borderWidth ?? 0.5 }
            : { width: 0 },
          rectRadius: el.radius,
          shadow: el.shadow
            ? {
                type: "outer",
                blur: 4,
                offset: 1.5,
                angle: 270,
                color: "000000",
                opacity: 0.06,
              }
            : undefined,
        });
        break;

      case "text":
        slide.addText(el.text || "", {
          x: el.x,
          y: el.y,
          w: el.w,
          h: el.h,
          fontSize: el.fontSize ?? 12,
          fontFace: el.fontFace || FONT,
          color: el.color || "1A202C",
          bold: el.bold ?? false,
          italic: el.italic ?? false,
          align: el.align ?? "left",
          valign: el.valign ?? "top",
          lineSpacingMultiple: el.lineSpacing,
        });
        break;

      case "chart": {
        const chartMap: Record<string, string> = {
          bar: "bar",
          pie: "pie",
          line: "line",
          doughnut: "doughnut",
        };
        const chartType = chartMap[el.chartType || "bar"] || "bar";
        if (el.data && el.data.length > 0) {
          slide.addChart(chartType as any, el.data, {
            x: el.x,
            y: el.y,
            w: el.w,
            h: el.h,
            showValue: chartType === "bar",
            showPercent: chartType === "pie" || chartType === "doughnut",
            chartColors: el.colors,
          });
        }
        break;
      }
    }
  }
}

// ── Main Export Function ──────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PptxLayoutMap = Record<string, { layout: Record<string, any> | null }>;

export async function generatePptx(
  spec: Record<string, any>,
  pptxLayouts?: PptxLayoutMap,
): Promise<void> {
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: "WIDE", width: SLIDE_W, height: SLIDE_H });
  pptx.layout = "WIDE";

  const theme = buildTheme(spec);
  const slides: SlideData[] =
    spec?.ppt_state?.presentation?.slides || [];
  const total = slides.length;

  for (let i = 0; i < slides.length; i++) {
    const data = slides[i];
    const pptxSlide = pptx.addSlide();
    pptxSlide.background = { color: theme.background };

    // Try JSON layout first (LLM-transpiled from React code)
    const layoutData = pptxLayouts?.[data.slide_id];
    if (layoutData?.layout?.elements) {
      renderFromJSON(pptx, pptxSlide, layoutData.layout as LayoutJSON);
    } else {
      // Fallback to fixed type-based renderer
      const renderer = FALLBACK_RENDERERS[data.type];
      if (renderer) {
        renderer(pptx, pptxSlide, data, theme);
      } else {
        pptxSlide.addText(data.content?.title || data.type, {
          x: 1,
          y: 3,
          w: 11,
          h: 1.5,
          fontSize: 28,
          fontFace: "Arial",
          color: theme.heading,
          bold: true,
          align: "center",
        });
      }
    }

    if (data.type !== "cover") {
      addSlideNumber(pptxSlide, i + 1, total, theme);
    }
  }

  const rawTitle =
    spec?.ppt_state?.presentation?.meta?.title || "presentation";
  const fileName =
    rawTitle
      .replace(/[^\w가-힣\s-]/g, "")
      .trim()
      .slice(0, 50) || "presentation";
  await pptx.writeFile({ fileName: `${fileName}.pptx` });
}
