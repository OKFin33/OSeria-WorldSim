export type BackendPhase = "interviewing" | "mirror" | "landing" | "complete";
export type UiPhase =
  | "idle"
  | "q1"
  | "interviewing"
  | "mirror"
  | "landing"
  | "generating"
  | "complete";

export interface RoutingSnapshot {
  confirmed: string[];
  exploring: string[];
  excluded: string[];
  untouched: string[];
}

export interface InterviewArtifacts {
  confirmed_dimensions: string[];
  emergent_dimensions: string[];
  excluded_dimensions: string[];
  narrative_briefing: string;
  player_profile: string;
}

export interface InterviewStepResponse {
  phase: BackendPhase;
  message: string | null;
  artifacts: InterviewArtifacts | null;
  raw_payload: {
    turn: number;
    question: string;
    suggested_tags: string[];
    routing_snapshot: RoutingSnapshot;
    vibe_flavor: string;
  } | null;
}

export interface StartInterviewResponse {
  session_id: string;
  phase: BackendPhase;
  message: string;
  raw_payload: null;
}

export interface BlueprintSummary {
  title: string;
  world_summary: string;
  protagonist_hook: string;
  core_tension: string;
  tone_keywords: string[];
  player_profile: string;
  confirmed_dimensions: string[];
  emergent_dimensions: string[];
  forged_modules: Array<{
    dimension: string;
    pack_id: string | null;
  }>;
}

export interface GenerateResponse {
  blueprint: BlueprintSummary;
  system_prompt: string;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}

export interface ApiErrorResponse {
  error: ApiErrorPayload;
}

