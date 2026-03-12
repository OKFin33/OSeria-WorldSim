"""Application service layer for the vNext Architect API."""

from __future__ import annotations

from dataclasses import dataclass

from .api_models import (
    BackendPhase,
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
from .domain import BubbleCandidate, CompileOutput, FrozenCompilePackage
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

    @classmethod
    def from_defaults(cls, llm_client: LLMClientProtocol | None = None) -> "ArchitectService":
        client = llm_client or OpenAICompatibleLLMClient.from_env()
        return cls(
            llm_client=client,
            session_store=InMemorySessionStore(),
            conductor=Conductor(),
            result_packager=ResultPackager(),
        )

    async def start_interview(self) -> StartInterviewResponse:
        interviewer = Interviewer(self.llm_client)
        record = self.session_store.create(interviewer)
        record.transaction_status = "idle"
        opening = await interviewer.start()
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
        if step.phase != InterviewPhase.COMPLETE:
            record.compile_output = None
            record.frozen_compile_package = None

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

        try:
            manifest = self.conductor.build_manifest(frozen_package.compile_output)
            forged_results = await Forge(self.llm_client).execute(manifest, frozen_package.forge_context)
            system_prompt = await Assembler(self.llm_client).assemble(
                forged_results,
                manifest,
                frozen_package.assembler_context,
            )
            blueprint = self.result_packager.build_blueprint(
                compile_output=frozen_package.compile_output,
                manifest=manifest,
            )
        except Exception as exc:  # pragma: no cover
            raise ArchitectServiceError(
                code="generate_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

        record.transaction_status = "idle"
        self.session_store.save(record)
        return GenerateResponse(blueprint=blueprint, system_prompt=system_prompt)

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
                compile_output = await record.interviewer.compile_output()
                record.compile_output = compile_output
                record.frozen_compile_package = record.interviewer.freeze_compile_package(compile_output)
                record.transaction_status = "idle"
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
