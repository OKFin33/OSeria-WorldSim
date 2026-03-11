"""Session storage for the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from .interviewer import InterviewArtifacts, Interviewer


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class SessionRecord:
    session_id: str
    interviewer: Interviewer
    artifacts: InterviewArtifacts | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


class SessionStore(Protocol):
    def create(self, interviewer: Interviewer) -> SessionRecord:
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

    def create(self, interviewer: Interviewer) -> SessionRecord:
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

