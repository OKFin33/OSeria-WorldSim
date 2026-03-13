export interface RuntimeMessage {
  role: "user" | "assistant" | "system";
  content: string;
  turn_number: number;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface RuntimeWorldSummary {
  title: string;
  world_summary: string;
  tone_keywords: string[];
  confirmed_dimensions: string[];
  emergent_dimensions: string[];
  player_profile: string;
}

export interface LorebookEntry {
  id: string;
  type: string;
  name: string;
  aliases: string[];
  keywords: string[];
  description: string;
  first_seen_turn: number;
  last_updated_turn: number;
  source_turns: number[];
  status: string;
}

export interface TurnSummaryMemory {
  turn_number: number;
  user_action: string;
  assistant_text: string;
  summary: string;
  timestamp_label: string;
  location_label: string;
}

export interface WorldStats {
  protagonist_name: string;
  protagonist_gender: "male" | "female" | "unknown";
  current_timestamp: string;
  current_location: string;
  important_assets: string[];
}

export interface RuntimeSessionSnapshot {
  runtime_session_id: string;
  world_summary_card: RuntimeWorldSummary;
  display_title: string;
  boot_status: "pending" | "booting" | "ready" | "failed";
  boot_started_at: string;
  boot_completed_at: string;
  boot_error: string;
  boot_generation_count: number;
  turn_count: number;
  messages: RuntimeMessage[];
  recent_memories: TurnSummaryMemory[];
  lorebook: LorebookEntry[];
  world_stats: WorldStats;
  state_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RuntimeErrorRecord {
  stage: string;
  code: string;
  message: string;
  retryable: boolean;
  status_code: number;
  created_at: string;
  turn_number: number;
  user_action: string;
}

export interface RuntimeSessionDebugSnapshot {
  runtime_session_id: string;
  boot_status: "pending" | "booting" | "ready" | "failed";
  turn_count: number;
  last_bootstrap_error: RuntimeErrorRecord | null;
  last_turn_error: RuntimeErrorRecord | null;
  last_lorebook_error: RuntimeErrorRecord | null;
  last_lorebook_job_status: "idle" | "queued" | "running" | "ok" | "failed";
  last_lorebook_job_turn: number;
}

export interface RuntimeTurnResponse {
  assistant_message: RuntimeMessage;
  turn_count: number;
  world_stats: WorldStats;
  state_snapshot: Record<string, unknown>;
  recent_memories: TurnSummaryMemory[];
  lorebook: LorebookEntry[];
  lorebook_updates: LorebookEntry[];
  lorebook_update_stats: {
    inserted: number;
    updated: number;
    total: number;
  };
  updated_at: string;
}

export interface RuntimeWorldListItem {
  runtime_session_id: string;
  title: string;
  display_title: string;
  world_summary: string;
  tone_keywords: string[];
  turn_count: number;
  updated_at: string;
  preview: string;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}
