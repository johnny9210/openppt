import { create } from "zustand";

interface ProgressStep {
  phase: number;
  step: string;
  message: string;
  done?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SlideSpec = Record<string, any>;

interface AppState {
  // Session
  sessionId: string | null;
  isGenerating: boolean;

  // Pipeline state
  reactCode: string;
  slideSpec: SlideSpec | null;
  validationResult: { layer?: string; status?: string } | null;
  revisionCount: number;
  progressSteps: ProgressStep[];

  // Actions
  setSessionId: (id: string) => void;
  setIsGenerating: (v: boolean) => void;
  setReactCode: (code: string) => void;
  setSlideSpec: (spec: SlideSpec) => void;
  setValidationResult: (result: { layer?: string; status?: string } | null) => void;
  addProgressStep: (step: ProgressStep) => void;
  resetProgress: () => void;
  reset: () => void;
}

export const useStore = create<AppState>()((set) => ({
  sessionId: null,
  isGenerating: false,
  reactCode: "",
  slideSpec: null,
  validationResult: null,
  revisionCount: 0,
  progressSteps: [],

  setSessionId: (id) => set({ sessionId: id }),
  setIsGenerating: (v) => set({ isGenerating: v }),
  setReactCode: (code) => set({ reactCode: code }),
  setSlideSpec: (spec) => set({ slideSpec: spec }),
  setValidationResult: (result) => set({ validationResult: result }),
  addProgressStep: (step) =>
    set((state) => ({ progressSteps: [...state.progressSteps, step] })),
  resetProgress: () => set({ progressSteps: [], isGenerating: false }),
  reset: () =>
    set({
      sessionId: null,
      isGenerating: false,
      reactCode: "",
      slideSpec: null,
      validationResult: null,
      revisionCount: 0,
      progressSteps: [],
    }),
}));
