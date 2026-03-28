"use client";

import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";

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
 * The assembled HTML already includes:
 * - Google Fonts, Tailwind CDN, FontAwesome CDN
 * - Custom Tailwind theme config
 * - All slide styles and content
 * - Navigation JavaScript (keyboard, postMessage)
 * - html2canvas for slide capture
 *
 * No Babel transpilation or React CDN loading needed.
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

  const slideIds = slideCodes ? Object.keys(slideCodes).sort() : [];

  useImperativeHandle(ref, () => ({
    getIframe: () => iframeRef.current,
    getSlideCount: () => slideIds.length,
  }));

  // Load assembled HTML directly into iframe
  useEffect(() => {
    if (!code || !iframeRef.current) return;

    setIsLoading(true);

    // The code is already a complete HTML document — load directly
    const blob = new Blob([code], { type: "text/html" });
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
  }, [code]);

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

  if (!code) {
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
            슬라이드
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
