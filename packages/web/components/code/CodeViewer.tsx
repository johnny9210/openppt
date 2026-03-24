"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface SlideCode {
  slide_id: string;
  type: string;
  code: string;
}

interface CodeViewerProps {
  code: string;
  slideCodes: Record<string, SlideCode>;
}

export default function CodeViewer({ code, slideCodes }: CodeViewerProps) {
  const slideIds = Object.keys(slideCodes).sort();
  const [activeSlide, setActiveSlide] = useState<string | null>(null);

  if (!code && slideIds.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>생성된 코드가 여기에 표시됩니다.</p>
      </div>
    );
  }

  const displayCode = activeSlide
    ? slideCodes[activeSlide]?.code || ""
    : code;

  return (
    <div className="flex flex-col h-full">
      {/* Slide tabs */}
      {slideIds.length > 0 && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-800 overflow-x-auto bg-gray-900/50">
          <button
            onClick={() => setActiveSlide(null)}
            className={`px-3 py-1 text-xs rounded-md whitespace-nowrap transition-colors ${
              activeSlide === null
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            전체 (조립)
          </button>
          {slideIds.map((id) => {
            const slide = slideCodes[id];
            return (
              <button
                key={id}
                onClick={() => setActiveSlide(id)}
                className={`px-3 py-1 text-xs rounded-md whitespace-nowrap transition-colors ${
                  activeSlide === id
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                }`}
              >
                {id.replace("slide_", "#")} {slide.type}
              </button>
            );
          })}
        </div>
      )}

      {/* Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          defaultLanguage="javascript"
          value={displayCode}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 20,
            padding: { top: 16 },
            scrollBeyondLastLine: false,
            wordWrap: "on",
          }}
        />
      </div>
    </div>
  );
}
