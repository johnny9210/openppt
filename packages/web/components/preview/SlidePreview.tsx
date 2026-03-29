"use client";

import { useEffect, useRef, useState, useMemo, useImperativeHandle, forwardRef } from "react";
import { useStore, type BriefStyle } from "@/lib/store";

interface SlideCode {
  slide_id: string;
  type: string;
  code: string;
}

interface SlidePreviewProps {
  code: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  spec?: Record<string, any> | null;
  slideCodes?: Record<string, SlideCode>;
}

export interface SlidePreviewHandle {
  getIframe: () => HTMLIFrameElement | null;
  getSlideCount: () => number;
}

/**
 * SlidePreview - Renders generated HTML presentation in a sandboxed iframe.
 *
 * Supports progressive preview: as individual slides complete during generation,
 * they are assembled into a partial HTML document and rendered immediately.
 * When the final assembled code arrives, it replaces the progressive preview.
 */

const TYPE_LABELS: Record<string, string> = {
  cover: "표지",
  table_of_contents: "목차",
  key_points: "핵심 포인트",
  data_visualization: "데이터 시각화",
  risk_analysis: "리스크 분석",
  action_plan: "실행 계획",
};

/**
 * Build a progressive HTML document from individual slide codes.
 * Replicates the backend code_assembly template structure.
 */
function buildProgressiveHTML(
  slideCodes: Record<string, SlideCode>,
  theme?: BriefStyle | null,
): string {
  const primary = theme?.primary_color || "#6366F1";
  const accent = theme?.accent_color || "#818CF8";
  const slideBg = theme?.background || "#F5F7FA";
  const heading = theme?.text_color || "#1A202C";

  const sortedIds = Object.keys(slideCodes).sort();

  let allStyles = "";
  let allContent = "";

  sortedIds.forEach((id, i) => {
    const slide = slideCodes[id];
    const code = slide.code;

    // Extract <style> blocks
    const styleMatches = [...code.matchAll(/<style>([\s\S]*?)<\/style>/g)];
    const styles = styleMatches.map((m) => m[0]).join("\n");
    let html = code.replace(/<style>[\s\S]*?<\/style>\s*/g, "").trim();

    allStyles += `  <!-- ${id} (${slide.type}) -->\n  ${styles}\n`;

    // First slide gets 'active' class
    if (i === 0 && !html.includes("active")) {
      html = html.replace(
        'class="slide-container',
        'class="slide-container active',
      );
    }
    allContent += `    <!-- ${id} (${slide.type}) -->\n    ${html}\n`;
  });

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"><\/script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            primary: '${primary}',
            accent: '${accent}',
            heading: '${heading}',
            body: '#64748B',
            card: '#FFFFFF',
            'card-border': '#E2E8F0',
            'slide-bg': '${slideBg}',
            danger: '#E53E3E',
            warning: '#F59E0B',
            success: '#38A169',
          },
          boxShadow: {
            card: '0 2px 8px rgba(0,0,0,0.06)',
            'card-hover': '0 8px 24px rgba(0,0,0,0.12)',
          }
        }
      }
    };
  <\/script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Noto Sans KR', sans-serif;
      background-color: #E8ECF1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .slide-container {
      width: 1280px;
      height: 720px;
      flex-direction: column;
      background-color: #ffffff;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    #presentation > .slide-container {
      display: none;
    }
    #presentation > .slide-container.active {
      display: flex;
    }
  </style>
${allStyles}
</head>
<body>
  <div id="presentation">
${allContent}
  </div>

  <script>
    var current = 0;
    var slides = document.querySelectorAll('.slide-container');
    var total = slides.length;

    function goTo(i) {
      if (total === 0) return;
      slides[current].classList.remove('active');
      current = Math.max(0, Math.min(total - 1, i));
      slides[current].classList.add('active');
      try { window.parent.postMessage({ type: 'slideChange', index: current }, '*'); } catch(e) {}
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowLeft') goTo(current - 1);
      if (e.key === 'ArrowRight') goTo(current + 1);
    });

    window.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'goToSlide') goTo(e.data.index);
    });

    if (slides.length > 0) slides[0].classList.add('active');
  <\/script>
