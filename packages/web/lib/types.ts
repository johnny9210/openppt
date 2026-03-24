export interface SlideSpec {
  ppt_state: {
    session_id: string;
    mode: "create" | "edit";
    target_slide_id: string | null;
    revision_count: number;
    presentation: {
      meta: {
        title: string;
        theme: {
          primary_color: string;
          accent_color: string;
          background: string;
          text_color: string;
        };
        total_slides: number;
        language: string;
      };
      slides: Slide[];
    };
  };
}

export interface Slide {
  slide_id: string;
  index: number;
  type: string;
  state: string;
  content: Record<string, unknown>;
  slots: Record<string, string>;
}

export interface ValidationResult {
  layer: "json_schema" | "ast" | "runtime" | "semantic";
  status: "pass" | "fail" | "aborted";
  errors?: Array<{ type: string; message: string }>;
  total?: number;
  passed?: number;
  missing_slots?: string[];
  fix_prompt?: string | null;
}
