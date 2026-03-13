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

export interface WorldSoftSignals {
  notable_imagery: string[];
  unstable_hypotheses: string[];
}

export interface PlayerSoftSignals {
  notable_phrasing: string[];
  subtext_hypotheses: string[];
  style_notes: string;
}

export interface WorldDossier {
  world_premise: string;
  tension_guess: string;
  scene_anchor: string;
  open_threads: string[];
  soft_signals: WorldSoftSignals;
}

export interface PlayerDossier {
  fantasy_vector: string;
  emotional_seed: string;
  taste_bias: string;
  language_register: string;
  user_no_go_zones: string[];
  soft_signals: PlayerSoftSignals;
}

export interface ChangeLog {
  newly_confirmed: string[];
  newly_rejected: string[];
  needs_follow_up: string[];
}

export interface TwinDossier {
  routing_snapshot: RoutingSnapshot;
  world_dossier: WorldDossier;
  player_dossier: PlayerDossier;
  change_log: ChangeLog;
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

export interface CompileOutput {
  confirmed_dimensions: string[];
  emergent_dimensions: string[];
  excluded_dimensions: string[];
  narrative_briefing: string;
  player_profile: string;
}

export interface FrozenCompilePackage {
  compile_output: CompileOutput;
  forge_context: Record<string, unknown>;
  assembler_context: Record<string, unknown>;
}

export interface LlmObservation {
  call_name: string;
  payload_chars: number;
  elapsed_ms: number;
  retry_count: number;
  fallback_used: boolean;
  status: "ok" | "error";
  error?: string;
}

export interface DebugEventPayload extends Record<string, unknown> {
  event?: string;
  call_name?: string;
  elapsed_ms?: number;
  fallback_used?: boolean;
  llm_observations?: LlmObservation[];
}

export interface DebugSessionPayload {
  session_id: string;
  schema_version: string;
  phase: BackendPhase;
  turn: number;
  transaction_status: string;
  dossier_update_status: DossierUpdateStatus;
  follow_up_signal: "" | "mirror_rejected";
  last_updated_turn: number;
  messages: Array<{ role: string; content: string }>;
  twin_dossier: TwinDossier;
  compile_output: CompileOutput | null;
  frozen_compile_package: FrozenCompilePackage | null;
  debug_events: DebugEventPayload[];
}

export type ReplayFrontstage =
  | { kind: "start"; response: StartInterviewResponse }
  | { kind: "step"; response: InterviewStepResponse }
  | { kind: "generate"; response: GenerateResponse };

export interface ReplayBackstage {
  phase: BackendPhase;
  turn: number;
  twin_dossier: TwinDossier;
  compile_output: CompileOutput | null;
  frozen_compile_package: FrozenCompilePackage | null;
  messages: Array<{ role: string; content: string }>;
  debug_event: DebugEventPayload | null;
}

export interface ReplaySnapshot {
  key: string;
  label: string;
  ui_phase: "q1" | "interviewing" | "mirror" | "landing" | "complete";
  frontstage: ReplayFrontstage;
  backstage: ReplayBackstage;
}

export interface ReplayBundle {
  id: string;
  name: string;
  source_session_id: string;
  captured_at: string;
  snapshots: ReplaySnapshot[];
}

export interface RuntimeSessionCreateResponse {
  runtime_session_id: string;
  turn_count: number;
  boot_status: "pending" | "ready" | "failed";
  intro_message: {
    role: string;
    content: string;
    turn_number: number;
    created_at: string;
    meta: Record<string, unknown>;
  } | null;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}

export interface ApiErrorResponse {
  error: ApiErrorPayload;
}
