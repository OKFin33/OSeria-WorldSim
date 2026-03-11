"""Pydantic models for the FastAPI layer."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BackendPhase(str, Enum):
    INTERVIEWING = "interviewing"
    MIRROR = "mirror"
    LANDING = "landing"
    COMPLETE = "complete"


class ForgeModuleSummary(BaseModel):
    dimension: str
    pack_id: str | None


class InterviewArtifactsModel(BaseModel):
    confirmed_dimensions: list[str] = Field(default_factory=list)
    emergent_dimensions: list[str] = Field(default_factory=list)
    excluded_dimensions: list[str] = Field(default_factory=list)
    narrative_briefing: str = ""
    player_profile: str = ""


class StartInterviewResponse(BaseModel):
    session_id: str
    phase: BackendPhase
    message: str
    raw_payload: dict | None = None


class InterviewMessageRequest(BaseModel):
    session_id: str
    message: str | None = None
    mirror_action: Literal["confirm", "reconsider"] | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "InterviewMessageRequest":
        has_message = bool(self.message and self.message.strip())
        if self.mirror_action is None and not has_message:
            raise ValueError("Either message or mirror_action must be provided.")
        if self.mirror_action is None:
            return self
        if self.mirror_action not in {"confirm", "reconsider"}:
            raise ValueError("Unsupported mirror_action.")
        return self


class InterviewStepResponse(BaseModel):
    phase: BackendPhase
    message: str | None = None
    artifacts: InterviewArtifactsModel | None = None
    raw_payload: dict | None = None


class GenerateRequest(BaseModel):
    session_id: str
    artifacts: InterviewArtifactsModel | None = None


class BlueprintSummary(BaseModel):
    title: str
    world_summary: str
    protagonist_hook: str
    core_tension: str
    tone_keywords: list[str] = Field(default_factory=list)
    player_profile: str
    confirmed_dimensions: list[str] = Field(default_factory=list)
    emergent_dimensions: list[str] = Field(default_factory=list)
    forged_modules: list[ForgeModuleSummary] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    blueprint: BlueprintSummary
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

