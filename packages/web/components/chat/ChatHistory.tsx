"use client";

import { useEffect, useRef } from "react";
import { useStore } from "@/lib/store";

export default function ChatHistory() {
  const { chatMessages } = useStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  const userMessages = chatMessages.filter((msg) => msg.role === "user");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [userMessages.length]);

  if (userMessages.length === 0) {
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
      {userMessages.map((msg) => (
        <div key={msg.id} className="flex justify-end">
          <div className="max-w-[90%] px-3 py-1.5 rounded-lg rounded-br-sm text-xs leading-relaxed bg-blue-500 text-white">
            {msg.content}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
