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
 * SlidePreview - Renders generated React code in a sandboxed iframe.
 * Uses @babel/standalone for browser-side JSX transpilation.
 *
 * CDN Dependencies (loaded inside iframe):
 * - React 18 UMD (React 19 removed UMD builds)
 * - Recharts 2.x UMD (Recharts 3.x has no UMD build; generated code must
 *   use Recharts 2.x API which is backwards-compatible for common charts)
 * - @babel/standalone for in-browser JSX transpilation
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

    // Wait for slide transition + React re-render
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
  const [isLoading, setIsLoading] = useState(false);
  const [activeSlide, setActiveSlide] = useState<number>(0);

  const slideIds = slideCodes ? Object.keys(slideCodes).sort() : [];

  useImperativeHandle(ref, () => ({
    getIframe: () => iframeRef.current,
    getSlideCount: () => slideIds.length,
  }));

  useEffect(() => {
    if (!code || !iframeRef.current) return;

    setIsLoading(true);

    const html = buildPreviewHTML(code, spec || getDefaultSpec());
    const blob = new Blob([html], { type: "text/html" });
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
  }, [code, spec]);

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
                  onClick={() => goToSlide(i)}
                  className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
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
      <div className="flex-1 flex items-center justify-center bg-blue-50 p-8 min-h-0 overflow-hidden">
        <div className="relative w-full max-w-[960px] max-h-full aspect-video rounded-xl overflow-hidden shadow-lg border border-blue-200">
          {isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/90 text-gray-500 gap-3">
              <div className="w-8 h-8 border-2 border-blue-200 border-t-sky-500 rounded-full animate-spin" />
              <p className="text-sm">프리뷰 로딩 중...</p>
              <p className="text-xs text-gray-400">외부 라이브러리를 불러오고 있습니다</p>
            </div>
          )}
          <iframe
            ref={iframeRef}
            sandbox="allow-scripts allow-same-origin"
            className="w-full h-full border-0"
            title="Slide Preview"
          />
        </div>
      </div>
    </div>
  );
});

export default SlidePreview;

/**
 * Strip import/export statements from generated code so it can run
 * inside the iframe where React, Recharts, etc. are global UMD variables.
 *
 * Handles:
 * - import { X, Y } from "module"      (named imports, possibly multi-line)
 * - import X from "module"              (default imports)
 * - import * as X from "module"         (namespace imports)
 * - import "side-effect"                (side-effect imports)
 * - export default function X(...)      -> function X(...)
 * - export default class X             -> class X
 * - export default (...)               -> const __Presentation__ = (...)
 * - export default X                   -> const __Presentation__ = X
 */
