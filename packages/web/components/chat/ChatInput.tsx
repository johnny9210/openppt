"use client";

import { useState, useRef, type KeyboardEvent, type DragEvent } from "react";
import { streamGenerate, streamEdit } from "@/lib/api";
import { useStore } from "@/lib/store";

interface EditTarget {
  slideId: string;
  label: string;
}

export default function ChatInput() {
  const [input, setInput] = useState("");
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    sessionId,
    isGenerating,
    setIsGenerating,
    setSessionId,
    setReactCode,
    setSlideCode,
    setSlideDesign,
    setWebResearch,
    setSlideSpec,
    setBriefStyle,
    setTokenUsage,
    setValidationResult,
    addProgressStep,
    addChatMessage,
    resetProgress,
  } = useStore();

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const slideId = e.dataTransfer.getData("slide_id");
    const slideLabel = e.dataTransfer.getData("slide_label");
    if (slideId) {
      setEditTarget({ slideId, label: slideLabel || slideId });
      textareaRef.current?.focus();
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isGenerating) return;

    const request = input.trim();
    setInput("");
    resetProgress();
    setIsGenerating(true);

    const currentEditTarget = editTarget;
    setEditTarget(null);

    addChatMessage({
      role: "user",
      content: currentEditTarget
        ? `[${currentEditTarget.label} 편집] ${request}`
        : request,
      type: "request",
    });

    try {
      let receivedCode = false;
      let receivedSpec = false;

      const stream =
        currentEditTarget && sessionId
          ? streamEdit(sessionId, request, currentEditTarget.slideId)
          : streamGenerate(request);

      for await (const event of stream) {
        const data = event.data as Record<string, unknown>;

        switch (event.event) {
          case "session":
            setSessionId(data.session_id as string);
            break;
          case "progress":
            addProgressStep({
              phase: data.phase as number,
              step: data.step as string,
              message: data.message as string,
              done: data.done as boolean,
            });
            break;
          case "scoping": {
            // Save theme style for progressive preview
            const style = data.style as Record<string, string> | undefined;
            if (style) {
              setBriefStyle({
                primary_color: style.primary_color || "#6366F1",
                accent_color: style.accent_color || "#818CF8",
                background: style.background || "#F5F7FA",
                text_color: style.text_color || "#1A202C",
              });
            }
            // Extract web_research from research_brief.slide_plan
            const slidePlan = (data.slide_plan as Array<Record<string, unknown>>) || [];
            const researchMap: Record<string, { slide_id: string; type: string; topic: string; results: Array<{ url: string; title: string; content: string }> }> = {};
            for (const slide of slidePlan) {
              const wr = slide.web_research as Array<Record<string, string>> | undefined;
              if (wr && wr.length > 0) {
                const sid = slide.slide_id as string;
                researchMap[sid] = {
                  slide_id: sid,
                  type: slide.type as string,
                  topic: slide.topic as string,
                  results: wr.map((r) => ({
                    url: r.url || "",
                    title: r.title || "",
                    content: r.content || "",
                  })),
                };
              }
            }
            if (Object.keys(researchMap).length > 0) {
              setWebResearch(researchMap);
            }
            break;
          }
          case "design":
            setSlideDesign({
              slide_id: data.slide_id as string,
              type: data.type as string,
              has_image: data.has_image as boolean,
              image_b64: (data.image_b64 as string) || null,
            });
            break;
          case "text":
            break;
          case "slide":
            setSlideCode({
              slide_id: data.slide_id as string,
              type: data.type as string,
              code: data.code as string,
            });
            break;
          case "state":
            if (data.slide_spec) {
              setSlideSpec(data.slide_spec as Record<string, unknown>);
              receivedSpec = true;
            }
            break;
          case "code":
            setReactCode(data.react_code as string);
            receivedCode = true;
            break;
          case "validation":
            setValidationResult(data as { layer: string; status: string });
            break;
          case "token_usage":
            setTokenUsage({
              input_tokens: (data.input_tokens as number) || 0,
              output_tokens: (data.output_tokens as number) || 0,
            });
            break;
          case "complete": {
            if (!receivedCode && data.react_code) setReactCode(data.react_code as string);
            if (!receivedSpec && data.slide_spec) setSlideSpec(data.slide_spec as Record<string, unknown>);
            if (data.token_usage) {
              const tu = data.token_usage as { input_tokens: number; output_tokens: number };
              setTokenUsage({ input_tokens: tu.input_tokens || 0, output_tokens: tu.output_tokens || 0 });
            }
            // Extract web_research from complete's research_brief if not already set
            const brief = data.research_brief as Record<string, unknown> | undefined;
            if (brief) {
              const plan = (brief.slide_plan as Array<Record<string, unknown>>) || [];
              const rMap: Record<string, { slide_id: string; type: string; topic: string; results: Array<{ url: string; title: string; content: string }> }> = {};
              for (const s of plan) {
                const wr = s.web_research as Array<Record<string, string>> | undefined;
                if (wr && wr.length > 0) {
                  const sid = s.slide_id as string;
                  rMap[sid] = {
                    slide_id: sid,
                    type: s.type as string,
                    topic: s.topic as string,
                    results: wr.map((r) => ({ url: r.url || "", title: r.title || "", content: r.content || "" })),
                  };
                }
              }
              if (Object.keys(rMap).length > 0) setWebResearch(rMap);
            }
            break;
          }
          case "error":
            setReactCode("");
            setIsGenerating(false);
            break;
        }
      }
    } catch {
      // error handled by isGenerating reset
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className={`p-3 border-b transition-colors ${
        isDragOver
          ? "border-blue-400 bg-blue-50"
          : "border-blue-200"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Edit target chip */}
      {editTarget && (
        <div className="mb-2 flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
            <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
              <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10z" />
            </svg>
            {editTarget.label} 편집
            <button
              onClick={() => setEditTarget(null)}
              className="ml-1 hover:text-amber-900"
            >
              ✕
            </button>
          </span>
          <span className="text-xs text-gray-400">수정 내용을 입력하세요</span>
        </div>
      )}

      {/* Drop zone hint */}
      {isDragOver && (
        <div className="mb-2 py-3 border-2 border-dashed border-blue-300 rounded-lg text-center text-sm text-blue-400">
          여기에 드롭하여 슬라이드 편집
        </div>
      )}

      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            editTarget
              ? `${editTarget.label} 수정 요청을 입력하세요...`
              : "PPT를 설명해주세요... (예: 2024년 4분기 성과 보고서)"
          }
          rows={2}
          className="flex-1 bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-blue-400 placeholder-gray-400 text-gray-700"
          disabled={isGenerating}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isGenerating}
          className={`px-4 rounded-lg text-sm font-medium transition-colors self-end disabled:bg-gray-300 disabled:cursor-not-allowed ${
            editTarget
              ? "bg-amber-500 hover:bg-amber-400 text-white"
              : "bg-blue-500 hover:bg-blue-400 text-white"
          }`}
        >
          {isGenerating ? "..." : editTarget ? "수정" : "생성"}
        </button>
      </div>
    </div>
  );
}