</body>
</html>`;
}

/**
 * Capture all slides as PNG images from the iframe.
 * Navigates to each slide, waits for render, captures via html2canvas.
 */
export async function captureAllSlides(
  iframeEl: HTMLIFrameElement,
  totalSlides: number,
  onProgress?: (current: number, total: number) => void,
): Promise<string[]> {
  const images: string[] = [];

  // First check if html2canvas is available by doing a test capture
  const testResult = await new Promise<string>((resolve) => {
    const timeout = setTimeout(() => resolve(""), 5000);
    const handler = (e: MessageEvent) => {
      if (e.data?.type === "captureResult" && e.data.index === -1) {
        window.removeEventListener("message", handler);
        clearTimeout(timeout);
        resolve(e.data.dataUrl as string);
      }
    };
    window.addEventListener("message", handler);
    iframeEl.contentWindow?.postMessage({ type: "captureSlide", index: -1 }, "*");
  });

  if (!testResult) {
    console.warn("[captureAllSlides] html2canvas not available in iframe");
    return [];
  }

  for (let i = 0; i < totalSlides; i++) {
    onProgress?.(i, totalSlides);

    // Navigate to slide
    iframeEl.contentWindow?.postMessage({ type: "goToSlide", index: i }, "*");

    // Wait for slide transition + render
    await new Promise((r) => setTimeout(r, 500));

    // Request capture
    const dataUrl = await new Promise<string>((resolve) => {
      const timeout = setTimeout(() => {
        console.warn(`[captureAllSlides] Slide ${i} capture timeout`);
        resolve("");
      }, 15000);

      const handler = (e: MessageEvent) => {
        if (e.data?.type === "captureResult" && e.data.index === i) {
          window.removeEventListener("message", handler);
          clearTimeout(timeout);
          resolve(e.data.dataUrl as string);
        }
      };
      window.addEventListener("message", handler);
      iframeEl.contentWindow?.postMessage({ type: "captureSlide", index: i }, "*");
    });

    // Extract base64 from data URL (remove "data:image/png;base64," prefix)
    const b64 = dataUrl.replace(/^data:image\/png;base64,/, "");
    images.push(b64);
  }

  return images;
}

const SlidePreview = forwardRef<SlidePreviewHandle, SlidePreviewProps>(function SlidePreview({ code, spec, slideCodes }, ref) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeSlide, setActiveSlide] = useState<number>(0);
  const [previewSize, setPreviewSize] = useState<{ w: number; h: number }>({ w: 960, h: 540 });

  const briefStyle = useStore((s) => s.briefStyle);
  const slideIds = slideCodes ? Object.keys(slideCodes).sort() : [];

  // Build progressive HTML when slides are arriving but final code is not yet ready
  const progressiveHTML = useMemo(() => {
    if (code || !slideCodes || Object.keys(slideCodes).length === 0) return null;
    return buildProgressiveHTML(slideCodes, briefStyle);
  }, [code, slideCodes, briefStyle]);

  // The HTML to render: final code takes priority, otherwise progressive
  const htmlToRender = code || progressiveHTML;

  useImperativeHandle(ref, () => ({
    getIframe: () => iframeRef.current,
    getSlideCount: () => slideIds.length,
  }));

  // Load HTML into iframe
  useEffect(() => {
    if (!htmlToRender || !iframeRef.current) return;

    setIsLoading(true);

    const blob = new Blob([htmlToRender], { type: "text/html" });
    const url = URL.createObjectURL(blob);

    const iframe = iframeRef.current;

    const handleLoad = () => {
      setIsLoading(false);
    };

    iframe.addEventListener("load", handleLoad);
    iframe.src = url;

    return () => {
      iframe.removeEventListener("load", handleLoad);
      URL.revokeObjectURL(url);
    };
  }, [htmlToRender]);

  // Listen for slide change messages from iframe
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data?.type === "slideChange") {
        setActiveSlide(e.data.index);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  // Fit 16:9 box within container
  useEffect(() => {
    const el = previewContainerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width: cw, height: ch } = entry.contentRect;
      let w = Math.min(cw, 960);
      let h = w * 9 / 16;
      if (h > ch) {
        h = ch;
        w = h * 16 / 9;
      }
      setPreviewSize({ w: Math.round(w), h: Math.round(h) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const goToSlide = (index: number) => {
    setActiveSlide(index);
    iframeRef.current?.contentWindow?.postMessage(
      { type: "goToSlide", index },
      "*"
    );
  };

  if (!htmlToRender) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p>코드를 생성하면 여기에 프리뷰가 표시됩니다.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Slide list panel */}
      {slideIds.length > 0 && (
        <div className="w-[200px] border-r border-blue-200 flex flex-col bg-white/80">
          <div className="px-3 py-2 text-xs text-gray-400 font-medium uppercase tracking-wider border-b border-blue-200">
            슬라이드{!code && <span className="ml-1 text-blue-400">({slideIds.length}장 완성)</span>}
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {slideIds.map((id, i) => {
              const slide = slideCodes![id];
              const num = id.replace("slide_", "");
              const label = TYPE_LABELS[slide.type] || slide.type;
              return (
                <button
                  key={id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("slide_id", id);
                    e.dataTransfer.setData("slide_label", `${num}. ${label}`);
                    e.dataTransfer.effectAllowed = "copy";
                  }}
                  onClick={() => goToSlide(i)}
                  className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors cursor-grab active:cursor-grabbing ${
                    activeSlide === i
                      ? "bg-blue-100 text-blue-600"
                      : "text-gray-500 hover:text-gray-700 hover:bg-blue-50"
                  }`}
                >
                  <span className="w-5 h-5 flex-shrink-0 rounded bg-blue-100 flex items-center justify-center text-[10px] text-blue-400">
                    {i + 1}
                  </span>
                  <div className="truncate">
                    <span className="text-gray-400">{num}.</span> {label}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Right: Preview */}
      <div ref={previewContainerRef} className="flex-1 flex items-center justify-center bg-blue-50 p-4 min-h-0">
        <div
          className="relative rounded-xl overflow-hidden shadow-lg border border-blue-200"
          style={{ width: previewSize.w, height: previewSize.h }}
        >
          {isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/90 text-gray-500 gap-3">
              <div className="w-8 h-8 border-2 border-blue-200 border-t-sky-500 rounded-full animate-spin" />
              <p className="text-sm">프리뷰 로딩 중...</p>
            </div>
          )}
          <iframe
            ref={iframeRef}
            sandbox="allow-scripts allow-same-origin"
            className="border-0 origin-top-left"
            style={{
              width: 1280,
              height: 720,
              transform: `scale(${previewSize.w / 1280})`,
            }}
            title="Slide Preview"
          />
        </div>
      </div>
    </div>
  );
});

export default SlidePreview;
