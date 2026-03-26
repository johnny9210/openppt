"use client";

import { useEffect, useRef } from "react";
import { useStore } from "@/lib/store";

const TYPE_STYLES: Record<string, string> = {
  request: "bg-blue-500 text-white",
  progress: "bg-gray-50 text-gray-600 border border-gray-200",
  design: "bg-green-50 text-green-700 border border-green-200",
  slide: "bg-purple-50 text-purple-700 border border-purple-200",
  code: "bg-indigo-50 text-indigo-700 border border-indigo-200",
  validation: "bg-amber-50 text-amber-700 border border-amber-200",
  complete: "bg-blue-50 text-blue-700 border border-blue-200",
  error: "bg-red-50 text-red-700 border border-red-200",
};

export default function ChatHistory() {
  const { chatMessages, isGenerating } = useStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages.length]);

  if (chatMessages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-300 p-4">
        <div className="text-center">
          <svg className="w-10 h-10 mx-auto mb-2 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
          <p className="text-sm">PPT 생성 요청을 입력하세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
      {chatMessages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[90%] px-3 py-1.5 rounded-lg text-xs leading-relaxed ${
              msg.role === "user"
                ? "bg-blue-500 text-white rounded-br-sm"
                : `${TYPE_STYLES[msg.type || "progress"]} rounded-bl-sm`
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
      {isGenerating && (
        <div className="flex justify-start">
          <div className="px-3 py-1.5 rounded-lg text-xs bg-gray-50 border border-gray-200 text-gray-400 rounded-bl-sm">
            <span className="inline-block animate-pulse">처리 중...</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
