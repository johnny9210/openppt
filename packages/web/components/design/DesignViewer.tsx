"use client";

import { useState, useCallback } from "react";

interface SlideDesign {
  slide_id: string;
  type: string;
  has_image: boolean;
  image_b64: string | null;
}

interface DesignViewerProps {
  slideDesigns: Record<string, SlideDesign>;
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

function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function crc32(data: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) {
    crc ^= data[i];
    for (let j = 0; j < 8; j++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function buildZip(files: { name: string; data: Uint8Array }[]): Blob {
  const parts: Uint8Array[] = [];
  const centralParts: Uint8Array[] = [];
  let offset = 0;

  for (const file of files) {
    const nameBytes = new TextEncoder().encode(file.name);
    const crc = crc32(file.data);

    // local file header
    const local = new Uint8Array(30 + nameBytes.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(4, 20, true);
    lv.setUint16(8, 0, true);             // stored
    lv.setUint32(14, crc, true);           // crc-32
    lv.setUint32(18, file.data.length, true);
    lv.setUint32(22, file.data.length, true);
    lv.setUint16(26, nameBytes.length, true);
    local.set(nameBytes, 30);

    // central directory header
    const central = new Uint8Array(46 + nameBytes.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(10, 0, true);            // stored
    cv.setUint32(16, crc, true);           // crc-32
    cv.setUint32(20, file.data.length, true);
    cv.setUint32(24, file.data.length, true);
    cv.setUint16(28, nameBytes.length, true);
    cv.setUint32(42, offset, true);
    central.set(nameBytes, 46);

    parts.push(local, file.data);
    centralParts.push(central);
    offset += local.length + file.data.length;
  }

  const centralSize = centralParts.reduce((s, e) => s + e.length, 0);
  const eocd = new Uint8Array(22);
  const ev = new DataView(eocd.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);

  // concat all into single ArrayBuffer to avoid .buffer slice issues
  const totalSize = offset + centralSize + 22;
  const result = new Uint8Array(totalSize);
  let pos = 0;
  for (const p of [...parts, ...centralParts, eocd]) {
    result.set(p, pos);
    pos += p.length;
  }
  return new Blob([result.buffer], { type: "application/zip" });
}

export default function DesignViewer({ slideDesigns }: DesignViewerProps) {
  const slideIds = Object.keys(slideDesigns).sort();
  const [activeSlide, setActiveSlide] = useState<string | null>(
    slideIds[0] || null
  );
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectMode, setSelectMode] = useState(false);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const selectableIds = slideIds.filter((id) => slideDesigns[id].image_b64);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) =>
      prev.size === selectableIds.length ? new Set() : new Set(selectableIds)
    );
  }, [selectableIds]);

