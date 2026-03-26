"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { streamGenerate } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function ChatInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    isGenerating,
    setIsGenerating,
    setSessionId,
    setReactCode,
    setSlideCode,
    setSlideDesign,
    setSlideSpec,
    setValidationResult,
    addProgressStep,
    addChatMessage,
    resetProgress,
  } = useStore();

  const handleSubmit = async () => {
    if (!input.trim() || isGenerating) return;

    const request = input.trim();
    setInput("");
    resetProgress();
    setIsGenerating(true);

    addChatMessage({ role: "user", content: request, type: "request" });

    try {
      let receivedCode = false;
      let receivedSpec = false;
      for await (const event of streamGenerate(request)) {
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
          case "scoping":
            // Handled via progress done events
            break;
          case "design":
            setSlideDesign({
              slide_id: data.slide_id as string,
              type: data.type as string,
              has_image: data.has_image as boolean,
              image_b64: (data.image_b64 as string) || null,
            });
            break;
          case "text":
            // Silent — too noisy per-slide
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
          case "complete":
            if (!receivedCode && data.react_code) setReactCode(data.react_code as string);
            if (!receivedSpec && data.slide_spec) setSlideSpec(data.slide_spec as Record<string, unknown>);
            break;
          case "error":
            setReactCode("");
            setIsGenerating(false);
            break;
        }
      }
    } catch (err) {
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
    <div className="p-3 border-b border-blue-200">
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="PPT를 설명해주세요... (예: 2024년 4분기 성과 보고서)"
          rows={2}
          className="flex-1 bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-blue-400 placeholder-gray-400 text-gray-700"
          disabled={isGenerating}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isGenerating}
          className="px-4 bg-blue-500 hover:bg-blue-400 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition-colors self-end"
        >
          {isGenerating ? "..." : "생성"}
        </button>
      </div>
    </div>
  );
}
