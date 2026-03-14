"""Pydantic models for Runtime vNext."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RuntimeStartRequest(BaseModel):
    system_prompt: str
    title: str
    world_summary: str
    protagonist_name: str
    protagonist_gender: str
    protagonist_identity_brief: str
    tone_keywords: list[str] = Field(default_factory=list)
    confirmed_dimensions: list[str] = Field(default_factory=list)
    emergent_dimensions: list[str] = Field(default_factory=list)
    player_profile: str | None = None

    @field_validator("system_prompt", "title", "world_summary", "protagonist_name", "protagonist_identity_brief")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @field_validator("protagonist_gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        lowered = value.strip().lower()
        if lowered in {"male", "man", "m", "男"}:
            return "male"
        if lowered in {"female", "woman", "f", "女"}:
            return "female"
        if lowered in {"unknown", "?", "other"}:
            return "unknown"
        raise ValueError("must be male, female, or unknown")


class RuntimeMessageModel(BaseModel):
    role: str
    content: str
    turn_number: int
    created_at: str
    meta: dict[str, Any] = Field(default_factory=dict)


class RuntimeWorldSummaryModel(BaseModel):
    title: str
    world_summary: str
    tone_keywords: list[str] = Field(default_factory=list)
    confirmed_dimensions: list[str] = Field(default_factory=list)
    emergent_dimensions: list[str] = Field(default_factory=list)
    player_profile: str = ""


class LorebookEntryModel(BaseModel):
    id: str
    type: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    description: str
    first_seen_turn: int
    last_updated_turn: int
    source_turns: list[int] = Field(default_factory=list)
    status: str = ""
    stage_id: str = ""
    layer: int = 1
    parent_id: str = ""
    activation_keys: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)


class WorldStatsModel(BaseModel):
    protagonist_name: str = ""
    protagonist_gender: str = "unknown"
    protagonist_identity_brief: str = ""
    current_timestamp: str = ""
    current_location: str = ""
    active_stage_id: str = ""
    active_stage_source: str = ""
    supporting_stage_ids: list[str] = Field(default_factory=list)
    important_assets: list[str] = Field(default_factory=list)


class DisplayTitleUpdateRequest(BaseModel):
    display_title: str = ""


class RuntimeErrorRecordModel(BaseModel):
    stage: str
    code: str
    message: str
    retryable: bool
    status_code: int
    created_at: str
    turn_number: int = 0
    user_action: str = ""


class LorebookUpdateStatsModel(BaseModel):
    inserted: int = 0
    updated: int = 0
    conflicts: int = 0
    total: int = 0


class RuntimeSessionCreateResponse(BaseModel):
    runtime_session_id: str
    intro_message: RuntimeMessageModel | None = None
    world_summary_card: RuntimeWorldSummaryModel
    display_title: str = ""
    boot_status: str = "pending"
    turn_count: int


class RuntimeTurnRequest(BaseModel):
    runtime_session_id: str
    user_action: str


class RuntimeTurnResponse(BaseModel):
    assistant_message: RuntimeMessageModel
    turn_count: int
    world_stats: WorldStatsModel
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    action_resolution: dict[str, Any] = Field(default_factory=dict)
    thread_updates: dict[str, list[str]] = Field(default_factory=dict)
    scene_progress: dict[str, Any] = Field(default_factory=dict)
    recent_memories: list[dict[str, Any]] = Field(default_factory=list)
    lorebook: list[LorebookEntryModel] = Field(default_factory=list)
    lorebook_updates: list[LorebookEntryModel] = Field(default_factory=list)
    lorebook_update_stats: LorebookUpdateStatsModel = Field(default_factory=LorebookUpdateStatsModel)
    updated_at: str


class RuntimeSessionSnapshotResponse(BaseModel):
    runtime_session_id: str
    world_summary_card: RuntimeWorldSummaryModel
    display_title: str = ""
    boot_status: str = "pending"
    boot_started_at: str = ""
    boot_completed_at: str = ""
    boot_error: str = ""
    boot_generation_count: int = 0
    turn_count: int
    messages: list[RuntimeMessageModel] = Field(default_factory=list)
    recent_memories: list[dict[str, Any]] = Field(default_factory=list)
    lorebook: list[LorebookEntryModel] = Field(default_factory=list)
    world_stats: WorldStatsModel
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class RuntimeWorldListItemModel(BaseModel):
    runtime_session_id: str
    title: str
    display_title: str = ""
    world_summary: str
    tone_keywords: list[str] = Field(default_factory=list)
    turn_count: int
    updated_at: str
    preview: str = ""


class RuntimeSessionDebugResponse(BaseModel):
    runtime_session_id: str
    boot_status: str
    turn_count: int
    last_bootstrap_error: RuntimeErrorRecordModel | None = None
    last_turn_error: RuntimeErrorRecordModel | None = None
    last_lorebook_error: RuntimeErrorRecordModel | None = None
    last_lorebook_job_status: str = "idle"
    last_lorebook_job_turn: int = 0
    last_lorebook_merge_stats: dict[str, int] = Field(default_factory=dict)
    last_lorebook_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    last_lorebook_started_window: dict[str, int] = Field(default_factory=dict)
    last_lorebook_completed_window: dict[str, int] = Field(default_factory=dict)
    pending_lorebook_windows_count: int = 0
    dropped_windows_count: int = 0
    active_stage_id: str = ""
    active_stage_source: str = ""
    supporting_stage_ids: list[str] = Field(default_factory=list)
    last_scene_lock_warning: dict[str, Any] = Field(default_factory=dict)
    scene_lock_warning_count: int = 0


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorPayload


class HealthResponse(BaseModel):
    status: str = "ok"
