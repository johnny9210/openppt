"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { streamGenerate } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function ChatInput() {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<string>("대기 중");
  const [eventCount, setEventCount] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    isGenerating,
    setIsGenerating,
    setSessionId,
    setReactCode,
    setSlideSpec,
    setValidationResult,
    addProgressStep,
    resetProgress,
  } = useStore();

  const handleSubmit = async () => {
    if (!input.trim() || isGenerating) return;

    const request = input.trim();
    setInput("");
    setStatus("API 호출 시작...");
    setEventCount(0);
    resetProgress();
    setIsGenerating(true);

    try {
      let count = 0;
      let receivedCode = false;
      let receivedSpec = false;
      for await (const event of streamGenerate(request)) {
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
          case "code":
            setReactCode(data.react_code as string);
            receivedCode = true;
            setStatus(`코드 수신 완료 (${(data.react_code as string)?.length || 0} chars)`);
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
    <div className="p-4 border-t border-gray-800">
      {/* Debug status */}
      <div className="mb-2 p-2 bg-gray-800 rounded text-xs text-gray-300 font-mono">
        상태: {status} | 이벤트: {eventCount}개
      </div>
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="PPT를 설명해주세요... (예: 2024년 4분기 성과 보고서)"
          rows={3}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 placeholder-gray-500"
          disabled={isGenerating}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isGenerating}
          className="px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors"
        >
          {isGenerating ? "..." : "생성"}
        </button>
      </div>
    </div>
  );
}
