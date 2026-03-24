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
  const [status, setStatus] = useState<string>("대기 중");
  const [eventCount, setEventCount] = useState(0);
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
    setSlideSpec,
    setValidationResult,
    addProgressStep,
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
    setStatus(editTarget ? `슬라이드 편집 시작: ${editTarget.label}` : "API 호출 시작...");
    setEventCount(0);
    resetProgress();
    setIsGenerating(true);

    const currentEditTarget = editTarget;
    setEditTarget(null);

    try {
      let count = 0;
      let receivedCode = false;
      let receivedSpec = false;

      // Choose stream based on edit target
      const stream =
        currentEditTarget && sessionId
          ? streamEdit(sessionId, request, currentEditTarget.slideId)
          : streamGenerate(request);

      for await (const event of stream) {
        count++;
        setEventCount(count);
        const data = event.data as Record<string, unknown>;
        setStatus(`이벤트 수신: ${event.event} (#${count})`);

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
          case "state":
            if (data.slide_spec) {
              setSlideSpec(data.slide_spec as Record<string, unknown>);
              receivedSpec = true;
            }
            break;
          case "slide":
            setSlideCode({
              slide_id: data.slide_id as string,
              type: data.type as string,
              code: data.code as string,
            });
            setStatus(`슬라이드 수신: ${data.slide_id}`);
            break;
          case "code":
            setReactCode(data.react_code as string);
            receivedCode = true;
            setStatus(`코드 조립 완료 (${(data.react_code as string)?.length || 0} chars)`);
            break;
          case "validation":
            setValidationResult(data as { layer: string; status: string });
            break;
          case "complete":
            if (!receivedCode && data.react_code) setReactCode(data.react_code as string);
            if (!receivedSpec && data.slide_spec) setSlideSpec(data.slide_spec as Record<string, unknown>);
            setStatus(`완료! 코드 길이: ${(data.react_code as string)?.length || 0}`);
            break;
          case "error": {
            const errorMsg =
              (data.message as string) ||
              (data.error as string) ||
              (data.detail as string) ||
              JSON.stringify(data);
            setReactCode("");
            setIsGenerating(false);
            setStatus(`에러: ${errorMsg}`);
            break;
          }
        }
      }
      setStatus(`스트림 종료. 총 ${count}개 이벤트 수신.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus(`실패: ${msg}`);
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
      className={`p-4 border-t transition-colors ${
        isDragOver
          ? "border-blue-500 bg-blue-950/30"
          : "border-gray-800"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Debug status */}
      <div className="mb-2 p-2 bg-gray-800 rounded text-xs text-gray-300 font-mono">
        상태: {status} | 이벤트: {eventCount}개
      </div>

      {/* Edit target chip */}
      {editTarget && (
        <div className="mb-2 flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-300 text-xs font-medium">
            <svg className="w-3 h-3" viewBox="0 0 16 16" fill="currentColor">
              <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10z" />
            </svg>
            {editTarget.label} 편집
            <button
              onClick={() => setEditTarget(null)}
              className="ml-1 hover:text-white"
            >
              ✕
            </button>
          </span>
          <span className="text-xs text-gray-500">수정 내용을 입력하세요</span>
        </div>
      )}

      {/* Drop zone hint */}
      {isDragOver && (
        <div className="mb-2 py-3 border-2 border-dashed border-blue-500/50 rounded-lg text-center text-sm text-blue-400">
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
          rows={3}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 placeholder-gray-500"
          disabled={isGenerating}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isGenerating}
          className={`px-4 rounded-lg text-sm font-medium transition-colors ${
            editTarget
              ? "bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed"
          }`}
        >
          {isGenerating ? "..." : editTarget ? "수정" : "생성"}
        </button>
      </div>
    </div>
  );
}
