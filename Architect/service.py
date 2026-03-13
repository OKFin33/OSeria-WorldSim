"""Application service layer for the vNext Architect API."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import time

from .api_models import (
    BackendPhase,
    BlueprintModel,
    BubbleCandidateModel,
    GenerateRequest,
    GenerateResponse,
    InterviewMessageRequest,
    InterviewStepResponse,
    InterviewTurnPayloadModel,
    RoutingSnapshotModel,
    StartInterviewResponse,
)
from .assembler import Assembler
from .conductor import Conductor
from .domain import BubbleCandidate, CompileOutput, FrozenCompilePackage, TwinDossier
from .forge import Forge
from .interview_controller import InterviewPhase
from .interviewer import InterviewStepResult, Interviewer
from .llm_client import LLMClientProtocol, OpenAICompatibleLLMClient
from .result_packager import ResultPackager
from .session_store import InMemorySessionStore, SessionRecord, SessionStore


class ArchitectServiceError(Exception):
    def __init__(self, *, code: str, message: str, retryable: bool, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


@dataclass
class ArchitectService:
    llm_client: LLMClientProtocol
    session_store: SessionStore
    conductor: Conductor
    result_packager: ResultPackager
    dossier_llm_client: LLMClientProtocol | None = None

    @classmethod
    def from_defaults(cls, llm_client: LLMClientProtocol | None = None) -> "ArchitectService":
        client = llm_client or OpenAICompatibleLLMClient.from_env()
        dossier_client = (
            OpenAICompatibleLLMClient.from_prefixed_env("ARCHITECT_DOSSIER_LLM")
            or client
        )
        return cls(
            llm_client=client,
            session_store=InMemorySessionStore(),
            conductor=Conductor(),
            result_packager=ResultPackager(),
            dossier_llm_client=dossier_client,
        )

    async def start_interview(self) -> StartInterviewResponse:
        interviewer = Interviewer(self.llm_client, dossier_llm_client=self.dossier_llm_client)
        record = self.session_store.create(interviewer)
        record.transaction_status = "idle"
        opening = await interviewer.start()
        if opening.debug_trace is not None:
            record.debug_events.append(opening.debug_trace)
        self.session_store.save(record)
        return StartInterviewResponse(
            session_id=record.session_id,
            phase=BackendPhase(opening.phase.value),
            message=opening.message or "",
        )

    async def submit_interview_message(self, request: InterviewMessageRequest) -> InterviewStepResponse:
        record = self._require_session(request.session_id)
        record.transaction_status = "pending_turn"
        self.session_store.save(record)

        runtime_message = self._resolve_runtime_message(request)
        try:
            step = await record.interviewer.process_user_message(runtime_message)
        except ValueError as exc:
            record.transaction_status = "idle"
            self.session_store.save(record)
            raise ArchitectServiceError(
                code="parse_error",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc
        except RuntimeError as exc:
            record.transaction_status = "idle"
            self.session_store.save(record)
            raise ArchitectServiceError(
                code="internal",
                message=str(exc),
                retryable=False,
                status_code=409,
            ) from exc
        except Exception as exc:  # pragma: no cover
            record.transaction_status = "idle"
            self.session_store.save(record)
            raise ArchitectServiceError(
                code="upstream_unavailable",
                message=str(exc),
                retryable=True,
                status_code=503,
            ) from exc

        record.twin_dossier = record.interviewer.twin_dossier
        record.dossier_update_status = record.interviewer.dossier_update_status
        record.follow_up_signal = record.interviewer.follow_up_signal
        record.last_updated_turn = record.interviewer.controller.turn
        if step.debug_trace is not None:
            record.debug_events.append(step.debug_trace)
        if step.phase != InterviewPhase.COMPLETE:
            record.compile_output = None
            record.frozen_compile_package = None
            record.generated_blueprint = None
            record.generated_system_prompt = None

        if step.phase == InterviewPhase.COMPLETE:
            record.transaction_status = "pending_compile"
            await self._compile_and_freeze(record)
        else:
            record.transaction_status = "idle"

        self.session_store.save(record)
        return self._serialize_step(step)

    async def generate_world(self, request: GenerateRequest) -> GenerateResponse:
        record = self._require_session(request.session_id)
        frozen_package = record.frozen_compile_package
        if frozen_package is None:
            await self._compile_and_freeze(record)
            frozen_package = record.frozen_compile_package
        if frozen_package is None:
            raise ArchitectServiceError(
                code="compile_missing",
                message="Frozen compile package is unavailable.",
                retryable=True,
                status_code=409,
            )

        started = time.perf_counter()
        try:
            manifest_started = time.perf_counter()
            manifest = self.conductor.build_manifest(frozen_package.compile_output)
            manifest_elapsed_ms = int((time.perf_counter() - manifest_started) * 1000)

            forge = Forge(self.llm_client)
            forge_started = time.perf_counter()
            forge_result = await forge.execute(manifest, frozen_package.forge_context)
            forge_elapsed_ms = int((time.perf_counter() - forge_started) * 1000)

            assembler = Assembler(self.llm_client)
            assemble_started = time.perf_counter()
            system_prompt = await assembler.assemble(
                forge_result,
                manifest,
                frozen_package.assembler_context,
            )
            assemble_elapsed_ms = int((time.perf_counter() - assemble_started) * 1000)

            blueprint_started = time.perf_counter()
            blueprint = self.result_packager.build_blueprint(
                compile_output=frozen_package.compile_output,
                manifest=manifest,
            )
            blueprint_elapsed_ms = int((time.perf_counter() - blueprint_started) * 1000)
        except Exception as exc:  # pragma: no cover
            raise ArchitectServiceError(
                code="generate_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

        record.transaction_status = "idle"
        record.generated_blueprint = blueprint.model_dump()
        record.generated_system_prompt = system_prompt
        record.debug_events.append(
            {
                "event": "generate_world",
                "phase": BackendPhase.COMPLETE.value,
                "compile_output": frozen_package.compile_output.to_dict(),
                "forge_context": frozen_package.forge_context.to_dict(),
                "assembler_context": frozen_package.assembler_context.to_dict(),
                "manifest": {
                    "confirmed_dimensions": list(manifest.compile_output.confirmed_dimensions),
                    "tasks": [
                        {
                            "module_id": task.module_id,
                            "section": task.section,
                            "forge_mode": task.forge_mode,
                            "dimension": task.dimension,
                            "pack_id": task.pack_id,
                        }
                        for task in manifest.tasks
                    ],
                },
                "module_execution": [execution.to_dict() for execution in forge_result.executions],
                "timing_breakdown": {
                    "manifest_elapsed_ms": manifest_elapsed_ms,
                    "forge_elapsed_ms": forge_elapsed_ms,
                    "forge_llm_elapsed_ms": forge_result.llm_elapsed_ms,
                    "assemble_elapsed_ms": assemble_elapsed_ms,
                    "assembler_debug": assembler.last_debug_info.to_dict(),
                    "blueprint_elapsed_ms": blueprint_elapsed_ms,
                },
                "call_name": "generate_world",
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "fallback_used": False,
                "blueprint": blueprint.model_dump(),
                "system_prompt_preview": system_prompt[:1200],
            }
        )
        self.session_store.save(record)
        return GenerateResponse(blueprint=blueprint, system_prompt=system_prompt)

    def get_debug_session(self, session_id: str) -> dict:
        record = self._require_session(session_id)
        return {
            "session_id": record.session_id,
            "schema_version": record.schema_version,
            "phase": record.interviewer.controller.phase.value,
            "turn": record.interviewer.controller.turn,
            "transaction_status": record.transaction_status,
            "dossier_update_status": record.dossier_update_status,
            "follow_up_signal": record.follow_up_signal,
            "last_updated_turn": record.last_updated_turn,
            "messages": [dict(message) for message in record.interviewer.messages],
            "twin_dossier": record.twin_dossier.to_dict(),
            "compile_output": record.compile_output.to_dict() if record.compile_output else None,
            "frozen_compile_package": (
                record.frozen_compile_package.to_dict() if record.frozen_compile_package else None
            ),
            "debug_events": list(record.debug_events),
        }

    def get_replay_bundle(self, session_id: str) -> dict:
        record = self._require_session(session_id)
        if record.interviewer.controller.phase != InterviewPhase.COMPLETE:
            raise ArchitectServiceError(
                code="debug_replay_not_ready",
                message="Replay bundle is only available after interview completion.",
                retryable=False,
                status_code=409,
            )
        if (
            record.compile_output is None
            or record.frozen_compile_package is None
            or record.generated_blueprint is None
            or record.generated_system_prompt is None
        ):
            raise ArchitectServiceError(
                code="debug_replay_not_ready",
                message="Replay bundle requires a successful /api/generate result.",
                retryable=False,
                status_code=409,
            )

        snapshots = self._build_replay_snapshots(record)
        bundle_name = str(record.generated_blueprint.get("title", "")).strip() or f"Replay {record.session_id[:8]}"
        return {
            "id": f"replay:{record.session_id}",
            "name": bundle_name,
            "source_session_id": record.session_id,
            "captured_at": record.updated_at.isoformat(),
            "snapshots": snapshots,
        }

    def _require_session(self, session_id: str) -> SessionRecord:
        record = self.session_store.get(session_id)
        if record is None:
            raise ArchitectServiceError(
                code="session_expired",
                message=f"Unknown session_id: {session_id}",
                retryable=False,
                status_code=404,
            )
        return record

    async def _compile_and_freeze(self, record: SessionRecord) -> None:
        last_error: Exception | None = None
        for _ in range(2):
            try:
                started = time.perf_counter()
                compile_output = await record.interviewer.compile_output()
                record.compile_output = compile_output
                record.frozen_compile_package = record.interviewer.freeze_compile_package(compile_output)
                record.transaction_status = "idle"
                record.debug_events.append(
                    {
                        "event": "compile_freeze",
                        "phase": BackendPhase.COMPLETE.value,
                        "call_name": "compile_freeze",
                        "elapsed_ms": int((time.perf_counter() - started) * 1000),
                        "fallback_used": False,
                        "compile_output": compile_output.to_dict(),
                        "forge_context": record.frozen_compile_package.forge_context.to_dict(),
                        "assembler_context": record.frozen_compile_package.assembler_context.to_dict(),
                        "llm_observations": record.interviewer._consume_llm_observations(),
                    }
                )
                return
            except Exception as exc:
                last_error = exc

        raise ArchitectServiceError(
            code="compile_failed",
            message=str(last_error),
            retryable=True,
            status_code=502,
        ) from last_error

    def _resolve_runtime_message(self, request: InterviewMessageRequest) -> str:
        if request.mirror_action is None:
            return (request.message or "").strip()
        return "推门" if request.mirror_action == "confirm" else "我得再想想"

    def _serialize_step(self, step: InterviewStepResult) -> InterviewStepResponse:
        raw_payload = None
        if step.raw_payload is not None:
            raw_payload = InterviewTurnPayloadModel(
                turn=int(step.raw_payload["turn"]),
                question=str(step.raw_payload["question"]),
                bubble_candidates=[
                    BubbleCandidateModel(text=item["text"], kind=item["kind"])
                    for item in step.raw_payload.get("bubble_candidates", [])
                ],
                routing_snapshot=RoutingSnapshotModel(**step.raw_payload["routing_snapshot"]),
                dossier_update_status=step.raw_payload["dossier_update_status"],
                follow_up_signal=step.raw_payload.get("follow_up_signal", ""),
            )
        return InterviewStepResponse(
            phase=BackendPhase(step.phase.value),
            message=step.message,
            raw_payload=raw_payload,
        )

    def _build_replay_snapshots(self, record: SessionRecord) -> list[dict]:
        snapshots: list[dict] = []
        messages: list[dict[str, str]] = []
        dossier_state = TwinDossier.empty().to_dict()
        interview_index = 0

        for event in record.debug_events:
            event_name = str(event.get("event", "")).strip()
            if event_name == "start":
                opening_question = str(event.get("opening_question", "")).strip()
                if opening_question:
                    messages = [{"role": "assistant", "content": opening_question}]
                snapshots.append(
                    self._replay_snapshot(
                        key="q1",
                        label="Q1",
                        ui_phase="q1",
                        frontstage={
                            "kind": "start",
                            "response": StartInterviewResponse(
                                session_id=record.session_id,
                                phase=BackendPhase.INTERVIEWING,
                                message=opening_question,
                            ).model_dump(),
                        },
                        backstage=self._replay_backstage(
                            phase=BackendPhase.INTERVIEWING,
                            turn=0,
                            twin_dossier=dossier_state,
                            compile_output=None,
                            frozen_compile_package=None,
                            messages=messages,
                            debug_event=event,
                        ),
                    )
                )
                continue

            if event_name in {"interview_turn", "mirror_reject_recovery"}:
                interview_index += 1
                user_message = str(event.get("user_message", "")).strip()
                if user_message:
                    messages.append({"role": "user", "content": user_message})
                assistant_content = self._compose_assistant_context_entry(
                    visible_text=str(event.get("visible_text", "")).strip(),
                    question=str(event.get("question", "")).strip(),
                )
                if assistant_content:
                    messages.append({"role": "assistant", "content": assistant_content})
                dossier_state = deepcopy(event.get("dossier_after") or dossier_state)
                snapshots.append(
                    self._replay_snapshot(
                        key=f"interview:{interview_index}",
                        label=f"访谈 {interview_index}",
                        ui_phase="interviewing",
                        frontstage={
                            "kind": "step",
                            "response": InterviewStepResponse(
                                phase=BackendPhase.INTERVIEWING,
                                message=str(event.get("visible_text", "")).strip() or None,
                                raw_payload=InterviewTurnPayloadModel(
                                    turn=interview_index,
                                    question=str(event.get("question", "")).strip(),
                                    bubble_candidates=[
                                        BubbleCandidateModel(text=item["text"], kind=item["kind"])
                                        for item in event.get("bubble_candidates", [])
                                        if isinstance(item, dict)
                                    ],
                                    routing_snapshot=RoutingSnapshotModel(
                                        **(event.get("routing_snapshot") or {})
                                    ),
                                    dossier_update_status=event.get("dossier_update_status", "updated"),
                                    follow_up_signal=event.get("follow_up_signal", ""),
                                ),
                            ).model_dump(),
                        },
                        backstage=self._replay_backstage(
                            phase=BackendPhase.INTERVIEWING,
                            turn=interview_index,
                            twin_dossier=dossier_state,
                            compile_output=None,
                            frozen_compile_package=None,
                            messages=messages,
                            debug_event=event,
                        ),
                    )
                )
                continue

            if event_name == "interview_to_mirror":
                user_message = str(event.get("user_message", "")).strip()
                mirror_text = str(event.get("mirror_text", "")).strip()
                if user_message:
                    messages.append({"role": "user", "content": user_message})
                if mirror_text:
                    messages.append({"role": "assistant", "content": mirror_text})
                dossier_state = deepcopy(event.get("dossier_after") or dossier_state)
                snapshots.append(
                    self._replay_snapshot(
                        key="mirror",
                        label="Mirror",
                        ui_phase="mirror",
                        frontstage={
                            "kind": "step",
                            "response": InterviewStepResponse(
                                phase=BackendPhase.MIRROR,
                                message=mirror_text or None,
                                raw_payload=None,
                            ).model_dump(),
                        },
                        backstage=self._replay_backstage(
                            phase=BackendPhase.MIRROR,
                            turn=interview_index or record.last_updated_turn,
                            twin_dossier=dossier_state,
                            compile_output=None,
                            frozen_compile_package=None,
                            messages=messages,
                            debug_event=event,
                        ),
                    )
                )
                continue

            if event_name == "mirror_confirm":
                user_message = str(event.get("user_message", "")).strip()
                landing_text = str(event.get("landing_text", "")).strip()
                if user_message:
                    messages.append({"role": "user", "content": user_message})
                if landing_text:
                    messages.append({"role": "assistant", "content": landing_text})
                snapshots.append(
                    self._replay_snapshot(
                        key="landing",
                        label="Landing",
                        ui_phase="landing",
                        frontstage={
                            "kind": "step",
                            "response": InterviewStepResponse(
                                phase=BackendPhase.LANDING,
                                message=landing_text or None,
                                raw_payload=None,
                            ).model_dump(),
                        },
                        backstage=self._replay_backstage(
                            phase=BackendPhase.LANDING,
                            turn=interview_index or record.last_updated_turn,
                            twin_dossier=dossier_state,
                            compile_output=None,
                            frozen_compile_package=None,
                            messages=messages,
                            debug_event=event,
                        ),
                    )
                )
                continue

            if event_name == "landing_submit":
                user_message = str(event.get("user_message", "")).strip()
                if user_message:
                    messages.append({"role": "user", "content": user_message})
                dossier_state = deepcopy(event.get("dossier_after") or dossier_state)

        complete_event = next(
            (item for item in reversed(record.debug_events) if item.get("event") == "generate_world"),
            None,
        )
        snapshots.append(
            self._replay_snapshot(
                key="complete",
                label="完成态",
                ui_phase="complete",
                frontstage={
                    "kind": "generate",
                    "response": GenerateResponse(
                        blueprint=BlueprintModel.model_validate(record.generated_blueprint),
                        system_prompt=record.generated_system_prompt or "",
                    ).model_dump(),
                },
                backstage=self._replay_backstage(
                    phase=BackendPhase.COMPLETE,
                    turn=record.interviewer.controller.turn,
                    twin_dossier=record.twin_dossier.to_dict(),
                    compile_output=record.compile_output.to_dict() if record.compile_output else None,
                    frozen_compile_package=(
                        record.frozen_compile_package.to_dict() if record.frozen_compile_package else None
                    ),
                    messages=record.interviewer.messages or messages,
                    debug_event=complete_event,
                ),
            )
        )
        return snapshots

    def _compose_assistant_context_entry(self, *, visible_text: str, question: str) -> str:
        parts = [segment.strip() for segment in (visible_text, question) if segment and segment.strip()]
        return "\n".join(parts)

    def _replay_backstage(
        self,
        *,
        phase: BackendPhase,
        turn: int,
        twin_dossier: dict,
        compile_output: dict | None,
        frozen_compile_package: dict | None,
        messages: list[dict[str, str]],
        debug_event: dict | None,
    ) -> dict:
        return {
            "phase": phase.value,
            "turn": turn,
            "twin_dossier": deepcopy(twin_dossier),
            "compile_output": deepcopy(compile_output),
            "frozen_compile_package": deepcopy(frozen_compile_package),
            "messages": [dict(message) for message in messages],
            "debug_event": deepcopy(debug_event),
        }

    def _replay_snapshot(
        self,
        *,
        key: str,
        label: str,
        ui_phase: str,
        frontstage: dict,
        backstage: dict,
    ) -> dict:
        return {
            "key": key,
            "label": label,
            "ui_phase": ui_phase,
            "frontstage": frontstage,
            "backstage": backstage,
        }
