"""Session storage for the vNext Architect API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from .domain import CompileOutput, DossierUpdateStatus, FrozenCompilePackage, TwinDossier, TurnTransactionStatus

if TYPE_CHECKING:  # pragma: no cover
    from .interviewer import Interviewer


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class SessionRecord:
    session_id: str
    interviewer: "Interviewer"
    twin_dossier: TwinDossier = field(default_factory=TwinDossier.empty)
    compile_output: CompileOutput | None = None
    frozen_compile_package: FrozenCompilePackage | None = None
    last_updated_turn: int = 0
    dossier_update_status: DossierUpdateStatus = "updated"
    transaction_status: TurnTransactionStatus = "idle"
    follow_up_signal: str = ""
    debug_events: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "vnext"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


class SessionStore(Protocol):
    def create(self, interviewer: "Interviewer") -> SessionRecord:
        ...

    def get(self, session_id: str) -> SessionRecord | None:
        ...

    def save(self, record: SessionRecord) -> None:
        ...

    def delete(self, session_id: str) -> None:
        ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    def create(self, interviewer: "Interviewer") -> SessionRecord:
        session_id = uuid4().hex
        record = SessionRecord(session_id=session_id, interviewer=interviewer)
        self._records[session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord | None:
        return self._records.get(session_id)

    def save(self, record: SessionRecord) -> None:
        record.touch()
        self._records[record.session_id] = record

    def delete(self, session_id: str) -> None:
        self._records.pop(session_id, None)
