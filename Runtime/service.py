"""Service layer for Runtime vNext."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import AsyncIterator
from uuid import uuid4

from .api_models import (
    DisplayTitleUpdateRequest,
    LorebookEntryModel,
    LorebookUpdateStatsModel,
    RuntimeSessionCreateResponse,
    RuntimeSessionDebugResponse,
    RuntimeSessionSnapshotResponse,
    RuntimeStartRequest,
    RuntimeTurnRequest,
    RuntimeTurnResponse,
    RuntimeErrorRecordModel,
    RuntimeWorldListItemModel,
    RuntimeWorldSummaryModel,
    RuntimeMessageModel,
    WorldStatsModel,
)
from .common import PROMPTS_DIR, deep_merge, dump_json, load_text
from .domain import (
    LorebookEntry,
    RuntimeErrorRecord,
    RuntimeMessage,
    RuntimeSession,
    RuntimeWorldSummary,
    TurnSummary,
)
from .llm_client import LLMClientProtocol, OpenAICompatibleLLMClient, extract_first_json_object
from .lorebook import select_relevant_entries, upsert_entries
from .store import JsonRuntimeSessionStore, RuntimeSessionStore

RECENT_MESSAGES_LIMIT = int(os.getenv("RUNTIME_RECENT_MESSAGES_LIMIT", "6"))
RECENT_SUMMARY_LIMIT = int(os.getenv("RUNTIME_RECENT_SUMMARY_LIMIT", "6"))
MAX_LOREBOOK_INJECTION = 5
LOREBOOK_EXTRACTION_INTERVAL = int(os.getenv("RUNTIME_LOREBOOK_EXTRACTION_INTERVAL", "5"))


class RuntimeServiceError(Exception):
    def __init__(self, *, code: str, message: str, retryable: bool, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


@dataclass
class RuntimeService:
    llm_client: LLMClientProtocol
    store: RuntimeSessionStore
    _bootstrap_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    _lorebook_tasks: dict[str, asyncio.Task[None]] = field(default_factory=dict)
    _lorebook_pending_turns: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_defaults(cls, llm_client: LLMClientProtocol | None = None) -> "RuntimeService":
        return cls(
            llm_client=llm_client or OpenAICompatibleLLMClient.from_env(),
            store=JsonRuntimeSessionStore(),
        )

    async def create_session(self, request: RuntimeStartRequest) -> RuntimeSessionCreateResponse:
        session = RuntimeSession(
            session_id=uuid4().hex,
            system_prompt=request.system_prompt.strip(),
            world=RuntimeWorldSummary(
                title=request.title.strip(),
                world_summary=request.world_summary.strip(),
                tone_keywords=list(request.tone_keywords),
                confirmed_dimensions=list(request.confirmed_dimensions),
                emergent_dimensions=list(request.emergent_dimensions),
                player_profile=(request.player_profile or "").strip(),
            ),
            state_snapshot={
                "protagonist_name": "",
                "protagonist_gender": "unknown",
                "current_timestamp": "",
                "current_location": "",
                "important_assets": [],
                "current_situation": request.world_summary.strip(),
                "active_threads": [],
                "status_flags": {},
                "last_scene": "",
            },
        )
        self.store.create(session)
        return RuntimeSessionCreateResponse(
            runtime_session_id=session.session_id,
            intro_message=None,
            world_summary_card=self._world_model(session.world),
            display_title=session.display_title,
            boot_status=session.boot_status,
            turn_count=session.turn_count,
        )

    async def bootstrap_session(self, runtime_session_id: str) -> RuntimeSessionSnapshotResponse:
        session = self._require_session(runtime_session_id)
        if session.boot_status == "ready":
            return self.get_session(runtime_session_id)

        lock = self._bootstrap_lock(runtime_session_id)
        async with lock:
            session = self._require_session(runtime_session_id)
            if session.boot_status in {"ready", "booting"}:
                return self.get_session(runtime_session_id)
            session.boot_status = "booting"
            session.boot_started_at = _utcnow_iso()
            session.boot_completed_at = ""
            session.boot_error = ""
            session.last_bootstrap_error = None
            session.boot_generation_count += 1
            self.store.save(session)
        try:
            intro_payload = await self._generate_turn_payload(
                session=session,
                user_action="Generate the opening scene for this world and end with an immediate hook.",
                relevant_entries=[],
                mode="intro",
            )
        except RuntimeServiceError as exc:
            async with lock:
                session = self._require_session(runtime_session_id)
                session.boot_status = "failed"
                session.boot_completed_at = _utcnow_iso()
                session.boot_error = exc.message
                session.last_bootstrap_error = self._error_record(
                    stage="bootstrap",
                    code="bootstrap_failed",
                    message=exc.message,
                    retryable=exc.retryable,
                    status_code=exc.status_code,
                )
                self.store.save(session)
            raise RuntimeServiceError(
                code="bootstrap_failed",
                message=exc.message,
                retryable=exc.retryable,
                status_code=exc.status_code,
            ) from exc

        intro_text = str(intro_payload.get("assistant_text", "")).strip()
        if not intro_text:
            async with lock:
                session = self._require_session(runtime_session_id)
                session.boot_status = "failed"
                session.boot_completed_at = _utcnow_iso()
                session.boot_error = "Runtime generation returned empty assistant_text."
                session.last_bootstrap_error = self._error_record(
                    stage="bootstrap",
                    code="bootstrap_failed",
                    message="Runtime generation returned empty assistant_text.",
                    retryable=True,
                    status_code=502,
                )
                self.store.save(session)
            raise RuntimeServiceError(
                code="bootstrap_failed",
                message="Runtime generation returned empty assistant_text.",
                retryable=True,
                status_code=502,
            )

        async with lock:
            session = self._require_session(runtime_session_id)
            if not self._has_opening_message(session):
                intro_message = RuntimeMessage(
                    role="assistant",
                    content=intro_text,
                    turn_number=0,
                    meta=dict(intro_payload.get("meta", {}) or {}),
                )
                session.messages.append(intro_message)
                session.state_snapshot = deep_merge(
                    session.state_snapshot,
                    dict(intro_payload.get("world_state_patch", {}) or {}),
                )
                session.state_snapshot["last_scene"] = intro_message.content[:400]
            session.boot_status = "ready"
            session.boot_completed_at = _utcnow_iso()
            session.boot_error = ""
            session.last_bootstrap_error = None
            self.store.save(session)
        return self.get_session(runtime_session_id)

    async def run_turn(self, request: RuntimeTurnRequest) -> RuntimeTurnResponse:
        session, next_turn = self._prepare_turn_session(request)
        relevant_entries = select_relevant_entries(request.user_action, session.lorebook, limit=MAX_LOREBOOK_INJECTION)
        try:
            generated = await self._generate_turn_payload(
                session=session,
                user_action=request.user_action,
                relevant_entries=relevant_entries,
                mode="turn",
            )
        except RuntimeServiceError as exc:
            self._record_turn_error(
                runtime_session_id=request.runtime_session_id,
                error=exc,
                turn_number=next_turn,
                user_action=request.user_action,
            )
            raise
        return self._finalize_turn_success(
            session=session,
            generated=generated,
            runtime_session_id=request.runtime_session_id,
            user_action=request.user_action,
            next_turn=next_turn,
        )

    async def stream_turn(self, request: RuntimeTurnRequest) -> AsyncIterator[dict[str, object]]:
        session, next_turn = self._prepare_turn_session(request)
        relevant_entries = select_relevant_entries(request.user_action, session.lorebook, limit=MAX_LOREBOOK_INJECTION)
        streamer = _AssistantTextStreamer()
        raw_chunks: list[str] = []
        try:
            async for chunk in self._stream_turn_payload(
                session=session,
                user_action=request.user_action,
                relevant_entries=relevant_entries,
                mode="turn",
            ):
                raw_chunks.append(chunk)
                delta = streamer.push(chunk)
                if delta:
                    yield {
                        "event": "assistant_delta",
                        "data": {
                            "delta": delta,
                            "content": streamer.current_text,
                            "turn_number": next_turn,
                        },
                    }
        except RuntimeServiceError as exc:
            self._record_turn_error(
                runtime_session_id=request.runtime_session_id,
                error=exc,
                turn_number=next_turn,
                user_action=request.user_action,
            )
            yield {
                "event": "error",
                "data": {"code": exc.code, "message": exc.message, "retryable": exc.retryable},
            }
            return

        try:
            generated = extract_first_json_object("".join(raw_chunks))
            response = self._finalize_turn_success(
                session=session,
                generated=generated,
                runtime_session_id=request.runtime_session_id,
                user_action=request.user_action,
                next_turn=next_turn,
            )
        except RuntimeServiceError as exc:
            self._record_turn_error(
                runtime_session_id=request.runtime_session_id,
                error=exc,
                turn_number=next_turn,
                user_action=request.user_action,
            )
            yield {
                "event": "error",
                "data": {"code": exc.code, "message": exc.message, "retryable": exc.retryable},
            }
            return
        except Exception as exc:
            error = RuntimeServiceError(
                code="generate_failed",
                message=f"Runtime generation returned malformed JSON: {exc}",
                retryable=True,
                status_code=502,
            )
            self._record_turn_error(
                runtime_session_id=request.runtime_session_id,
                error=error,
                turn_number=next_turn,
                user_action=request.user_action,
            )
            yield {
                "event": "error",
                "data": {"code": error.code, "message": error.message, "retryable": error.retryable},
            }
            return

        yield {"event": "turn_complete", "data": response.model_dump()}

    def get_session(self, runtime_session_id: str) -> RuntimeSessionSnapshotResponse:
        session = self._require_session(runtime_session_id)
        return RuntimeSessionSnapshotResponse(
            runtime_session_id=session.session_id,
            world_summary_card=self._world_model(session.world),
            display_title=session.display_title,
            boot_status=session.boot_status,
            boot_started_at=session.boot_started_at,
            boot_completed_at=session.boot_completed_at,
            boot_error=session.boot_error,
            boot_generation_count=session.boot_generation_count,
            turn_count=session.turn_count,
            messages=[self._message_model(message) for message in session.messages],
            recent_memories=[item.to_dict() for item in session.recent_turn_summaries],
            lorebook=[self._lorebook_model(entry) for entry in session.lorebook],
            world_stats=self._stats_model(session),
            state_snapshot=dict(session.state_snapshot),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def get_session_debug(self, runtime_session_id: str) -> RuntimeSessionDebugResponse:
        session = self._require_session(runtime_session_id)
        return RuntimeSessionDebugResponse(
            runtime_session_id=session.session_id,
            boot_status=session.boot_status,
            turn_count=session.turn_count,
            last_bootstrap_error=self._error_model(session.last_bootstrap_error),
            last_turn_error=self._error_model(session.last_turn_error),
            last_lorebook_error=self._error_model(session.last_lorebook_error),
            last_lorebook_job_status=self._effective_lorebook_job_status(session),
            last_lorebook_job_turn=session.last_lorebook_job_turn,
        )

    def update_display_title(
        self,
        runtime_session_id: str,
        request: DisplayTitleUpdateRequest,
    ) -> RuntimeSessionSnapshotResponse:
        session = self._require_session(runtime_session_id)
        session.display_title = request.display_title.strip()
        self.store.save(session)
        return self.get_session(runtime_session_id)

    def list_worlds(self) -> list[RuntimeWorldListItemModel]:
        items: list[RuntimeWorldListItemModel] = []
        for session in self.store.list():
            preview_source = next(
                (message.content for message in reversed(session.messages) if message.role == "assistant"),
                session.world.world_summary,
            )
            items.append(
                RuntimeWorldListItemModel(
                    runtime_session_id=session.session_id,
                    title=session.world.title,
                    display_title=session.display_title,
                    world_summary=session.world.world_summary,
                    tone_keywords=list(session.world.tone_keywords),
                    turn_count=session.turn_count,
                    updated_at=session.updated_at,
                    preview=preview_source[:120],
                )
            )
        return items

    def _bootstrap_lock(self, runtime_session_id: str) -> asyncio.Lock:
        lock = self._bootstrap_locks.get(runtime_session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._bootstrap_locks[runtime_session_id] = lock
        return lock

    def _has_opening_message(self, session: RuntimeSession) -> bool:
        return any(message.role == "assistant" and message.turn_number == 0 for message in session.messages)

    def _record_turn_error(
        self,
        *,
        runtime_session_id: str,
        error: RuntimeServiceError,
        turn_number: int,
        user_action: str,
    ) -> None:
        session = self._require_session(runtime_session_id)
        session.last_turn_error = self._error_record(
            stage="turn",
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            status_code=error.status_code,
            turn_number=turn_number,
            user_action=user_action,
        )
        self.store.save(session)

    def _prepare_turn_session(self, request: RuntimeTurnRequest) -> tuple[RuntimeSession, int]:
        session = self._require_session(request.runtime_session_id)
        if session.boot_status != "ready" or not session.messages:
            raise RuntimeServiceError(
                code="session_boot_pending",
                message="Runtime session is still bootstrapping its opening scene.",
                retryable=True,
                status_code=409,
            )
        next_turn = session.turn_count + 1
        user_message = RuntimeMessage(role="user", content=request.user_action.strip(), turn_number=next_turn)
        session.messages.append(user_message)
        return session, next_turn

    def _build_turn_generation_request(
        self,
        *,
        session: RuntimeSession,
        user_action: str,
        relevant_entries: list[LorebookEntry],
        mode: str,
    ) -> tuple[str, str, float]:
        system_prompt = session.system_prompt.strip()
        runtime_contract = load_text(PROMPTS_DIR / "runtime_turn_system_prompt.md")
        payload = {
            "mode": mode,
            "runtime_contract": runtime_contract,
            "world": session.world.to_dict(),
            "state_snapshot": self._prompt_state_snapshot(session),
            "recent_messages": [message.to_dict() for message in session.messages[-RECENT_MESSAGES_LIMIT:]],
            "recent_turn_summaries": [item.to_dict() for item in session.recent_turn_summaries[-RECENT_SUMMARY_LIMIT:]],
            "relevant_lorebook_entries": [entry.to_dict() for entry in relevant_entries],
            "user_action": user_action,
        }
        temperature = 0.7 if mode == "turn" else 0.6
        return system_prompt, dump_json(payload), temperature

    def _queue_lorebook_sync(self, runtime_session_id: str, target_turn: int) -> None:
        pending_turn = self._lorebook_pending_turns.get(runtime_session_id, 0)
        self._lorebook_pending_turns[runtime_session_id] = max(target_turn, pending_turn)
        existing_task = self._lorebook_tasks.get(runtime_session_id)
        if existing_task is None or existing_task.done():
            self._lorebook_tasks[runtime_session_id] = asyncio.create_task(
                self._drain_lorebook_jobs(runtime_session_id)
            )

    async def _drain_lorebook_jobs(self, runtime_session_id: str) -> None:
        try:
            while True:
                target_turn = self._lorebook_pending_turns.pop(runtime_session_id, None)
                if target_turn is None:
                    break
                session = self._require_session(runtime_session_id)
                session.last_lorebook_job_status = "running"
                session.last_lorebook_job_turn = target_turn
                self.store.save(session)
                try:
                    await self._extract_and_update_lorebook(session)
                    self.store.save(session)
                except RuntimeServiceError as exc:
                    failed_session = self._require_session(runtime_session_id)
                    failed_session.last_lorebook_job_status = "failed"
                    failed_session.last_lorebook_job_turn = target_turn
                    failed_session.last_lorebook_error = self._error_record(
                        stage="lorebook",
                        code=exc.code,
                        message=exc.message,
                        retryable=exc.retryable,
                        status_code=exc.status_code,
                        turn_number=target_turn,
                    )
                    self.store.save(failed_session)
                    continue

                completed_session = self._require_session(runtime_session_id)
                completed_session.last_lorebook_job_status = "ok"
                completed_session.last_lorebook_job_turn = target_turn
                completed_session.last_lorebook_error = None
                self.store.save(completed_session)
        finally:
            self._lorebook_tasks.pop(runtime_session_id, None)

    def _error_record(
        self,
        *,
        stage: str,
        code: str,
        message: str,
        retryable: bool,
        status_code: int,
        turn_number: int = 0,
        user_action: str = "",
    ) -> RuntimeErrorRecord:
        return RuntimeErrorRecord(
            stage=stage,
            code=code,
            message=message,
            retryable=retryable,
            status_code=status_code,
            turn_number=turn_number,
            user_action=user_action,
        )

    async def _generate_turn_payload(
        self,
        *,
        session: RuntimeSession,
        user_action: str,
        relevant_entries: list[LorebookEntry],
        mode: str,
    ) -> dict[str, object]:
        system_prompt, prompt, temperature = self._build_turn_generation_request(
            session=session,
            user_action=user_action,
            relevant_entries=relevant_entries,
            mode=mode,
        )
        try:
            return await self.llm_client.generate_json(
                prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeServiceError(
                code="generate_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

    async def _stream_turn_payload(
        self,
        *,
        session: RuntimeSession,
        user_action: str,
        relevant_entries: list[LorebookEntry],
        mode: str,
    ) -> AsyncIterator[str]:
        system_prompt, prompt, temperature = self._build_turn_generation_request(
            session=session,
            user_action=user_action,
            relevant_entries=relevant_entries,
            mode=mode,
        )
        try:
            async for chunk in self.llm_client.stream_chat(
                [{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=temperature,
                response_format="json_object",
            ):
                yield chunk
        except Exception as exc:
            raise RuntimeServiceError(
                code="generate_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

    async def _extract_and_update_lorebook(
        self,
        session: RuntimeSession,
    ) -> tuple[list[LorebookEntry], dict[str, int]]:
        payload = {
            "world": session.world.to_dict(),
            "recent_turn_summaries": [item.to_dict() for item in session.recent_turn_summaries[-RECENT_SUMMARY_LIMIT:]],
            "existing_lorebook": [entry.to_dict() for entry in session.lorebook],
        }
        try:
            result = await self.llm_client.generate_json(
                dump_json(payload),
                system_prompt=load_text(PROMPTS_DIR / "lorebook_extractor_system_prompt.md"),
                temperature=0.25,
            )
        except Exception as exc:
            raise RuntimeServiceError(
                code="lorebook_extract_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

        extracted = result.get("entries", [])
        if not isinstance(extracted, list):
            extracted = []
        session.lorebook, changed_entries, stats = upsert_entries(
            session.lorebook,
            extracted,
            turn_number=session.turn_count,
        )
        session.last_extracted_turn = session.turn_count
        return changed_entries, stats

    def _require_session(self, runtime_session_id: str) -> RuntimeSession:
        session = self.store.get(runtime_session_id)
        if session is None:
            raise RuntimeServiceError(
                code="session_not_found",
                message=f"Unknown runtime_session_id: {runtime_session_id}",
                retryable=False,
                status_code=404,
            )
        return session

    def _world_model(self, world: RuntimeWorldSummary) -> RuntimeWorldSummaryModel:
        return RuntimeWorldSummaryModel(**world.to_dict())

    def _message_model(self, message: RuntimeMessage) -> RuntimeMessageModel:
        return RuntimeMessageModel(**message.to_dict())

    def _lorebook_model(self, entry: LorebookEntry) -> LorebookEntryModel:
        return LorebookEntryModel(**entry.to_dict())

    def _error_model(self, entry: RuntimeErrorRecord | None) -> RuntimeErrorRecordModel | None:
        if entry is None:
            return None
        return RuntimeErrorRecordModel(**entry.to_dict())

    def _effective_lorebook_job_status(self, session: RuntimeSession) -> str:
        if session.last_lorebook_job_status in {"queued", "running"}:
            if session.session_id in self._lorebook_pending_turns:
                return "queued"
            task = self._lorebook_tasks.get(session.session_id)
            if task is not None and not task.done():
                return "running" if session.last_lorebook_job_status == "running" else "queued"
            if task is None or task.done():
                return "idle"
        return session.last_lorebook_job_status

    def _prompt_state_snapshot(self, session: RuntimeSession) -> dict[str, object]:
        snapshot = session.state_snapshot
        return {
            "protagonist_name": str(snapshot.get("protagonist_name", "")).strip(),
            "protagonist_gender": str(snapshot.get("protagonist_gender", "unknown")).strip(),
            "current_timestamp": str(snapshot.get("current_timestamp", "")).strip(),
            "current_location": str(snapshot.get("current_location", "")).strip(),
            "current_situation": str(snapshot.get("current_situation", "")).strip(),
            "active_threads": [
                str(item).strip() for item in snapshot.get("active_threads", []) if str(item).strip()
            ],
            "important_assets": [
                str(item).strip() for item in snapshot.get("important_assets", []) if str(item).strip()
            ],
        }

    def _finalize_turn_success(
        self,
        *,
        session: RuntimeSession,
        generated: dict[str, object],
        runtime_session_id: str,
        user_action: str,
        next_turn: int,
    ) -> RuntimeTurnResponse:
        assistant_message = RuntimeMessage(
            role="assistant",
            content=str(generated.get("assistant_text", "")).strip(),
            turn_number=next_turn,
            meta=dict(generated.get("meta", {}) or {}),
        )
        if not assistant_message.content:
            raise RuntimeServiceError(
                code="generate_failed",
                message="Runtime generation returned empty assistant_text.",
                retryable=True,
                status_code=502,
            )

        session.messages.append(assistant_message)
        session.turn_count = next_turn
        session.state_snapshot = deep_merge(
            session.state_snapshot,
            dict(generated.get("world_state_patch", {}) or {}),
        )
        session.state_snapshot["last_scene"] = assistant_message.content[:400]

        summary = str(generated.get("turn_summary", "")).strip() or assistant_message.content[:180]
        session.recent_turn_summaries.append(
            TurnSummary(
                turn_number=next_turn,
                user_action=user_action.strip(),
                assistant_text=assistant_message.content,
                summary=summary,
                timestamp_label=str(session.state_snapshot.get("current_timestamp", "")).strip(),
                location_label=str(session.state_snapshot.get("current_location", "")).strip(),
            )
        )
        session.recent_turn_summaries = session.recent_turn_summaries[-RECENT_SUMMARY_LIMIT:]

        changed_entries: list[LorebookEntry] = []
        stats = {"inserted": 0, "updated": 0, "total": len(session.lorebook)}
        should_queue_lorebook = session.turn_count % LOREBOOK_EXTRACTION_INTERVAL == 0
        if should_queue_lorebook:
            session.last_lorebook_job_status = "queued"
            session.last_lorebook_job_turn = session.turn_count
            session.last_lorebook_error = None
            self._queue_lorebook_sync(runtime_session_id, session.turn_count)

        session.last_turn_error = None
        self.store.save(session)
        return RuntimeTurnResponse(
            assistant_message=self._message_model(assistant_message),
            turn_count=session.turn_count,
            world_stats=self._stats_model(session),
            state_snapshot=dict(session.state_snapshot),
            recent_memories=[item.to_dict() for item in session.recent_turn_summaries],
            lorebook=[self._lorebook_model(entry) for entry in session.lorebook],
            lorebook_updates=[self._lorebook_model(entry) for entry in changed_entries],
            lorebook_update_stats=LorebookUpdateStatsModel(**stats),
            updated_at=session.updated_at,
        )

    async def wait_for_lorebook_jobs(self, runtime_session_id: str | None = None) -> None:
        if runtime_session_id is not None:
            task = self._lorebook_tasks.get(runtime_session_id)
            if task is not None:
                await asyncio.shield(task)
            return
        tasks = [task for task in self._lorebook_tasks.values() if not task.done()]
        if tasks:
            await asyncio.gather(*(asyncio.shield(task) for task in tasks), return_exceptions=True)

    def _stats_model(self, session: RuntimeSession) -> WorldStatsModel:
        return WorldStatsModel(
            protagonist_name=str(session.state_snapshot.get("protagonist_name", "")).strip(),
            protagonist_gender=_normalize_gender(str(session.state_snapshot.get("protagonist_gender", "unknown"))),
            current_timestamp=str(session.state_snapshot.get("current_timestamp", "")).strip(),
            current_location=str(session.state_snapshot.get("current_location", "")).strip(),
            important_assets=[
                str(item).strip()
                for item in session.state_snapshot.get("important_assets", [])
                if str(item).strip()
            ],
        )


def _normalize_gender(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"male", "man", "m", "男"}:
        return "male"
    if lowered in {"female", "woman", "f", "女"}:
        return "female"
    return "unknown"


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class _AssistantTextStreamer:
    def __init__(self) -> None:
        self._buffer = ""
        self.current_text = ""

    def push(self, chunk: str) -> str:
        self._buffer += chunk
        current_text = _extract_partial_json_string(self._buffer, "assistant_text")
        if current_text is None or current_text == self.current_text:
            return ""
        delta = current_text[len(self.current_text) :]
        self.current_text = current_text
        return delta


def _extract_partial_json_string(raw: str, key: str) -> str | None:
    key_marker = f'"{key}"'
    key_index = raw.find(key_marker)
    if key_index == -1:
        return None
    colon_index = raw.find(":", key_index + len(key_marker))
    if colon_index == -1:
        return None
    value_index = colon_index + 1
    while value_index < len(raw) and raw[value_index].isspace():
        value_index += 1
    if value_index >= len(raw) or raw[value_index] != '"':
        return None

    chars: list[str] = []
    escape = False
    index = value_index + 1
    while index < len(raw):
        char = raw[index]
        if escape:
            decoded, consumed = _decode_json_escape(raw, index)
            if decoded is None:
                break
            chars.append(decoded)
            index = consumed
            escape = False
        else:
            if char == "\\":
                escape = True
            elif char == '"':
                break
            else:
                chars.append(char)
        index += 1
    return "".join(chars)


def _decode_json_escape(raw: str, index: int) -> tuple[str | None, int]:
    char = raw[index]
    if char == "n":
        return "\n", index
    if char == "r":
        return "\r", index
    if char == "t":
        return "\t", index
    if char in {'"', "\\", "/"}:
        return char, index
    if char == "u":
        if index + 4 >= len(raw):
            return None, index
        codepoint = raw[index + 1 : index + 5]
        try:
            return chr(int(codepoint, 16)), index + 4
        except ValueError:
            return None, index
    return char, index