  const downloadZip = useCallback(() => {
    const files = [...selectedIds]
      .sort()
      .map((id) => {
        const d = slideDesigns[id];
        return { name: `${d.slide_id}_${d.type}.png`, data: base64ToBytes(d.image_b64!) };
      });
    if (files.length === 0) return;
    const blob = buildZip(files);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "design_images.zip";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setSelectMode(false);
    setSelectedIds(new Set());
  }, [selectedIds, slideDesigns]);

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
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.41a2.25 2.25 0 013.182 0l2.909 2.91m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
            />
          </svg>
          <p className="text-sm">Nano Banana 디자인 이미지가 여기에 표시됩니다.</p>
          <p className="text-xs mt-1 text-gray-300">
            Gemini가 생성한 슬라이드 배경 이미지
          </p>
        </div>
      </div>
    );
  }

  const activeDesign = activeSlide ? slideDesigns[activeSlide] : null;

  function downloadImage(design: SlideDesign) {
    if (!design.image_b64) return;
    const a = document.createElement("a");
    a.href = `data:image/png;base64,${design.image_b64}`;
    a.download = `${design.slide_id}_${design.type}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  return (
    <div className="flex h-full">
      {/* Left: Slide list panel */}
      <div className="w-[200px] border-r border-blue-200 flex flex-col bg-white/80">
        <div className="px-3 py-2 text-xs text-gray-400 font-medium uppercase tracking-wider border-b border-blue-200">
          디자인 이미지
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {slideIds.map((id) => {
            const design = slideDesigns[id];
            const num = id.replace("slide_", "");
            const label = TYPE_LABELS[design.type] || design.type;
            return (
              <button
                key={id}
                onClick={() => selectMode && design.image_b64 ? toggleSelect(id) : setActiveSlide(id)}
                className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
                  activeSlide === id && !selectMode
                    ? "bg-blue-100 text-blue-600"
                    : "text-gray-500 hover:text-gray-700 hover:bg-blue-50"
                }`}
              >
                {selectMode ? (
                  <span
                    className={`w-5 h-5 flex-shrink-0 rounded border flex items-center justify-center text-[10px] transition-colors ${
                      !design.image_b64
                        ? "border-gray-200 bg-gray-50 text-gray-300 cursor-not-allowed"
                        : selectedIds.has(id)
                          ? "border-blue-500 bg-blue-500 text-white"
                          : "border-gray-300 bg-white"
                    }`}
                  >
                    {selectedIds.has(id) && "✓"}
                  </span>
                ) : (
                  <span
                    className={`w-5 h-5 flex-shrink-0 rounded flex items-center justify-center text-[10px] ${
                      design.has_image
                        ? "bg-green-100 text-green-500"
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {design.has_image ? "✓" : "✗"}
                  </span>
                )}
                <div className="truncate">
                  <span className="text-gray-400">{num}.</span> {label}
                </div>
              </button>
            );
          })}
        </div>
        <div className="px-3 py-2 border-t border-blue-200 text-[10px] text-gray-400">
          {selectMode ? (
            <div className="flex items-center justify-between">
              <button onClick={toggleAll} className="text-blue-500 hover:text-blue-700">
                {selectedIds.size === selectableIds.length ? "전체 해제" : "전체 선택"}
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setSelectMode(false); setSelectedIds(new Set()); }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  취소
                </button>
                <button
                  onClick={downloadZip}
                  disabled={selectedIds.size === 0}
                  className={`px-2 py-0.5 rounded ${
                    selectedIds.size > 0
                      ? "bg-blue-500 text-white hover:bg-blue-600"
                      : "bg-gray-200 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  ZIP ({selectedIds.size})
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span>
                {slideIds.filter((id) => slideDesigns[id].has_image).length}/
                {slideIds.length} 이미지 생성됨
              </span>
              {selectableIds.length > 0 && (
                <button
                  onClick={() => { setSelectMode(true); setSelectedIds(new Set(selectableIds)); }}
                  className="text-blue-500 hover:text-blue-700"
                >
                  ZIP 저장
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Image viewer */}
      <div className="flex-1 flex flex-col">
        {/* Info bar */}
        {activeDesign && (
          <div className="px-4 py-1.5 border-b border-blue-200 text-xs text-gray-500 bg-blue-50/50 flex items-center justify-between">
            <span>
              {activeSlide}.png — {TYPE_LABELS[activeDesign.type] || activeDesign.type}
            </span>
            <div className="flex items-center gap-3">
              {activeDesign.image_b64 && (
                <span className="text-gray-400">
                  {Math.round(activeDesign.image_b64.length * 0.75 / 1024)} KB
                </span>
              )}
              {activeDesign.image_b64 && (
                <button
                  onClick={() => downloadImage(activeDesign)}
                  className="px-2 py-0.5 rounded text-[11px] bg-blue-100 text-blue-600 hover:bg-blue-200 transition-colors"
                >
                  다운로드
                </button>
              )}
            </div>
          </div>
        )}

        {/* Image display */}
        <div className="flex-1 flex items-center justify-center bg-blue-50 p-8 overflow-auto">
          {activeDesign?.image_b64 ? (
            <div className="max-w-[960px] w-full">
              <div className="relative aspect-video rounded-xl overflow-hidden shadow-lg border border-blue-200 bg-white">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`data:image/png;base64,${activeDesign.image_b64}`}
                  alt={`${activeDesign.type} design`}
                  className="w-full h-full object-contain"
                />
              </div>
              <div className="mt-3 text-center text-xs text-gray-400">
                Nano Banana (Gemini) generated design — 코드 합성의 시각 레퍼런스로 사용됨
              </div>
            </div>
          ) : activeDesign ? (
            <div className="text-center text-gray-400">
              <svg
                className="w-16 h-16 mx-auto mb-3 opacity-20"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
              <p className="text-sm">이미지 생성 실패</p>
              <p className="text-xs mt-1 text-gray-300">
                Nano Banana API가 이 슬라이드의 이미지를 생성하지 못했습니다
              </p>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">슬라이드를 선택하세요</p>
          )}
        </div>
      </div>
    </div>
  );
}
