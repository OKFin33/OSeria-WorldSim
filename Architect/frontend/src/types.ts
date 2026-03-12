export type BackendPhase = "interviewing" | "mirror" | "landing" | "complete";
export type UiPhase =
  | "idle"
  | "q1"
  | "interviewing"
  | "mirror"
  | "landing"
  | "generating"
  | "complete";

export type CompleteViewMode = "success" | "generate_failure" | "fatal_error";
export type DossierUpdateStatus = "updated" | "conservative_update" | "update_skipped" | "hard_failed";
export type BubbleKind = "answer" | "advance";

export interface RoutingSnapshot {
  confirmed: string[];
  exploring: string[];
  excluded: string[];
  untouched: string[];
}

export interface BubbleCandidate {
  text: string;
  kind: BubbleKind;
}

export interface InterviewTurnPayload {
  turn: number;
  question: string;
  bubble_candidates: BubbleCandidate[];
  routing_snapshot: RoutingSnapshot;
  dossier_update_status: DossierUpdateStatus;
  follow_up_signal: "" | "mirror_rejected";
}

export interface InterviewStepResponse {
  phase: BackendPhase;
  message: string | null;
  raw_payload: InterviewTurnPayload | null;
}

export interface StartInterviewResponse {
  session_id: string;
  phase: BackendPhase;
  message: string;
  raw_payload: null;
}

export interface Blueprint {
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
  blueprint: Blueprint;
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
