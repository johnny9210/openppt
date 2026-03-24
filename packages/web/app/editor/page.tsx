"use client";

import { useState } from "react";
import ChatInput from "@/components/chat/ChatInput";
import ProgressBar from "@/components/chat/ProgressBar";
import SlidePreview from "@/components/preview/SlidePreview";
import CodeViewer from "@/components/code/CodeViewer";
import { useStore } from "@/lib/store";

export default function EditorPage() {
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");
  const { reactCode, slideCodes, slideSpec, isGenerating, progressSteps, validationResult } = useStore();

  const slideCount = Object.keys(slideCodes).length;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-800">
        <h1 className="text-lg font-semibold text-gray-200">PPT Code Generator</h1>
        <div className="flex items-center gap-4">
          {slideCount > 0 && (
            <span className="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400">
              {slideCount}개 슬라이드
            </span>
          )}
          {validationResult?.status && (
            <span
              className={`text-xs px-2 py-1 rounded ${
                validationResult.status === "pass"
                  ? "bg-green-900 text-green-300"
                  : "bg-red-900 text-red-300"
              }`}
            >
              {validationResult.layer}: {validationResult.status}
            </span>
          )}
        </div>
      </header>

      {/* Progress */}
      {isGenerating && <ProgressBar steps={progressSteps} />}

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat + Input */}
        <div className="w-[400px] flex flex-col border-r border-gray-800">
          <div className="flex-1 overflow-y-auto p-4">
            {/* Chat history will be here */}
          </div>
          <ChatInput />
        </div>

        {/* Right: Preview/Code */}
        <div className="flex-1 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => setActiveTab("preview")}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === "preview"
                  ? "text-blue-400 border-b-2 border-blue-400"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Preview
            </button>
            <button
              onClick={() => setActiveTab("code")}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === "code"
                  ? "text-blue-400 border-b-2 border-blue-400"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Code
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "preview" ? (
              <SlidePreview code={reactCode} spec={slideSpec} slideCodes={slideCodes} />
            ) : (
              <CodeViewer code={reactCode} slideCodes={slideCodes} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
