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

const TYPE_LABELS: Record<string, string> = {
  cover: "표지",
  table_of_contents: "목차",
  key_points: "핵심 포인트",
  data_visualization: "데이터 시각화",
  risk_analysis: "리스크 분석",
  action_plan: "실행 계획",
};

export default function CodeViewer({ code, slideCodes }: CodeViewerProps) {
  const slideIds = Object.keys(slideCodes).sort();
  const [activeFile, setActiveFile] = useState<string>("assembled");

  if (!code && slideIds.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>생성된 코드가 여기에 표시됩니다.</p>
      </div>
    );
  }

  const displayCode =
    activeFile === "assembled"
      ? code
      : slideCodes[activeFile]?.code || "";

  const displayName =
    activeFile === "assembled"
      ? "Presentation.jsx"
      : `${activeFile}.jsx`;

  return (
    <div className="flex h-full">
      {/* Left: File list panel */}
      <div className="w-[200px] border-r border-gray-800 flex flex-col bg-gray-950">
        <div className="px-3 py-2 text-xs text-gray-500 font-medium uppercase tracking-wider border-b border-gray-800">
          파일
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {/* Assembled file */}
          <button
            onClick={() => setActiveFile("assembled")}
            className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
              activeFile === "assembled"
                ? "bg-blue-600/20 text-blue-300"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            }`}
          >
            <svg className="w-4 h-4 flex-shrink-0 opacity-50" viewBox="0 0 16 16" fill="currentColor">
              <path d="M3 1h7l3 3v9a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1zm6.5 0L13 4.5V4h-3V1h-.5z" />
            </svg>
            <span className="truncate">Presentation.jsx</span>
          </button>

          {/* Divider */}
          {slideIds.length > 0 && (
            <div className="mx-3 my-2 border-t border-gray-800" />
          )}

          {/* Per-slide files */}
          {slideIds.map((id) => {
            const slide = slideCodes[id];
            const num = id.replace("slide_", "");
            const label = TYPE_LABELS[slide.type] || slide.type;
            return (
              <button
                key={id}
                onClick={() => setActiveFile(id)}
                className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
                  activeFile === id
                    ? "bg-blue-600/20 text-blue-300"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                }`}
              >
                <svg className="w-4 h-4 flex-shrink-0 opacity-50" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M3 1h7l3 3v9a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1zm6.5 0L13 4.5V4h-3V1h-.5z" />
                </svg>
                <div className="truncate">
                  <span className="text-gray-500">{num}.</span>{" "}
                  {label}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right: Code editor */}
      <div className="flex-1 flex flex-col">
        {/* File name bar */}
        <div className="px-4 py-1.5 border-b border-gray-800 text-xs text-gray-500 bg-gray-900/50">
          {displayName}
        </div>
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
    </div>
  );
}
