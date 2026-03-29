"use client";

import { useState } from "react";

interface WebSearchResult {
  url: string;
  title: string;
  content: string;
}

interface SlideWebResearch {
  slide_id: string;
  type: string;
  topic: string;
  results: WebSearchResult[];
}

interface WebSearchViewerProps {
  webResearch: Record<string, SlideWebResearch>;
}

const TYPE_LABELS: Record<string, string> = {
  cover: "표지",
  table_of_contents: "목차",
  hero: "히어로",
  quote: "인용",
  icon_grid: "아이콘 그리드",
  key_points: "핵심 포인트",
  three_column: "3열",
  comparison: "비교",
  process_flow: "프로세스",
  timeline: "타임라인",
  data_visualization: "데이터 시각화",
  risk_analysis: "리스크 분석",
  action_plan: "실행 계획",
  summary: "요약",
  closing: "마무리",
};

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

export default function WebSearchViewer({ webResearch }: WebSearchViewerProps) {
  const slideIds = Object.keys(webResearch).sort();
  const [activeSlide, setActiveSlide] = useState<string | null>(slideIds[0] || null);

  const totalResults = Object.values(webResearch).reduce((sum, s) => sum + s.results.length, 0);

  if (slideIds.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <div className="text-center">
          <svg
            className="w-12 h-12 mx-auto mb-3 opacity-30"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <p className="text-sm">웹 리서치 결과가 없습니다.</p>
          <p className="text-xs mt-1 text-gray-300">
            TAVILY_API_KEY가 설정되지 않았거나 검색 대상 슬라이드가 없습니다.
          </p>
        </div>
      </div>
    );
  }

  const activeResearch = activeSlide ? webResearch[activeSlide] : null;

  return (
    <div className="flex h-full">
      {/* Left: Slide list */}
      <div className="w-[200px] border-r border-blue-200 flex flex-col bg-white/80">
        <div className="px-3 py-2 text-xs text-gray-400 font-medium uppercase tracking-wider border-b border-blue-200">
          웹 리서치
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {slideIds.map((id) => {
            const research = webResearch[id];
            const num = id.replace("slide_", "");
            const label = TYPE_LABELS[research.type] || research.type;
            return (
              <button
                key={id}
                onClick={() => setActiveSlide(id)}
                className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
                  activeSlide === id
                    ? "bg-blue-100 text-blue-600"
                    : "text-gray-500 hover:text-gray-700 hover:bg-blue-50"
                }`}
              >
                <span className="w-5 h-5 flex-shrink-0 rounded flex items-center justify-center text-[10px] bg-indigo-100 text-indigo-500">
                  {research.results.length}
                </span>
                <div className="truncate">
                  <span className="text-gray-400">{num}.</span> {label}
                </div>
              </button>
            );
          })}
        </div>
        <div className="px-3 py-2 border-t border-blue-200 text-[10px] text-gray-400">
          {slideIds.length}개 슬라이드 / {totalResults}개 소스
        </div>
      </div>

      {/* Right: Results */}
      <div className="flex-1 flex flex-col">
        {activeResearch && (
          <div className="px-4 py-1.5 border-b border-blue-200 text-xs text-gray-500 bg-blue-50/50 flex items-center justify-between">
            <span>
              {activeSlide} &mdash; {activeResearch.topic}
            </span>
            <span className="text-gray-400">
              {activeResearch.results.length}개 검색 결과
            </span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          {activeResearch ? (
            <div className="max-w-[800px] mx-auto space-y-3">
              {activeResearch.results.map((result, i) => (
                <a
                  key={i}
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-4 rounded-lg border border-blue-200 bg-white hover:border-blue-400 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-500 flex items-center justify-center text-xs font-medium">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-700 group-hover:text-blue-600 transition-colors truncate">
                        {result.title || "Untitled"}
                      </h3>
                      <p className="mt-1 text-xs text-gray-400 truncate">
                        {getDomain(result.url)}
                      </p>
                      {result.content && (
                        <p className="mt-2 text-xs text-gray-500 leading-relaxed line-clamp-3">
                          {result.content}
                        </p>
                      )}
                    </div>
                    <svg
                      className="flex-shrink-0 w-4 h-4 text-gray-300 group-hover:text-blue-400 transition-colors mt-0.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                    </svg>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              슬라이드를 선택하세요
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
