"use client";

import dynamic from "next/dynamic";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface CodeViewerProps {
  code: string;
}

export default function CodeViewer({ code }: CodeViewerProps) {
  if (!code) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>생성된 코드가 여기에 표시됩니다.</p>
      </div>
    );
  }

  return (
    <Editor
      height="100%"
      defaultLanguage="javascript"
      value={code}
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
  );
}
