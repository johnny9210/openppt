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

interface ChatMessage {
  id: string;
  role: "user" | "system";
  content: string;
  timestamp: number;
  type?: "request" | "progress" | "design" | "slide" | "code" | "validation" | "complete" | "error";
}

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

export interface BriefStyle {
  primary_color: string;
  accent_color: string;
  background: string;
  text_color: string;
}

interface AppState {
  // Session
  sessionId: string | null;
  isGenerating: boolean;

  // Pipeline state
  reactCode: string;
  slideCodes: Record<string, SlideCode>;
  slideDesigns: Record<string, SlideDesign>;
  webResearch: Record<string, SlideWebResearch>;
  slideSpec: SlideSpec | null;
  briefStyle: BriefStyle | null;
  tokenUsage: { input_tokens: number; output_tokens: number };
  validationResult: { layer?: string; status?: string } | null;
  progressSteps: ProgressStep[];
  chatMessages: ChatMessage[];

  // Actions
  setSessionId: (id: string) => void;
  setIsGenerating: (v: boolean) => void;
  setReactCode: (code: string) => void;
  setSlideCode: (slide: SlideCode) => void;
  setSlideDesign: (design: SlideDesign) => void;
  setWebResearch: (research: Record<string, SlideWebResearch>) => void;
  setSlideSpec: (spec: SlideSpec) => void;
  setBriefStyle: (style: BriefStyle) => void;
  setTokenUsage: (usage: { input_tokens: number; output_tokens: number }) => void;
  setValidationResult: (result: { layer?: string; status?: string } | null) => void;
  addProgressStep: (step: ProgressStep) => void;
  addChatMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  resetProgress: () => void;
}

export const useStore = create<AppState>()((set) => ({
  sessionId: null,
  isGenerating: false,
  reactCode: "",
  slideCodes: {},
  slideDesigns: {},
  webResearch: {},
  slideSpec: null,
  briefStyle: null,
  tokenUsage: { input_tokens: 0, output_tokens: 0 },
  validationResult: null,
  progressSteps: [],
  chatMessages: [],

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
  setWebResearch: (research) => set({ webResearch: research }),
  setSlideSpec: (spec) => set({ slideSpec: spec }),
  setBriefStyle: (style) => set({ briefStyle: style }),
  setTokenUsage: (usage) => set({ tokenUsage: usage }),
  setValidationResult: (result) => set({ validationResult: result }),
  addProgressStep: (step) =>
    set((state) => ({ progressSteps: [...state.progressSteps, step] })),
  addChatMessage: (msg) =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        { ...msg, id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, timestamp: Date.now() },
      ],
    })),
  resetProgress: () => set({ progressSteps: [], isGenerating: false, briefStyle: null }),
}));
