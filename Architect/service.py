"""Application service layer for the Architect API."""

from __future__ import annotations

from dataclasses import dataclass

from .api_models import (
    BackendPhase,
    GenerateRequest,
    GenerateResponse,
    InterviewArtifactsModel,
    InterviewMessageRequest,
    InterviewStepResponse,
    StartInterviewResponse,
)
from .assembler import Assembler
from .conductor import Conductor
from .forge import Forge
from .interviewer import InterviewArtifacts, InterviewStepResult, Interviewer
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
        opening = await interviewer.start()
        self.session_store.save(record)
        return StartInterviewResponse(
            session_id=record.session_id,
            phase=BackendPhase(opening.phase.value),
            message=opening.message or "",
            raw_payload=opening.raw_payload,
        )

    async def submit_interview_message(self, request: InterviewMessageRequest) -> InterviewStepResponse:
        record = self._require_session(request.session_id)
        runtime_message = self._resolve_runtime_message(request)

        try:
            step = await record.interviewer.process_user_message(runtime_message)
        except ValueError as exc:
            raise ArchitectServiceError(
                code="parse_error",
                message=str(exc),
                retryable=False,
                status_code=502,
            ) from exc
        except RuntimeError as exc:
            raise ArchitectServiceError(
                code="internal",
                message=str(exc),
                retryable=False,
                status_code=409,
            ) from exc
        except Exception as exc:  # pragma: no cover - live API/runtime failures
            raise ArchitectServiceError(
                code="upstream_unavailable",
                message=str(exc),
                retryable=True,
                status_code=503,
            ) from exc

        if step.artifacts:
            record.artifacts = step.artifacts
        self.session_store.save(record)
        return self._serialize_step(step)

    async def generate_world(self, request: GenerateRequest) -> GenerateResponse:
        record = self._require_session(request.session_id)
        artifacts = self._resolve_artifacts(record, request.artifacts)

        try:
            manifest = self.conductor.process_interview_results(
                artifacts.routing_tags,
                artifacts.narrative_briefing,
                artifacts.player_profile,
            )
            forged_results = await Forge(self.llm_client).execute(manifest)
            system_prompt = await Assembler(self.llm_client).assemble(forged_results, manifest)
            blueprint = self.result_packager.build_blueprint_summary(
                artifacts=artifacts,
                manifest=manifest,
                system_prompt=system_prompt,
            )
        except Exception as exc:  # pragma: no cover - exercised under live model failures
            raise ArchitectServiceError(
                code="generate_failed",
                message=str(exc),
                retryable=True,
                status_code=502,
            ) from exc

        record.artifacts = artifacts
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

    def _resolve_runtime_message(self, request: InterviewMessageRequest) -> str:
        if request.mirror_action is None:
            return (request.message or "").strip()
        fallback_map = {"confirm": "推门", "reconsider": "重来"}
        return (request.message or fallback_map[request.mirror_action]).strip()

    def _resolve_artifacts(
        self,
        record: SessionRecord,
        request_artifacts: InterviewArtifactsModel | None,
    ) -> InterviewArtifacts:
        if request_artifacts is not None:
            return self._deserialize_artifacts(request_artifacts)
        if record.artifacts is not None:
            return record.artifacts
        raise ArchitectServiceError(
            code="session_expired",
            message="No interview artifacts available for generation.",
            retryable=False,
            status_code=409,
        )

    def _serialize_step(self, step: InterviewStepResult) -> InterviewStepResponse:
        artifacts = None
        if step.artifacts is not None:
            artifacts = self._serialize_artifacts(step.artifacts)
        return InterviewStepResponse(
            phase=BackendPhase(step.phase.value),
            message=step.message,
            artifacts=artifacts,
            raw_payload=step.raw_payload,
        )

    def _serialize_artifacts(self, artifacts: InterviewArtifacts) -> InterviewArtifactsModel:
        return InterviewArtifactsModel(
            confirmed_dimensions=list(artifacts.routing_tags.get("confirmed_dimensions", [])),
            emergent_dimensions=list(artifacts.routing_tags.get("emergent_dimensions", [])),
            excluded_dimensions=list(artifacts.routing_tags.get("excluded_dimensions", [])),
            narrative_briefing=artifacts.narrative_briefing,
            player_profile=artifacts.player_profile,
        )

    def _deserialize_artifacts(self, model: InterviewArtifactsModel) -> InterviewArtifacts:
        return InterviewArtifacts(
            routing_tags={
                "confirmed_dimensions": list(model.confirmed_dimensions),
                "emergent_dimensions": list(model.emergent_dimensions),
                "excluded_dimensions": list(model.excluded_dimensions),
            },
            narrative_briefing=model.narrative_briefing,
            player_profile=model.player_profile,
        )