function stripImportsAndExports(code: string): string {
  const lines = code.split("\n");
  const result: string[] = [];
  let inMultiLineImport = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Continue skipping lines if we're inside a multi-line import
    if (inMultiLineImport) {
      // Look for the closing line: `} from "...";` or just `from "...";`
      if (/from\s+["'][^"']*["']\s*;?\s*$/.test(trimmed) || /}\s*from\s+["']/.test(trimmed)) {
        inMultiLineImport = false;
      }
      continue;
    }

    // Skip side-effect imports: import "module" or import 'module'
    if (/^\s*import\s+["'][^"']*["']\s*;?\s*$/.test(line)) {
      continue;
    }

    // Skip namespace imports: import * as X from "module"
    if (/^\s*import\s+\*\s+as\s+\w+\s+from\s+["'][^"']*["']\s*;?\s*$/.test(line)) {
      continue;
    }

    // Skip default imports: import X from "module"
    if (/^\s*import\s+\w+\s+from\s+["'][^"']*["']\s*;?\s*$/.test(line)) {
      continue;
    }

    // Skip single-line named imports: import { X, Y } from "module"
    if (/^\s*import\s+\{[^}]*\}\s+from\s+["'][^"']*["']\s*;?\s*$/.test(line)) {
      continue;
    }

    // Detect multi-line import start: import { X, Y,
    if (/^\s*import\s+\{/.test(line) && !line.includes("}")) {
      inMultiLineImport = true;
      continue;
    }

    // Skip import with both default and named: import X, { Y } from "module"
    if (/^\s*import\s+\w+\s*,\s*\{[^}]*\}\s+from\s+["'][^"']*["']\s*;?\s*$/.test(line)) {
      continue;
    }

    // Transform export default function/class -> keep the declaration
    if (/^\s*export\s+default\s+function\s/.test(line)) {
      result.push(line.replace(/export\s+default\s+/, ""));
      continue;
    }
    if (/^\s*export\s+default\s+class\s/.test(line)) {
      result.push(line.replace(/export\s+default\s+/, ""));
      continue;
    }

    // Transform export default (...) or export default identifier
    if (/^\s*export\s+default\s+/.test(line)) {
      result.push(line.replace(/export\s+default\s+/, "const __Presentation__ = "));
      continue;
    }

    // Strip named exports: export { X, Y }
    if (/^\s*export\s+\{[^}]*\}\s*;?\s*$/.test(line)) {
      continue;
    }

    // Transform export const/let/var/function/class -> keep without export
    if (/^\s*export\s+(const|let|var|function|class)\s/.test(line)) {
      result.push(line.replace(/export\s+/, ""));
      continue;
    }

    result.push(line);
  }

  return result.join("\n");
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildPreviewHTML(code: string, spec: Record<string, any>): string {
  const cleanCode = stripImportsAndExports(code);

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    #root { width: 100%; height: 100vh; }
    #error {
      color: #f87171;
      padding: 24px;
      font-size: 14px;
      white-space: pre-wrap;
      display: none;
    }
    #error.visible { display: block; }
    #error .error-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 8px;
      color: #fca5a5;
    }
    #error .error-type {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      margin-bottom: 12px;
    }
    #error .error-type.cdn { background: #7c2d12; color: #fed7aa; }
    #error .error-type.code { background: #7f1d1d; color: #fecaca; }
    #error .error-message { color: #f87171; margin-bottom: 8px; }
    #error .error-stack { color: #9ca3af; font-size: 12px; }
    #loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      color: #9ca3af;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      gap: 12px;
    }
    #loading .spinner {
      width: 32px;
      height: 32px;
      border: 2px solid #374151;
      border-top-color: #60a5fa;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div id="loading">
    <div class="spinner"></div>
    <div style="font-size: 14px;">스크립트 로딩 중...</div>
  </div>
  <div id="root"></div>
  <div id="error"></div>

  <script>
    // --- Parent ↔ Iframe Communication Bridge ---
    window.__goToSlide = null;
    window.addEventListener("message", function(e) {
      if (e.data && e.data.type === "goToSlide" && typeof e.data.index === "number") {
        if (window.__goToSlide) window.__goToSlide(e.data.index);
      }
      if (e.data && e.data.type === "captureSlide" && typeof e.data.index === "number") {
        captureCurrentSlide(e.data.index);
      }
    });

    function captureCurrentSlide(index) {
      var root = document.getElementById("root");
      if (typeof html2canvas === "undefined") {
        console.warn("[capture] html2canvas not available, index:", index);
        window.parent.postMessage({ type: "captureResult", index: index, dataUrl: "" }, "*");
        return;
      }
      if (!root) {
        window.parent.postMessage({ type: "captureResult", index: index, dataUrl: "" }, "*");
        return;
      }
      // Test capture (index -1): just confirm html2canvas is available
      if (index === -1) {
        window.parent.postMessage({ type: "captureResult", index: -1, dataUrl: "ok" }, "*");
        return;
      }
      console.log("[capture] Starting capture for slide", index, "root size:", root.offsetWidth, "x", root.offsetHeight);
      html2canvas(root, {
        scale: 2,
        useCORS: true,
        backgroundColor: null,
        width: root.offsetWidth,
        height: root.offsetHeight,
        logging: false,
      }).then(function(canvas) {
        var dataUrl = canvas.toDataURL("image/png");
        console.log("[capture] Slide", index, "captured, size:", dataUrl.length);
        window.parent.postMessage({ type: "captureResult", index: index, dataUrl: dataUrl }, "*");
      }).catch(function(err) {
        console.error("[capture] Failed for slide", index, err);
        window.parent.postMessage({ type: "captureResult", index: index, dataUrl: "" }, "*");
      });
    }

    // --- CDN Script Loader with Error Handling ---
    var __cdnErrors = [];
    var __scriptsLoaded = { react: false, reactDom: false, propTypes: false, recharts: false, babel: false, html2canvas: false };

    function showError(type, title, message, stack) {
      var el = document.getElementById("error");
      var typeClass = type === "cdn" ? "cdn" : "code";
      var typeLabel = type === "cdn" ? "CDN Error" : "Code Error";
      el.innerHTML =
        '<span class="error-type ' + typeClass + '">' + typeLabel + '</span>' +
        '<div class="error-title">' + title + '</div>' +
        '<div class="error-message">' + message + '</div>' +
        (stack ? '<div class="error-stack">' + stack + '</div>' : '');
      el.className = "visible";
      document.getElementById("root").style.display = "none";
      document.getElementById("loading").style.display = "none";
    }

    function hideLoading() {
      var el = document.getElementById("loading");
      if (el) el.style.display = "none";
    }

    function loadScript(url, name) {
      return new Promise(function(resolve, reject) {
        var script = document.createElement("script");
        script.src = url;
        script.onload = function() {
          __scriptsLoaded[name] = true;
          resolve();
        };
        script.onerror = function() {
          var err = "Failed to load " + name + " from " + url;
          __cdnErrors.push(err);
          reject(new Error(err));
        };
        document.head.appendChild(script);
      });
    }

    // Load scripts sequentially (they depend on each other)
    loadScript("https://unpkg.com/react@18/umd/react.production.min.js", "react")
      .then(function() {
        return loadScript("https://unpkg.com/react-dom@18/umd/react-dom.production.min.js", "reactDom");
      })
      .then(function() {
        // Recharts 2.x UMD requires PropTypes as a global (not bundled in React 18 production)
        return loadScript("https://unpkg.com/prop-types@15/prop-types.min.js", "propTypes");
      })
      .then(function() {
        // Recharts depends on React + PropTypes being available
        return loadScript("https://unpkg.com/recharts@2.15.0/umd/Recharts.js", "recharts");
      })
      .then(function() {
        return loadScript("https://unpkg.com/@babel/standalone/babel.min.js", "babel");
      })
      .then(function() {
        hideLoading();
        runGeneratedCode();
        // Load html2canvas separately (non-blocking, optional for slide capture)
        loadScript("https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js", "html2canvas")
          .catch(function() { console.warn("html2canvas failed to load - slide capture disabled"); });
      })
      .catch(function(err) {
        hideLoading();
        var failedScripts = Object.keys(__scriptsLoaded).filter(function(k) {
          return !__scriptsLoaded[k];
        });
        showError(
          "cdn",
          "외부 라이브러리 로딩 실패",
          err.message,
          "로딩 실패 항목: " + failedScripts.join(", ") +
          "\\n\\n네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요." +
          "\\nunpkg.com CDN에 접근할 수 없을 수 있습니다."
        );
      });

    function runGeneratedCode() {
      try {
        // Verify all required globals exist
        if (typeof React === "undefined") throw new Error("React is not loaded");
        if (typeof ReactDOM === "undefined") throw new Error("ReactDOM is not loaded");
        if (typeof Babel === "undefined") throw new Error("Babel is not loaded");

        // Recharts 2.x UMD exposes all components on the global Recharts object.
        // We destructure ALL commonly used components here so generated code
        // can reference them directly (matching typical Recharts import patterns).
        // NOTE: We intentionally use Recharts 2.x (not 3.x) because 3.x has no
        // UMD build. The API for these components is compatible between 2.x and 3.x.
        var rechartsCode = "";
        if (typeof Recharts !== "undefined") {
          rechartsCode = [
            "const {",
            "  // Layout",
            "  ResponsiveContainer,",
            "  // Cartesian Charts",
            "  BarChart, Bar, LineChart, Line, AreaChart, Area,",
            "  ComposedChart, ScatterChart, Scatter,",
            "  // Radial Charts",
            "  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid,",
            "  PolarAngleAxis, PolarRadiusAxis, RadialBarChart, RadialBar,",
            "  // Axes & Grid",
            "  XAxis, YAxis, ZAxis, CartesianGrid,",
            "  // Tooltip & Legend",
            "  Tooltip, Legend,",
            "  // Reference elements",
            "  ReferenceLine, ReferenceArea, ReferenceDot,",
            "  // Misc",
            "  Brush, Funnel, FunnelChart, Treemap,",
            "  LabelList, Label, Text",
            "} = Recharts;"
          ].join("\\n");
        }

        var userCode = rechartsCode + "\\n" +
          "const { useState, useEffect, useMemo, useCallback, useRef, Fragment } = React;\\n" +
          ${JSON.stringify(cleanCode)} + "\\n" +
          "var spec = " + ${JSON.stringify(JSON.stringify(spec))} + ";\\n" +
          "ReactDOM.createRoot(document.getElementById('root')).render(" +
          "  React.createElement(typeof __Presentation__ !== 'undefined' ? __Presentation__ : (typeof Presentation !== 'undefined' ? Presentation : function() { return React.createElement('div', {style:{padding:24,color:'#f87171'}}, 'No Presentation component found'); }), { spec: spec })" +
          ");";

        // Use Babel to transform JSX at runtime
        var transformed = Babel.transform(userCode, {
          presets: ["env", "react"],
          filename: "preview.jsx"
        }).code;

        eval(transformed);
      } catch (e) {
        var friendlyMessage = parseFriendlyError(e);
        showError(
          "code",
          "프리뷰 렌더링 오류",
          friendlyMessage,
          e.stack ? e.stack.split("\\n").slice(0, 5).join("\\n") : ""
        );
      }
    }

    function parseFriendlyError(e) {
      var msg = e.message || String(e);

      // Common error patterns with friendlier messages
      if (msg.includes("is not defined")) {
        var match = msg.match(/(\\w+) is not defined/);
        if (match) {
          return "'" + match[1] + "' 변수를 찾을 수 없습니다.\\n" +
            "이 변수가 올바르게 정의되었는지 확인해주세요.";
        }
      }
      if (msg.includes("is not a function")) {
        return msg + "\\n함수 호출을 확인해주세요.";
      }
      if (msg.includes("Unexpected token")) {
        return "구문 오류: " + msg + "\\n코드 문법을 확인해주세요.";
      }
      if (msg.includes("Cannot read properties of")) {
        return msg + "\\nnull 또는 undefined 값에 접근하고 있습니다.";
      }

      return msg;
    }
  <\/script>
</body>
</html>`;
}

function getDefaultSpec() {
  // Minimal spec for preview
  return {
    ppt_state: {
      presentation: {
        slides: [
          { slide_id: "slide_001", index: 0, type: "cover", state: "INITIAL", content: { title: "Loading...", subtitle: "", date: "", department: "" }, slots: {} },
        ],
      },
    },
  };
}
