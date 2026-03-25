"use client";

import { useState, useRef } from "react";
import ChatInput from "@/components/chat/ChatInput";
import ProgressBar from "@/components/chat/ProgressBar";
import SlidePreview, { captureAllSlides } from "@/components/preview/SlidePreview";
import type { SlidePreviewHandle } from "@/components/preview/SlidePreview";
import CodeViewer from "@/components/code/CodeViewer";
import { useStore } from "@/lib/store";
import { downloadPptxWithImages, downloadPptx } from "@/lib/api";

export default function EditorPage() {
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");
  const [isExporting, setIsExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState("");
  const previewRef = useRef<SlidePreviewHandle>(null);
  const { reactCode, slideCodes, slideSpec, isGenerating, progressSteps, validationResult, sessionId } = useStore();

  const slideCount = Object.keys(slideCodes).length;
  const canExport = !!sessionId && !!reactCode && !isGenerating;

  const handleDownloadPptx = async () => {
    if (!sessionId || isExporting) return;
    setIsExporting(true);
    try {
      const iframe = previewRef.current?.getIframe();
      const total = previewRef.current?.getSlideCount() || 0;

      if (iframe && total > 0) {
        // Capture slides from Preview
        setExportStatus(`슬라이드 캡처 준비 중...`);
        const images = await captureAllSlides(iframe, total, (current, t) => {
          setExportStatus(`슬라이드 캡처 중... (${current + 1}/${t})`);
        });
        const validImages = images.filter((img) => img.length > 0);
        console.log(`[export] Captured ${validImages.length}/${total} slides`);

        if (validImages.length > 0) {
          setExportStatus("PPTX 생성 중...");
          await downloadPptxWithImages(sessionId, validImages);
        } else {
          // Fallback to text-based export
          console.warn("[export] No valid captures, falling back to text-based export");
          setExportStatus("텍스트 기반 내보내기...");
          await downloadPptx(sessionId);
        }
      } else {
        // Fallback
        await downloadPptx(sessionId);
      }
    } catch (err) {
      console.error("PPTX export failed:", err);
      alert(`다운로드 실패: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsExporting(false);
      setExportStatus("");
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-blue-200 bg-white/70 backdrop-blur-sm">
        <h1 className="text-lg font-semibold text-gray-700">PPT Code Generator</h1>
        <div className="flex items-center gap-4">
          {slideCount > 0 && (
            <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-500">
              {slideCount}개 슬라이드
            </span>
          )}
          {validationResult?.status && (
            <span
              className={`text-xs px-2 py-1 rounded ${
                validationResult.status === "pass"
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-600"
              }`}
            >
              {validationResult.layer}: {validationResult.status}
            </span>
          )}
          {canExport && (
            <button
              onClick={handleDownloadPptx}
              disabled={isExporting}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-500 hover:bg-blue-400 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isExporting ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {exportStatus || "내보내는 중..."}
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  PPTX 다운로드
                </>
              )}
            </button>
          )}
        </div>
      </header>

      {/* Progress */}
      {isGenerating && <ProgressBar steps={progressSteps} />}

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat + Input */}
        <div className="w-[400px] flex flex-col border-r border-blue-200 bg-white/50">
          <div className="flex-1 overflow-y-auto p-4">
            {/* Chat history will be here */}
          </div>
          <ChatInput />
        </div>

        {/* Right: Preview/Code */}
        <div className="flex-1 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-blue-200 bg-white/70">
            <button
              onClick={() => setActiveTab("preview")}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === "preview"
                  ? "text-blue-500 border-b-2 border-blue-400"
                  : "text-gray-400 hover:text-gray-500"
              }`}
            >
              Preview
            </button>
            <button
              onClick={() => setActiveTab("code")}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === "code"
                  ? "text-blue-500 border-b-2 border-blue-400"
                  : "text-gray-400 hover:text-gray-500"
              }`}
            >
              Code
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "preview" ? (
              <SlidePreview ref={previewRef} code={reactCode} spec={slideSpec} slideCodes={slideCodes} />
            ) : (
              <CodeViewer code={reactCode} slideCodes={slideCodes} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
