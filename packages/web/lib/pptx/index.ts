/**
 * Client-side PPTX generator using PptxGenJS.
 * Generates editable PowerPoint files directly from slide spec data.
 */
import PptxGenJS from "pptxgenjs";
import {
  buildTheme,
  addSlideNumber,
  SLIDE_W,
  SLIDE_H,
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

const RENDERERS: Record<string, SlideRenderer> = {
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

export async function generatePptx(
  spec: Record<string, any>,
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

    const renderer = RENDERERS[data.type];
    if (renderer) {
      renderer(pptx, pptxSlide, data, theme);
    } else {
      // Fallback: just render title
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
