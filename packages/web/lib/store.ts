import { create } from "zustand";

interface ProgressStep {
  phase: number;
  step: string;
  message: string;
  done?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SlideSpec = Record<string, any>;

interface SlideCode {
  slide_id: string;
  type: string;
  code: string;
}

interface SlideDesign {
  slide_id: string;
  type: string;
  has_image: boolean;
  image_b64: string | null;
}

interface AppState {
  // Session
  sessionId: string | null;
  isGenerating: boolean;

  // Pipeline state
  reactCode: string;
  slideCodes: Record<string, SlideCode>;
  slideDesigns: Record<string, SlideDesign>;
  slideSpec: SlideSpec | null;
  validationResult: { layer?: string; status?: string } | null;
  progressSteps: ProgressStep[];

  // Actions
  setSessionId: (id: string) => void;
  setIsGenerating: (v: boolean) => void;
  setReactCode: (code: string) => void;
  setSlideCode: (slide: SlideCode) => void;
  setSlideDesign: (design: SlideDesign) => void;
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
  slideCodes: {},
  slideDesigns: {},
  slideSpec: null,
  validationResult: null,
  progressSteps: [],

  setSessionId: (id) => set({ sessionId: id }),
  setIsGenerating: (v) => set({ isGenerating: v }),
  setReactCode: (code) => set({ reactCode: code }),
  setSlideCode: (slide) =>
    set((state) => ({
      slideCodes: { ...state.slideCodes, [slide.slide_id]: slide },
    })),
  setSlideDesign: (design) =>
    set((state) => ({
      slideDesigns: { ...state.slideDesigns, [design.slide_id]: design },
    })),
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
      slideCodes: {},
      slideDesigns: {},
      slideSpec: null,
      validationResult: null,
      progressSteps: [],
    }),
}));
