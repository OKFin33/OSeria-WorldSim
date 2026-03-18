"""JSON-backed session storage for Runtime."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .common import DEFAULT_SESSIONS_DIR
from .domain import RuntimeSession


class RuntimeSessionStore(Protocol):
    def create(self, session: RuntimeSession) -> RuntimeSession:
        ...

    def get(self, session_id: str) -> RuntimeSession | None:
        ...

    def save(self, session: RuntimeSession) -> None:
        ...

    def list(self) -> list[RuntimeSession]:
        ...


class JsonRuntimeSessionStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        configured_dir = base_dir or os.getenv("RUNTIME_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
        self.base_dir = Path(configured_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(self, session: RuntimeSession) -> RuntimeSession:
        if not session.session_id:
            session.session_id = uuid4().hex
        self.save(session)
        return session

    def get(self, session_id: str) -> RuntimeSession | None:
        path = self.base_dir / f"{session_id}.json"
        if not path.exists():
            return None
        return RuntimeSession.from_dict(__import__("json").loads(path.read_text(encoding="utf-8")))

    def save(self, session: RuntimeSession) -> None:
        import json

        session.touch()
        path = self.base_dir / f"{session.session_id}.json"
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> list[RuntimeSession]:
        sessions: list[RuntimeSession] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                session = RuntimeSession.from_dict(
                    __import__("json").loads(path.read_text(encoding="utf-8"))
                )
            except Exception:
                continue
            sessions.append(session)
        sessions.sort(key=lambda item: item.updated_at, reverse=True)
        return sessions
