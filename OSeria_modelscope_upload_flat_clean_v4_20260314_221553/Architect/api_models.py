"""Pydantic API models for the vNext Architect pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BackendPhase(str, Enum):
    INTERVIEWING = "interviewing"
    MIRROR = "mirror"
    LANDING = "landing"
    COMPLETE = "complete"


class BubbleCandidateModel(BaseModel):
    text: str
    kind: Literal["answer", "advance"]


class RoutingSnapshotModel(BaseModel):
    confirmed: list[str] = Field(default_factory=list)
    exploring: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    untouched: list[str] = Field(default_factory=list)


class InterviewTurnPayloadModel(BaseModel):
    turn: int
    question: str
    bubble_candidates: list[BubbleCandidateModel] = Field(default_factory=list)
    routing_snapshot: RoutingSnapshotModel
    dossier_update_status: Literal["updated", "conservative_update", "update_skipped", "hard_failed"]
    follow_up_signal: Literal["", "mirror_rejected"] = ""


class StartInterviewResponse(BaseModel):
    session_id: str
    phase: BackendPhase
    message: str
    raw_payload: None = None


class LandingPayloadModel(BaseModel):
    user_gender: Literal["男", "女", "其他"]
    avatar_gender: Literal["男", "女", "其他", "世界提供"]
    name_mode: Literal["custom", "generated"]
    custom_name: str | None = None

    @model_validator(mode="after")
    def validate_name_mode(self) -> "LandingPayloadModel":
        trimmed = (self.custom_name or "").strip()
        if self.name_mode == "custom" and not trimmed:
            raise ValueError("custom_name is required when name_mode=custom.")
        if self.name_mode == "generated":
            self.custom_name = None
        else:
            self.custom_name = trimmed
        return self


class InterviewMessageRequest(BaseModel):
    session_id: str
    message: str | None = None
    mirror_action: Literal["confirm", "reconsider"] | None = None
    landing_payload: LandingPayloadModel | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "InterviewMessageRequest":
        has_message = bool(self.message and self.message.strip())
        has_landing = self.landing_payload is not None
        if sum([has_message, self.mirror_action is not None, has_landing]) > 1:
            raise ValueError("message, mirror_action, and landing_payload are mutually exclusive.")
        if not any([has_message, self.mirror_action is not None, has_landing]):
            raise ValueError("Either message, mirror_action, or landing_payload must be provided.")
        return self


class InterviewStepResponse(BaseModel):
    phase: BackendPhase
    message: str | None = None
    raw_payload: InterviewTurnPayloadModel | None = None


class GenerateRequest(BaseModel):
    session_id: str


class ForgeModuleSummary(BaseModel):
    dimension: str
    pack_id: str | None


class BlueprintModel(BaseModel):
    title: str
    world_summary: str
    protagonist_hook: str
    core_tension: str
    protagonist_name: str
    protagonist_gender: str
    protagonist_identity_brief: str
    tone_keywords: list[str] = Field(default_factory=list)
    player_profile: str
    confirmed_dimensions: list[str] = Field(default_factory=list)
    emergent_dimensions: list[str] = Field(default_factory=list)
    forged_modules: list[ForgeModuleSummary] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    blueprint: BlueprintModel
    system_prompt: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorPayload


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class SessionRecordModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
