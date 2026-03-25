"use client";

interface ProgressStep {
  phase: number;
  step: string;
  message: string;
  done?: boolean;
}

const PHASE_LABELS: Record<number, string> = {
  0: "Mode Router",
  1: "전처리",
  2: "코드 생성",
  3: "검증",
};

export default function ProgressBar({ steps }: { steps: ProgressStep[] }) {
  const latestStep = steps[steps.length - 1];
  const currentPhase = latestStep?.phase ?? 0;

  return (
    <div className="px-6 py-2 bg-white/70 border-b border-blue-200">
      {/* Phase indicators */}
      <div className="flex gap-1 mb-2">
        {[0, 1, 2, 3].map((phase) => (
          <div key={phase} className="flex-1 flex items-center gap-2">
            <div
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                phase < currentPhase
                  ? "bg-green-400"
                  : phase === currentPhase
                  ? "bg-blue-400 animate-pulse"
                  : "bg-blue-100"
              }`}
            />
            <span className="text-[10px] text-gray-400 whitespace-nowrap">
              {PHASE_LABELS[phase]}
            </span>
          </div>
        ))}
      </div>

      {/* Current step */}
      {latestStep && (
        <p className="text-xs text-gray-500">
          {latestStep.done ? "✓" : "⟳"} {latestStep.message}
        </p>
      )}
    </div>
  );
}
