"""Domain models for Runtime vNext."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _unique_strings(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: list[str] = []
    for raw in values:
        text = str(raw).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


LorebookType = Literal["character", "location", "event", "concept", "faction"]
MessageRole = Literal["user", "assistant", "system"]
BootStatus = Literal["pending", "booting", "ready", "failed"]
LorebookJobStatus = Literal["idle", "queued", "running", "ok", "failed"]


@dataclass
class RuntimeWorldSummary:
    title: str
    world_summary: str
    tone_keywords: list[str] = field(default_factory=list)
    confirmed_dimensions: list[str] = field(default_factory=list)
    emergent_dimensions: list[str] = field(default_factory=list)
    player_profile: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeWorldSummary":
        return cls(
            title=str(payload.get("title", "")).strip(),
            world_summary=str(payload.get("world_summary", "")).strip(),
            tone_keywords=_unique_strings(payload.get("tone_keywords")),
            confirmed_dimensions=_unique_strings(payload.get("confirmed_dimensions")),
            emergent_dimensions=_unique_strings(payload.get("emergent_dimensions")),
            player_profile=str(payload.get("player_profile", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "world_summary": self.world_summary,
            "tone_keywords": _unique_strings(self.tone_keywords),
            "confirmed_dimensions": _unique_strings(self.confirmed_dimensions),
            "emergent_dimensions": _unique_strings(self.emergent_dimensions),
            "player_profile": self.player_profile,
        }


@dataclass
class RuntimeMessage:
    role: MessageRole
    content: str
    turn_number: int
    created_at: str = field(default_factory=_utcnow_iso)
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeMessage":
        role = str(payload.get("role", "system")).strip()
        if role not in {"user", "assistant", "system"}:
            role = "system"
        return cls(
            role=role,  # type: ignore[arg-type]
            content=str(payload.get("content", "")).strip(),
            turn_number=int(payload.get("turn_number", 0)),
            created_at=str(payload.get("created_at", _utcnow_iso())).strip(),
            meta=dict(payload.get("meta", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "turn_number": self.turn_number,
            "created_at": self.created_at,
            "meta": dict(self.meta),
        }


@dataclass
class LorebookEntry:
    id: str
    type: LorebookType
    name: str
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    description: str = ""
    first_seen_turn: int = 0
    last_updated_turn: int = 0
    source_turns: list[int] = field(default_factory=list)
    status: str = ""

    @classmethod
    def create(
        cls,
        *,
        entry_type: LorebookType,
        name: str,
        aliases: list[str] | None,
        keywords: list[str] | None,
        description: str,
        turn_number: int,
        status: str = "",
    ) -> "LorebookEntry":
        return cls(
            id=uuid4().hex,
            type=entry_type,
            name=name.strip(),
            aliases=_unique_strings(aliases),
            keywords=_unique_strings(keywords),
            description=description.strip(),
            first_seen_turn=turn_number,
            last_updated_turn=turn_number,
            source_turns=[turn_number],
            status=status.strip(),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LorebookEntry":
        entry_type = str(payload.get("type", "concept")).strip()
        if entry_type not in {"character", "location", "event", "concept", "faction"}:
            entry_type = "concept"
        return cls(
            id=str(payload.get("id", uuid4().hex)),
            type=entry_type,  # type: ignore[arg-type]
            name=str(payload.get("name", "")).strip(),
            aliases=_unique_strings(payload.get("aliases")),
            keywords=_unique_strings(payload.get("keywords")),
            description=str(payload.get("description", "")).strip(),
            first_seen_turn=int(payload.get("first_seen_turn", 0)),
            last_updated_turn=int(payload.get("last_updated_turn", 0)),
            source_turns=[int(item) for item in payload.get("source_turns", []) if str(item).strip()],
            status=str(payload.get("status", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "aliases": _unique_strings(self.aliases),
            "keywords": _unique_strings(self.keywords),
            "description": self.description,
            "first_seen_turn": self.first_seen_turn,
            "last_updated_turn": self.last_updated_turn,
            "source_turns": list(dict.fromkeys(self.source_turns)),
            "status": self.status,
        }


@dataclass
class TurnSummary:
    turn_number: int
    user_action: str
    assistant_text: str
    summary: str
    timestamp_label: str = ""
    location_label: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurnSummary":
        return cls(
            turn_number=int(payload.get("turn_number", 0)),
            user_action=str(payload.get("user_action", "")).strip(),
            assistant_text=str(payload.get("assistant_text", "")).strip(),
            summary=str(payload.get("summary", "")).strip(),
            timestamp_label=str(payload.get("timestamp_label", "")).strip(),
            location_label=str(payload.get("location_label", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "user_action": self.user_action,
            "assistant_text": self.assistant_text,
            "summary": self.summary,
            "timestamp_label": self.timestamp_label,
            "location_label": self.location_label,
        }


@dataclass
class RuntimeErrorRecord:
    stage: str
    code: str
    message: str
    retryable: bool
    status_code: int
    created_at: str = field(default_factory=_utcnow_iso)
    turn_number: int = 0
    user_action: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeErrorRecord":
        return cls(
            stage=str(payload.get("stage", "")).strip(),
            code=str(payload.get("code", "")).strip(),
            message=str(payload.get("message", "")).strip(),
            retryable=bool(payload.get("retryable", False)),
            status_code=int(payload.get("status_code", 0)),
            created_at=str(payload.get("created_at", _utcnow_iso())).strip(),
            turn_number=int(payload.get("turn_number", 0)),
            user_action=str(payload.get("user_action", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "status_code": self.status_code,
            "created_at": self.created_at,
            "turn_number": self.turn_number,
            "user_action": self.user_action,
        }


@dataclass
class RuntimeSession:
    session_id: str
    system_prompt: str
    world: RuntimeWorldSummary
    display_title: str = ""
    boot_status: BootStatus = "pending"
    boot_started_at: str = ""
    boot_completed_at: str = ""
    boot_error: str = ""
    boot_generation_count: int = 0
    last_bootstrap_error: RuntimeErrorRecord | None = None
    last_turn_error: RuntimeErrorRecord | None = None
    last_lorebook_error: RuntimeErrorRecord | None = None
    last_lorebook_job_status: LorebookJobStatus = "idle"
    last_lorebook_job_turn: int = 0
    turn_count: int = 0
    messages: list[RuntimeMessage] = field(default_factory=list)
    lorebook: list[LorebookEntry] = field(default_factory=list)
    last_extracted_turn: int = 0
    recent_turn_summaries: list[TurnSummary] = field(default_factory=list)
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeSession":
        return cls(
            session_id=str(payload.get("session_id", "")).strip(),
            system_prompt=str(payload.get("system_prompt", "")).strip(),
            world=RuntimeWorldSummary.from_dict(payload.get("world", {}) or {}),
            display_title=str(payload.get("display_title", "")).strip(),
            boot_status=_normalize_boot_status(str(payload.get("boot_status", "pending"))),
            boot_started_at=str(payload.get("boot_started_at", "")).strip(),
            boot_completed_at=str(payload.get("boot_completed_at", "")).strip(),
            boot_error=str(payload.get("boot_error", "")).strip(),
            boot_generation_count=int(payload.get("boot_generation_count", 0)),
            last_bootstrap_error=(
                RuntimeErrorRecord.from_dict(payload["last_bootstrap_error"])
                if payload.get("last_bootstrap_error")
                else None
            ),
            last_turn_error=(
                RuntimeErrorRecord.from_dict(payload["last_turn_error"])
                if payload.get("last_turn_error")
                else None
            ),
            last_lorebook_error=(
                RuntimeErrorRecord.from_dict(payload["last_lorebook_error"])
                if payload.get("last_lorebook_error")
                else None
            ),
            last_lorebook_job_status=_normalize_lorebook_job_status(
                str(payload.get("last_lorebook_job_status", "idle"))
            ),
            last_lorebook_job_turn=int(payload.get("last_lorebook_job_turn", 0)),
            turn_count=int(payload.get("turn_count", 0)),
            messages=[RuntimeMessage.from_dict(item) for item in payload.get("messages", [])],
            lorebook=[LorebookEntry.from_dict(item) for item in payload.get("lorebook", [])],
            last_extracted_turn=int(payload.get("last_extracted_turn", 0)),
            recent_turn_summaries=[
                TurnSummary.from_dict(item) for item in payload.get("recent_turn_summaries", [])
            ],
            state_snapshot=dict(payload.get("state_snapshot", {}) or {}),
            created_at=str(payload.get("created_at", _utcnow_iso())).strip(),
            updated_at=str(payload.get("updated_at", _utcnow_iso())).strip(),
        )

    def touch(self) -> None:
        self.updated_at = _utcnow_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "world": self.world.to_dict(),
            "display_title": self.display_title,
            "boot_status": self.boot_status,
            "boot_started_at": self.boot_started_at,
            "boot_completed_at": self.boot_completed_at,
            "boot_error": self.boot_error,
            "boot_generation_count": self.boot_generation_count,
            "last_bootstrap_error": self.last_bootstrap_error.to_dict() if self.last_bootstrap_error else None,
            "last_turn_error": self.last_turn_error.to_dict() if self.last_turn_error else None,
            "last_lorebook_error": self.last_lorebook_error.to_dict() if self.last_lorebook_error else None,
            "last_lorebook_job_status": self.last_lorebook_job_status,
            "last_lorebook_job_turn": self.last_lorebook_job_turn,
            "turn_count": self.turn_count,
            "messages": [message.to_dict() for message in self.messages],
            "lorebook": [entry.to_dict() for entry in self.lorebook],
            "last_extracted_turn": self.last_extracted_turn,
            "recent_turn_summaries": [item.to_dict() for item in self.recent_turn_summaries],
            "state_snapshot": dict(self.state_snapshot),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _normalize_boot_status(value: str) -> BootStatus:
    lowered = value.strip().lower()
    if lowered in {"booting", "ready", "failed"}:
        return lowered  # type: ignore[return-value]
    return "pending"


def _normalize_lorebook_job_status(value: str) -> LorebookJobStatus:
    lowered = value.strip().lower()
    if lowered in {"queued", "running", "ok", "failed"}:
        return lowered  # type: ignore[return-value]
    return "idle"
