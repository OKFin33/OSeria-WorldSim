"""vNext stateful runtime: dossier update, composition, bubble generation, and compile freeze."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .common import OPENING_QUESTION, PROMPTS_DIR, dump_json, load_text
from .domain import (
    BubbleCandidate,
    CompileOutput,
    DossierUpdateStatus,
    FrozenCompilePackage,
    ScopeState,
    TwinDossier,
    build_assembler_context,
    build_forge_context,
)
from .dimension_registry import InterviewDimensionRegistry
from .interview_controller import InterviewController, InterviewPhase
from .llm_client import LLMClientProtocol

MAX_BUBBLES = 3
DOSSIER_BOOTSTRAP_TIMEOUT_SECONDS = 30.0
DOSSIER_STABILIZE_TIMEOUT_SECONDS = 20.0
ALLOWED_FOUNDATION_GAPS = {
    "missing_stage",
    "missing_group_context",
    "missing_role_position",
    "missing_world_top_cover",
}


@dataclass
class InterviewStepResult:
    phase: InterviewPhase
    message: str | None = None
    raw_payload: dict[str, Any] | None = None
    debug_trace: dict[str, Any] | None = None


class Interviewer:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        *,
        controller: InterviewController | None = None,
        dossier_llm_client: LLMClientProtocol | None = None,
    ) -> None:
        self.llm = llm_client
        self.dossier_llm = dossier_llm_client or llm_client
        self.controller = controller or InterviewController()
        self.dimension_registry = InterviewDimensionRegistry.load()
        self.messages: list[dict[str, str]] = []
        self.started = False

        self.twin_dossier = TwinDossier.empty()
        self.dossier_update_status: DossierUpdateStatus = "updated"
        self.follow_up_signal = ""
        self.user_gender = ""
        self.protagonist_gender = "unknown"
        self.protagonist_name_mode = "generated"
        self.protagonist_name_input = ""
        self._last_landing_debug: dict[str, str | bool] = {
            "fallback_used": False,
            "fallback_reason": "",
        }

        self.dossier_updater_prompt = self._compose_dossier_updater_prompt()
        self.interview_composer_prompt = load_text(PROMPTS_DIR / "interview_composer_system_prompt.md")
        self.bubble_composer_prompt = load_text(PROMPTS_DIR / "bubble_composer_system_prompt.md")
        self.compile_output_prompt = load_text(PROMPTS_DIR / "compile_output_system_prompt.md")
        self._llm_observations: list[dict[str, Any]] = []

    async def start(self) -> InterviewStepResult:
        if not self.started:
            self.started = True
            self.messages.append({"role": "assistant", "content": OPENING_QUESTION})
        return InterviewStepResult(
            phase=self.controller.phase,
            message=OPENING_QUESTION,
            debug_trace={
                "event": "start",
                "phase_before": InterviewPhase.INTERVIEWING.value,
                "phase_after": self.controller.phase.value,
                "opening_question": OPENING_QUESTION,
            },
        )

    async def process_user_message(
        self,
        user_message: str,
        *,
        landing_payload: dict[str, Any] | None = None,
    ) -> InterviewStepResult:
        if not self.started:
            await self.start()

        if self.controller.phase == InterviewPhase.COMPLETE:
            raise RuntimeError("Interview is already complete.")

        normalized_message = user_message.strip()
        if self.controller.phase == InterviewPhase.LANDING and landing_payload is not None:
            normalized_message = self._serialize_landing_payload(landing_payload)
        if normalized_message:
            self.messages.append({"role": "user", "content": normalized_message})

        if self.controller.phase == InterviewPhase.INTERVIEWING:
            return await self._handle_interview_turn(current_phase="interviewing")
        if self.controller.phase == InterviewPhase.MIRROR:
            return await self._handle_mirror_feedback(normalized_message)
        if self.controller.phase == InterviewPhase.LANDING:
            return await self._handle_landing_submission(landing_payload)

        raise RuntimeError(f"Unsupported interview phase: {self.controller.phase}")

    async def compile_output(self) -> CompileOutput:
        self._begin_llm_observations()
        payload = await self._generate_json(
            call_name="compile_output",
            system_prompt=self.compile_output_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "recent_context": self._recent_context(limit=2),
            },
            temperature=0.2,
        )
        return self._normalize_compile_output(CompileOutput.from_dict(payload))

    def freeze_compile_package(self, compile_output: CompileOutput) -> FrozenCompilePackage:
        return FrozenCompilePackage(
            compile_output=compile_output,
            forge_context=build_forge_context(self.twin_dossier),
            assembler_context=build_assembler_context(self.twin_dossier),
        )

    async def _handle_interview_turn(self, *, current_phase: str) -> InterviewStepResult:
        if current_phase != "interviewing":
            raise RuntimeError("Only interviewing turns can trigger dossier updates.")

        self._begin_llm_observations()
        dossier_before = self.twin_dossier.to_dict()
        user_message = self._latest_user_message()
        update_status = await self._run_dossier_updater()
        next_phase = self.controller.process_turn(
            {"routing_snapshot": self.twin_dossier.routing_snapshot.to_dict()}
        )

        if next_phase == InterviewPhase.MIRROR:
            mirror_text = await self._compose_mirror()
            self.messages.append({"role": "assistant", "content": mirror_text})
            self.follow_up_signal = ""
            return InterviewStepResult(
                phase=InterviewPhase.MIRROR,
                message=mirror_text,
                debug_trace={
                    "event": "interview_to_mirror",
                    "phase_before": current_phase,
                    "phase_after": InterviewPhase.MIRROR.value,
                    "user_message": user_message,
                    "dossier_before": dossier_before,
                    "dossier_after": self.twin_dossier.to_dict(),
                    "dossier_update_status": update_status,
                    "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                    "mirror_text": mirror_text,
                    "fallback_used": update_status == "update_skipped",
                    "llm_observations": self._consume_llm_observations(),
                },
            )

        question_result = await self._compose_interview_response()
        return InterviewStepResult(
            phase=InterviewPhase.INTERVIEWING,
            message=question_result["visible_text"],
            raw_payload=self._build_turn_payload(
                turn=self.controller.turn + 1,
                question=question_result["question"],
                bubble_candidates=question_result["bubble_candidates"],
                update_status=update_status,
                follow_up_signal=self.follow_up_signal,
            ),
            debug_trace={
                "event": "interview_turn",
                "phase_before": current_phase,
                "phase_after": InterviewPhase.INTERVIEWING.value,
                "user_message": user_message,
                "dossier_before": dossier_before,
                "dossier_after": self.twin_dossier.to_dict(),
                "dossier_update_status": update_status,
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "visible_text": question_result["visible_text"],
                "question": question_result["question"],
                "bubble_candidates": [
                    candidate.to_dict() for candidate in question_result["bubble_candidates"]
                ],
                "follow_up_signal": self.follow_up_signal,
                "fallback_used": update_status == "update_skipped",
                "llm_observations": self._consume_llm_observations(),
            },
        )

    async def _handle_mirror_feedback(self, user_message: str) -> InterviewStepResult:
        self._begin_llm_observations()
        disposition = self._classify_mirror_feedback(user_message)
        if disposition == "confirm":
            next_phase = self.controller.process_turn({})
            landing = await self._compose_landing()
            self.messages.append({"role": "assistant", "content": landing})
            return InterviewStepResult(
                phase=next_phase,
                message=landing,
                debug_trace={
                    "event": "mirror_confirm",
                    "phase_before": InterviewPhase.MIRROR.value,
                    "phase_after": next_phase.value,
                    "user_message": user_message,
                    "mirror_disposition": disposition,
                    "landing_text": landing,
                    "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                    "dossier_update_status": self.dossier_update_status,
                    "fallback_used": bool(self._last_landing_debug.get("fallback_used", False)),
                    "fallback_reason": str(self._last_landing_debug.get("fallback_reason", "")).strip(),
                    "llm_observations": self._consume_llm_observations(),
                },
            )

        self.controller.phase = InterviewPhase.INTERVIEWING
        if "mirror_rejected" not in self.twin_dossier.change_log.needs_follow_up:
            self.twin_dossier.change_log.needs_follow_up.append("mirror_rejected")
        self.follow_up_signal = "mirror_rejected"
        question_result = await self._compose_interview_response()
        return InterviewStepResult(
            phase=InterviewPhase.INTERVIEWING,
            message=question_result["visible_text"],
            raw_payload=self._build_turn_payload(
                turn=self.controller.turn + 1,
                question=question_result["question"],
                bubble_candidates=question_result["bubble_candidates"],
                update_status=self.dossier_update_status,
                follow_up_signal="mirror_rejected",
            ),
            debug_trace={
                "event": "mirror_reject_recovery",
                "phase_before": InterviewPhase.MIRROR.value,
                "phase_after": InterviewPhase.INTERVIEWING.value,
                "user_message": user_message,
                "mirror_disposition": disposition,
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "dossier_after": self.twin_dossier.to_dict(),
                "dossier_update_status": self.dossier_update_status,
                "visible_text": question_result["visible_text"],
                "question": question_result["question"],
                "bubble_candidates": [
                    candidate.to_dict() for candidate in question_result["bubble_candidates"]
                ],
                "follow_up_signal": "mirror_rejected",
                "fallback_used": False,
                "llm_observations": self._consume_llm_observations(),
            },
        )

    async def _handle_landing_submission(self, landing_payload: dict[str, Any] | None) -> InterviewStepResult:
        dossier_before = self.twin_dossier.to_dict()
        user_message = self._latest_user_message()
        if landing_payload is not None:
            self.user_gender = str(landing_payload.get("user_gender", "")).strip()
            self.protagonist_gender = self._normalize_avatar_gender(
                str(landing_payload.get("avatar_gender", "")).strip()
            )
            self.protagonist_name_mode = str(landing_payload.get("name_mode", "generated")).strip() or "generated"
            if self.protagonist_name_mode == "custom":
                self.protagonist_name_input = str(landing_payload.get("custom_name", "")).strip()
            else:
                self.protagonist_name_input = ""
        # Landing only collects finishing metadata; dossier should already be stabilized before mirror.
        self.dossier_update_status = "update_skipped"
        self.controller.process_turn({})
        return InterviewStepResult(
            phase=InterviewPhase.COMPLETE,
            message=None,
            debug_trace={
                "event": "landing_submit",
                "phase_before": InterviewPhase.LANDING.value,
                "phase_after": InterviewPhase.COMPLETE.value,
                "user_message": user_message,
                "dossier_before": dossier_before,
                "dossier_after": self.twin_dossier.to_dict(),
                "dossier_update_status": self.dossier_update_status,
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "landing_payload": dict(landing_payload or {}),
                "protagonist_gender": self.protagonist_gender,
                "protagonist_name_mode": self.protagonist_name_mode,
                "protagonist_name_input": self.protagonist_name_input,
            },
        )

    async def _run_dossier_updater(self) -> DossierUpdateStatus:
        previous = self.twin_dossier
        updater_mode = self._dossier_update_mode()
        payload = self._build_dossier_updater_payload(previous)
        can_reuse_previous = self._can_conservatively_reuse(previous)
        max_retries = 1 if updater_mode == "bootstrap" and not can_reuse_previous else 0
        timeout = (
            DOSSIER_BOOTSTRAP_TIMEOUT_SECONDS
            if updater_mode == "bootstrap"
            else DOSSIER_STABILIZE_TIMEOUT_SECONDS
        )

        try:
            updated = await self._generate_json(
                call_name="dossier_updater",
                system_prompt=self.dossier_updater_prompt,
                user_payload=payload,
                temperature=0.15,
                timeout=timeout,
                max_retries=max_retries,
            )
            self.twin_dossier = self._normalize_twin_dossier(
                TwinDossier.from_dict(updated),
                updater_mode=updater_mode,
                previous=previous,
            )
            self.dossier_update_status = "updated"
            return self.dossier_update_status
        except Exception as exc:
            last_error = exc

        if can_reuse_previous:
            self.twin_dossier = previous
            self.dossier_update_status = "update_skipped"
            return self.dossier_update_status

        self.dossier_update_status = "hard_failed"
        raise ValueError(f"Dossier update failed: {last_error}") from last_error

    async def _compose_interview_response(self) -> dict[str, Any]:
        payload = await self._generate_json(
            call_name="interview_composer_interview",
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "scope_state": self.twin_dossier.scope_state.to_dict(),
                "recent_context": self._recent_context(limit=4),
                "current_phase": "interviewing",
                "dossier_update_status": self.dossier_update_status,
                "follow_up_signal": self.follow_up_signal,
            },
            temperature=0.7,
        )
        visible_text = str(payload.get("visible_text", "")).strip()
        question = str(payload.get("question", "")).strip()
        if not visible_text or not question:
            raise ValueError("InterviewComposer did not return visible_text/question.")
        bubbles = await self._compose_bubbles(question=question, visible_text=visible_text)
        self.messages.append({"role": "assistant", "content": self._compose_assistant_context_entry(visible_text, question)})
        self.follow_up_signal = ""
        return {
            "visible_text": visible_text,
            "question": question,
            "bubble_candidates": bubbles,
        }

    async def _compose_mirror(self) -> str:
        payload = await self._generate_json(
            call_name="interview_composer_mirror",
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "scope_state": self.twin_dossier.scope_state.to_dict(),
                "recent_context": self._recent_context(limit=4),
                "current_phase": "mirror",
                "dossier_update_status": self.dossier_update_status,
                "follow_up_signal": self.follow_up_signal,
            },
            temperature=0.65,
        )
        mirror_text = str(payload.get("mirror_text", "")).strip()
        if not mirror_text:
            raise ValueError("InterviewComposer did not return mirror_text.")
        return mirror_text

    async def _compose_landing(self) -> str:
        self._last_landing_debug = {"fallback_used": False, "fallback_reason": ""}
        payload = await self._generate_json(
            call_name="interview_composer_landing",
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "scope_state": self.twin_dossier.scope_state.to_dict(),
                "recent_context": self._recent_context(limit=4),
                "current_phase": "landing",
                "dossier_update_status": self.dossier_update_status,
                "follow_up_signal": self.follow_up_signal,
            },
            temperature=0.45,
        )
        text = str(payload.get("visible_text") or payload.get("question") or "").strip()
        latest_assistant = self.messages[-1]["content"].strip() if self.messages else ""
        mode = str(payload.get("mode", "")).strip()
        invalid_reasons: list[str] = []
        if not text:
            invalid_reasons.append("empty_text")
        if mode != "landing":
            invalid_reasons.append("mode_mismatch")
        if text == latest_assistant:
            invalid_reasons.append("duplicate_with_latest_assistant")
        if len(text) > 80:
            invalid_reasons.append("overlong_text")
        if text and not self._landing_has_question_semantics(text):
            invalid_reasons.append("missing_question_semantics")
        if text and not self._landing_has_gender_coverage(text):
            invalid_reasons.append("missing_gender_coverage")
        if invalid_reasons:
            text = self._fallback_landing_text()
            self._last_landing_debug = {
                "fallback_used": True,
                "fallback_reason": "invalid_landing_text",
                "invalid_reasons": ",".join(invalid_reasons),
            }
        return text

    async def _compose_bubbles(self, *, question: str, visible_text: str) -> list[BubbleCandidate]:
        try:
            payload = await self._generate_json(
                call_name="bubble_composer",
                system_prompt=self.bubble_composer_prompt,
                user_payload={
                    "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                    "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                    "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                    "question": question,
                    "latest_user_message": self._latest_user_message(),
                    "recent_assistant_message": visible_text,
                },
                temperature=0.55,
            )
        except Exception:
            return []

        raw_candidates = payload.get("bubble_candidates", [])
        if not isinstance(raw_candidates, list):
            return []
        candidates: list[BubbleCandidate] = []
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            candidate = BubbleCandidate.from_dict(item)
            if candidate.text and candidate.text not in {existing.text for existing in candidates}:
                candidates.append(candidate)
            if len(candidates) >= MAX_BUBBLES:
                break
        return candidates

    async def _generate_json(
        self,
        *,
        call_name: str,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        payload_text = dump_json(user_payload)
        retry_count = 0

        def observer(*, attempt: int, error: Exception) -> None:
            nonlocal retry_count
            retry_count = max(retry_count, attempt)

        started = time.perf_counter()
        client = self.dossier_llm if call_name == "dossier_updater" else self.llm
        try:
            result = await client.generate_json(
                payload_text,
                system_prompt=system_prompt,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
                observer=observer,
            )
        except Exception as exc:
            self._llm_observations.append(
                {
                    "call_name": call_name,
                    "payload_chars": len(payload_text),
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                    "retry_count": retry_count,
                    "fallback_used": False,
                    "status": "error",
                    "error": str(exc),
                }
            )
            raise

        self._llm_observations.append(
            {
                "call_name": call_name,
                "payload_chars": len(payload_text),
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "retry_count": retry_count,
                "fallback_used": False,
                "status": "ok",
            }
        )
        return result

    def _compose_dossier_updater_prompt(self) -> str:
        dimension_menu = self.dimension_registry.render_prompt_menu()
        return (
            load_text(PROMPTS_DIR / "dossier_updater_system_prompt.md")
            + "\n\n<known_dimensions>\n"
            + dimension_menu
            + "\n</known_dimensions>"
        )

    def _build_turn_payload(
        self,
        *,
        turn: int,
        question: str,
        bubble_candidates: list[BubbleCandidate],
        update_status: DossierUpdateStatus,
        follow_up_signal: str,
    ) -> dict[str, Any]:
        return {
            "turn": max(turn, 1),
            "question": question,
            "bubble_candidates": [candidate.to_dict() for candidate in bubble_candidates],
            "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
            "dossier_update_status": update_status,
            "follow_up_signal": follow_up_signal if follow_up_signal == "mirror_rejected" else "",
        }

    def _compose_assistant_context_entry(self, visible_text: str, question: str) -> str:
        parts = [segment.strip() for segment in (visible_text, question) if segment and segment.strip()]
        return "\n".join(parts)

    def _begin_llm_observations(self) -> None:
        self._llm_observations = []

    def _consume_llm_observations(self) -> list[dict[str, Any]]:
        observations = [dict(item) for item in self._llm_observations]
        self._llm_observations = []
        return observations

    def _build_dossier_updater_payload(self, previous: TwinDossier) -> dict[str, Any]:
        routing_snapshot = previous.routing_snapshot.to_dict()
        routing_snapshot.pop("untouched", None)

        payload = {
            "previous_world_dossier": previous.world_dossier.to_dict(),
            "previous_player_dossier": previous.player_dossier.to_dict(),
            "previous_routing_snapshot": routing_snapshot,
            "previous_scope_state": previous.scope_state.to_dict(),
            "latest_user_message": self._latest_user_message(),
            "last_assistant_prompt": self._last_assistant_prompt(),
            "current_phase": self.controller.phase.value,
            "current_turn_index": self.controller.turn + 1,
            "updater_mode": self._dossier_update_mode(),
        }
        previous_user_message = self._previous_user_message()
        if previous_user_message:
            payload["previous_user_message"] = previous_user_message
        return payload

    def _recent_context(self, *, limit: int) -> list[dict[str, str]]:
        if limit <= 0:
            return []
        return [dict(message) for message in self.messages[-limit:]]

    def _latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.get("role") == "user":
                return str(message.get("content", "")).strip()
        return ""

    def _last_assistant_prompt(self) -> str:
        for message in reversed(self.messages[:-1]):
            if message.get("role") == "assistant":
                return str(message.get("content", "")).strip()
        return ""

    def _previous_user_message(self) -> str:
        seen_latest = False
        for message in reversed(self.messages):
            if message.get("role") != "user":
                continue
            content = str(message.get("content", "")).strip()
            if not seen_latest:
                seen_latest = True
                continue
            return content
        return ""

    def _serialize_landing_payload(self, payload: dict[str, Any]) -> str:
        user_gender = str(payload.get("user_gender", "")).strip()
        avatar_gender = str(payload.get("avatar_gender", "")).strip()
        name_mode = str(payload.get("name_mode", "generated")).strip()
        if name_mode == "custom":
            custom_name = str(payload.get("custom_name", "")).strip()
            return f"我的性别是{user_gender}，主角性别是{avatar_gender}，主角名字由我命名为{custom_name}。"
        return f"我的性别是{user_gender}，主角性别是{avatar_gender}，主角名字由世界提供。"

    def _normalize_avatar_gender(self, value: str) -> str:
        lowered = value.strip().lower()
        if lowered in {"男", "male", "man", "m"}:
            return "male"
        if lowered in {"女", "female", "woman", "f"}:
            return "female"
        if lowered in {"其他", "世界提供", "other", "unknown"}:
            return "unknown"
        return "unknown"

    def _can_conservatively_reuse(self, dossier: TwinDossier) -> bool:
        return any(
            [
                dossier.world_dossier.world_premise,
                dossier.player_dossier.fantasy_vector,
                dossier.routing_snapshot.confirmed,
                dossier.routing_snapshot.exploring,
                dossier.routing_snapshot.excluded,
                dossier.routing_snapshot.untouched,
            ]
        )

    def _normalize_twin_dossier(
        self,
        dossier: TwinDossier,
        *,
        updater_mode: str,
        previous: TwinDossier | None = None,
    ) -> TwinDossier:
        dossier.routing_snapshot = self._normalize_routing_snapshot(dossier.routing_snapshot)
        dossier.scope_state = self._normalize_scope_state(
            dossier.scope_state,
            updater_mode=updater_mode,
            previous=previous.scope_state if previous else None,
            dossier=dossier,
        )
        if updater_mode == "bootstrap":
            dossier = self._apply_bootstrap_guardrails(dossier)
        elif updater_mode == "stabilize":
            dossier = self._apply_stabilize_guardrails(dossier, previous=previous)
        return dossier

    def _dossier_update_mode(self) -> str:
        if self.controller.turn <= 1:
            return "bootstrap"
        if self.controller.turn <= 3:
            return "refine"
        return "stabilize"

    def _apply_bootstrap_guardrails(self, dossier: TwinDossier) -> TwinDossier:
        user_message = self._latest_user_message()
        lowered = user_message.lower()

        world = dossier.world_dossier
        player = dossier.player_dossier
        snapshot = dossier.routing_snapshot

        volatile_bootstrap_dims = {
            "dim:power_progression",
            "dim:combat_rules",
            "dim:ability_loot",
            "dim:skill_shop",
            "dim:command_friction",
        }
        demoted = [
            item for item in snapshot.confirmed if item in volatile_bootstrap_dims and item not in snapshot.excluded
        ]
        if demoted:
            snapshot.confirmed = [item for item in snapshot.confirmed if item not in demoted]
            snapshot.exploring = list(dict.fromkeys([*demoted, *snapshot.exploring]))

        if world.world_premise:
            world.world_premise = self._soften_bootstrap_world_premise(world.world_premise)
        if player.fantasy_vector:
            player.fantasy_vector = self._soften_bootstrap_fantasy_vector(player.fantasy_vector)
        if player.taste_bias and not any(token in user_message for token in ("爽", "热血", "燃", "轻松", "压抑", "冷硬", "克制")):
            player.taste_bias = ""
        if player.emotional_seed and not any(
            token in lowered for token in ("自由", "翻身", "不认命", "认可", "复仇", "爽", "压迫", "掌控")
        ):
            player.emotional_seed = ""
        return dossier

    def _apply_stabilize_guardrails(
        self,
        dossier: TwinDossier,
        *,
        previous: TwinDossier | None,
    ) -> TwinDossier:
        snapshot = dossier.routing_snapshot
        previous_confirmed = set(previous.routing_snapshot.confirmed if previous else [])
        historical_support = self._historical_routing_support_counts()

        retained_confirmed: list[str] = []
        demoted: list[str] = []
        for item in snapshot.confirmed:
            if item in previous_confirmed or historical_support.get(item, 0) >= 4:
                retained_confirmed.append(item)
            else:
                demoted.append(item)

        snapshot.confirmed = list(dict.fromkeys(retained_confirmed))
        snapshot.exploring = [
            item
            for item in dict.fromkeys([*demoted, *snapshot.exploring])
            if item not in snapshot.confirmed and item not in snapshot.excluded
        ]
        snapshot.untouched = [item for item in snapshot.untouched if item not in snapshot.confirmed]

        if demoted:
            dossier.change_log.newly_confirmed = [
                item for item in dossier.change_log.newly_confirmed if item not in demoted
            ]
        return dossier

    def _normalize_scope_state(
        self,
        scope_state: ScopeState,
        *,
        updater_mode: str,
        previous: ScopeState | None,
        dossier: TwinDossier,
    ) -> ScopeState:
        normalized = ScopeState.from_dict(scope_state.to_dict())
        normalized.unresolved_foundations = [
            item for item in normalized.unresolved_foundations if item in ALLOWED_FOUNDATION_GAPS
        ]

        if normalized.primary_scope == "unset":
            normalized.scope_locked = False
            normalized.primary_anchor = "self"
            normalized.reason = "fallback"
            return normalized

        if normalized.primary_scope == "macro" and normalized.primary_anchor != "system":
            normalized.primary_scope = "meso"
            normalized.primary_anchor = "group"
            normalized.reason = "fallback"

        if updater_mode == "bootstrap" and self.controller.turn + 1 <= 1:
            if normalized.primary_scope == "macro" and (
                normalized.reason != "user_explicit"
                or not self._has_explicit_system_need(self._latest_user_message())
            ):
                normalized = self._fallback_scope_state(previous)

        if normalized.primary_scope == "macro" and normalized.reason != "user_explicit":
            if "missing_world_top_cover" not in normalized.unresolved_foundations and updater_mode != "stabilize":
                normalized.primary_scope = "meso"
                if normalized.primary_anchor == "system":
                    normalized.primary_anchor = "group"
                normalized.reason = "fallback"

        demoted_scope = self._scope_demotion_from_evidence(dossier, previous=previous)
        if normalized.primary_scope == "macro" and demoted_scope is not None:
            normalized.primary_scope = demoted_scope.primary_scope
            normalized.primary_anchor = demoted_scope.primary_anchor
            normalized.scope_locked = demoted_scope.scope_locked
            normalized.reason = demoted_scope.reason
            normalized.unresolved_foundations = [
                item
                for item in normalized.unresolved_foundations
                if item not in {"missing_role_position", "missing_group_context"}
            ]

        if normalized.reason == "fallback" and normalized.primary_scope == "macro":
            normalized.scope_locked = False

        return normalized

    def _fallback_scope_state(self, previous: ScopeState | None) -> ScopeState:
        if previous and previous.primary_scope != "unset":
            return ScopeState.from_dict(previous.to_dict())
        return ScopeState(
            primary_scope="unset",
            primary_anchor="self",
            scope_locked=False,
            reason="fallback",
            unresolved_foundations=[],
        )

    def _landing_has_question_semantics(self, text: str) -> bool:
        lowered = text.strip().lower()
        if "?" in lowered or "？" in text:
            return True
        question_tokens = (
            "最后两个问题",
            "什么",
            "吗",
            "是否",
            "希望",
            "请选择",
            "告诉我",
        )
        return any(token in text for token in question_tokens)

    def _landing_has_gender_coverage(self, text: str) -> bool:
        user_tokens = ("你本人", "你本人的性别", "你的性别", "本人性别", "本人")
        avatar_tokens = ("化身", "进入这个世界", "角色性别", "希望是什么性别", "avatar")
        return any(token in text for token in user_tokens) and any(token in text for token in avatar_tokens)

    def _has_explicit_system_need(self, text: str) -> bool:
        lowered = text.strip().lower()
        if not lowered:
            return False
        system_focus_tokens = (
            "制度",
            "秩序",
            "文明",
            "世界怎么运转",
            "城市怎么运转",
            "系统如何运行",
            "规则本身",
            "权力结构",
            "社会结构",
            "运转逻辑",
        )
        return any(token in text for token in system_focus_tokens)

    def _scope_demotion_from_evidence(
        self,
        dossier: TwinDossier,
        *,
        previous: ScopeState | None,
    ) -> ScopeState | None:
        evidence_text = "\n".join(
            [
                self._latest_user_message(),
                dossier.player_dossier.fantasy_vector,
                dossier.player_dossier.emotional_seed,
                dossier.world_dossier.scene_anchor,
                dossier.world_dossier.tension_guess,
                dossier.world_dossier.world_premise,
                *dossier.world_dossier.open_threads,
                *dossier.player_dossier.soft_signals.notable_phrasing,
            ]
        )
        relationship_tokens = (
            "关系",
            "喜欢",
            "恋",
            "亲密",
            "室友",
            "搭档",
            "朋友",
            "学长",
            "学姐",
            "学弟",
            "学妹",
            "同桌",
            "告白",
        )
        group_tokens = (
            "班级",
            "宿舍",
            "社团",
            "学生会",
            "学院",
            "组织",
            "队伍",
            "项目组",
            "门派",
            "公司",
            "家族",
        )
        role_tokens = (
            "新生",
            "学生",
            "快递员",
            "记者",
            "医生",
            "修理师",
            "骑手",
            "实习生",
            "老师",
            "研究生",
            "邮差",
            "社员",
            "社长",
            "成员",
            "收件人",
        )

        if any(token in evidence_text for token in relationship_tokens):
            return ScopeState(
                primary_scope="micro",
                primary_anchor="relationship",
                scope_locked=False,
                reason="fallback",
                unresolved_foundations=[],
            )
        if any(token in evidence_text for token in group_tokens):
            return ScopeState(
                primary_scope="meso",
                primary_anchor="group",
                scope_locked=False,
                reason="fallback",
                unresolved_foundations=[],
            )
        if any(token in evidence_text for token in role_tokens):
            return ScopeState(
                primary_scope="micro",
                primary_anchor="self",
                scope_locked=False,
                reason="fallback",
                unresolved_foundations=[],
            )
        if previous and previous.primary_scope in {"micro", "meso"}:
            return ScopeState.from_dict(previous.to_dict())
        return None

    def _routing_support_counts(self, current_snapshot) -> dict[str, int]:
        counts: dict[str, int] = {}
        for snapshot in [*self.controller.history, current_snapshot.to_dict()]:
            for item in snapshot.get("confirmed", []):
                counts[item] = counts.get(item, 0) + 2
            for item in snapshot.get("exploring", []):
                counts[item] = counts.get(item, 0) + 1
        return counts

    def _historical_routing_support_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for snapshot in self.controller.history:
            for item in snapshot.get("confirmed", []):
                counts[item] = counts.get(item, 0) + 2
            for item in snapshot.get("exploring", []):
                counts[item] = counts.get(item, 0) + 1
        return counts

    def _normalize_compile_output(self, compile_output: CompileOutput) -> CompileOutput:
        snapshot = self.twin_dossier.routing_snapshot
        support_counts = self._routing_support_counts(snapshot)

        confirmed = list(dict.fromkeys([*compile_output.confirmed_dimensions, *snapshot.confirmed]))
        if not confirmed:
            promoted = [
                item
                for item in snapshot.exploring
                if support_counts.get(item, 0) >= 2 and item not in snapshot.excluded
            ]
            confirmed = promoted[:2]

        excluded = [
            item
            for item in dict.fromkeys([*compile_output.excluded_dimensions, *snapshot.excluded])
            if item not in confirmed
        ]

        allowed_emergent = [item for item in [*snapshot.untouched, *snapshot.exploring] if item not in confirmed and item not in excluded]
        emergent_seed = [item for item in compile_output.emergent_dimensions if item in allowed_emergent]
        emergent = list(dict.fromkeys([*emergent_seed, *allowed_emergent]))[:4]

        compile_output.confirmed_dimensions = confirmed
        compile_output.excluded_dimensions = excluded
        compile_output.emergent_dimensions = emergent
        return compile_output

    def _fallback_landing_text(self) -> str:
        return "最后两个问题。你本人的性别是什么？你想进入这个世界时，化身希望是什么性别？"

    def _soften_bootstrap_world_premise(self, text: str) -> str:
        softened = text.strip()
        softened = softened.replace("主角追求成为", "带有")
        softened = softened.replace("以大剑仙为核心", "以剑修意象为强烈核心")
        softened = softened.replace("主角", "这个世界")
        return softened

    def _soften_bootstrap_fantasy_vector(self, text: str) -> str:
        softened = text.strip()
        replacements = {
            "成为大剑仙，掌握御剑飞行和强大剑术。": "靠近剑修/大剑仙那种位置感，但具体身份与起点还未定。",
            "成为": "靠近",
            "站在": "接近",
            "顶端": "高处",
            "最强": "更有分量",
            "无敌": "不再轻易被压住",
        }
        for source, target in replacements.items():
            softened = softened.replace(source, target)
        return softened

    def _normalize_routing_snapshot(self, snapshot):
        known_dimensions = [dimension.id for dimension in self.dimension_registry.dimensions]
        known_set = set(known_dimensions)

        confirmed = list(dict.fromkeys(snapshot.confirmed))
        excluded = [item for item in dict.fromkeys(snapshot.excluded) if item not in confirmed]
        exploring = [
            item
            for item in dict.fromkeys(snapshot.exploring)
            if item not in confirmed and item not in excluded
        ]
        touched_known = {item for item in [*confirmed, *excluded, *exploring] if item in known_set}
        provided_untouched = [
            item for item in dict.fromkeys(snapshot.untouched) if item in known_set and item not in touched_known
        ]
        untouched = provided_untouched or [item for item in known_dimensions if item not in touched_known]

        snapshot.confirmed = confirmed
        snapshot.excluded = excluded
        snapshot.exploring = exploring
        snapshot.untouched = untouched
        return snapshot

    def _classify_mirror_feedback(self, user_message: str) -> str:
        lowered = user_message.strip().lower()
        if any(token in lowered for token in ("推门", "yes", "correct", "exactly", "对", "没错", "可以", "就这")):
            return "confirm"
        return "reject"
