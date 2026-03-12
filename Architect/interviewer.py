"""vNext stateful runtime: dossier update, composition, bubble generation, and compile freeze."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import OPENING_QUESTION, PROMPTS_DIR, dump_json, load_text
from .domain import (
    BubbleCandidate,
    CompileOutput,
    DossierUpdateStatus,
    FrozenCompilePackage,
    TwinDossier,
    build_assembler_context,
    build_forge_context,
)
from .dimension_registry import InterviewDimensionRegistry
from .interview_controller import InterviewController, InterviewPhase
from .llm_client import LLMClientProtocol

MAX_BUBBLES = 3


@dataclass
class InterviewStepResult:
    phase: InterviewPhase
    message: str | None = None
    raw_payload: dict[str, Any] | None = None


class Interviewer:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        *,
        controller: InterviewController | None = None,
    ) -> None:
        self.llm = llm_client
        self.controller = controller or InterviewController()
        self.dimension_registry = InterviewDimensionRegistry.load()
        self.messages: list[dict[str, str]] = []
        self.started = False

        self.twin_dossier = TwinDossier.empty()
        self.dossier_update_status: DossierUpdateStatus = "updated"
        self.follow_up_signal = ""

        self.dossier_updater_prompt = self._compose_dossier_updater_prompt()
        self.interview_composer_prompt = load_text(PROMPTS_DIR / "interview_composer_system_prompt.md")
        self.bubble_composer_prompt = load_text(PROMPTS_DIR / "bubble_composer_system_prompt.md")
        self.compile_output_prompt = load_text(PROMPTS_DIR / "compile_output_system_prompt.md")

    async def start(self) -> InterviewStepResult:
        if not self.started:
            self.started = True
            self.messages.append({"role": "assistant", "content": OPENING_QUESTION})
        return InterviewStepResult(phase=self.controller.phase, message=OPENING_QUESTION)

    async def process_user_message(self, user_message: str) -> InterviewStepResult:
        if not self.started:
            await self.start()

        if self.controller.phase == InterviewPhase.COMPLETE:
            raise RuntimeError("Interview is already complete.")

        self.messages.append({"role": "user", "content": user_message})

        if self.controller.phase == InterviewPhase.INTERVIEWING:
            return await self._handle_interview_turn(current_phase="interviewing")
        if self.controller.phase == InterviewPhase.MIRROR:
            return await self._handle_mirror_feedback(user_message)
        if self.controller.phase == InterviewPhase.LANDING:
            return await self._handle_landing_submission()

        raise RuntimeError(f"Unsupported interview phase: {self.controller.phase}")

    async def compile_output(self) -> CompileOutput:
        payload = await self._generate_json(
            system_prompt=self.compile_output_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "recent_context": self._recent_context(limit=2),
            },
            temperature=0.2,
        )
        return CompileOutput.from_dict(payload)

    def freeze_compile_package(self, compile_output: CompileOutput) -> FrozenCompilePackage:
        return FrozenCompilePackage(
            compile_output=compile_output,
            forge_context=build_forge_context(self.twin_dossier),
            assembler_context=build_assembler_context(self.twin_dossier),
        )

    async def _handle_interview_turn(self, *, current_phase: str) -> InterviewStepResult:
        if current_phase != "interviewing":
            raise RuntimeError("Only interviewing turns can trigger dossier updates.")

        update_status = await self._run_dossier_updater()
        next_phase = self.controller.process_turn(
            {"routing_snapshot": self.twin_dossier.routing_snapshot.to_dict()}
        )

        if next_phase == InterviewPhase.MIRROR:
            mirror_text = await self._compose_mirror()
            self.messages.append({"role": "assistant", "content": mirror_text})
            self.follow_up_signal = ""
            return InterviewStepResult(phase=InterviewPhase.MIRROR, message=mirror_text)

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
        )

    async def _handle_mirror_feedback(self, user_message: str) -> InterviewStepResult:
        disposition = self._classify_mirror_feedback(user_message)
        if disposition == "confirm":
            next_phase = self.controller.process_turn({})
            landing = await self._compose_landing()
            self.messages.append({"role": "assistant", "content": landing})
            return InterviewStepResult(phase=next_phase, message=landing)

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
        )

    async def _handle_landing_submission(self) -> InterviewStepResult:
        await self._run_dossier_updater()
        self.controller.process_turn({})
        return InterviewStepResult(phase=InterviewPhase.COMPLETE, message=None)

    async def _run_dossier_updater(self) -> DossierUpdateStatus:
        previous = self.twin_dossier
        payload = {
            "previous_world_dossier": previous.world_dossier.to_dict(),
            "previous_player_dossier": previous.player_dossier.to_dict(),
            "previous_routing_snapshot": previous.routing_snapshot.to_dict(),
            "recent_context": self._recent_context(limit=6),
            "latest_user_message": self._latest_user_message(),
            "current_phase": self.controller.phase.value,
        }

        last_error: Exception | None = None
        for _ in range(2):
            try:
                updated = await self._generate_json(
                    system_prompt=self.dossier_updater_prompt,
                    user_payload=payload,
                    temperature=0.15,
                )
                self.twin_dossier = self._normalize_twin_dossier(TwinDossier.from_dict(updated))
                self.dossier_update_status = "updated"
                return self.dossier_update_status
            except Exception as exc:
                last_error = exc

        if self._can_conservatively_reuse(previous):
            self.twin_dossier = previous
            self.dossier_update_status = "update_skipped"
            return self.dossier_update_status

        self.dossier_update_status = "hard_failed"
        raise ValueError(f"Dossier update failed: {last_error}") from last_error

    async def _compose_interview_response(self) -> dict[str, Any]:
        payload = await self._generate_json(
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
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
        self.messages.append({"role": "assistant", "content": visible_text})
        self.follow_up_signal = ""
        return {
            "visible_text": visible_text,
            "question": question,
            "bubble_candidates": bubbles,
        }

    async def _compose_mirror(self) -> str:
        payload = await self._generate_json(
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
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
        payload = await self._generate_json(
            system_prompt=self.interview_composer_prompt,
            user_payload={
                "world_dossier": self.twin_dossier.world_dossier.to_dict(),
                "player_dossier": self.twin_dossier.player_dossier.to_dict(),
                "routing_snapshot": self.twin_dossier.routing_snapshot.to_dict(),
                "recent_context": self._recent_context(limit=4),
                "current_phase": "landing",
                "dossier_update_status": self.dossier_update_status,
                "follow_up_signal": self.follow_up_signal,
            },
            temperature=0.45,
        )
        text = str(payload.get("visible_text") or payload.get("question") or "").strip()
        if not text:
            raise ValueError("InterviewComposer did not return landing text.")
        return text

    async def _compose_bubbles(self, *, question: str, visible_text: str) -> list[BubbleCandidate]:
        try:
            payload = await self._generate_json(
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

    async def _generate_json(self, *, system_prompt: str, user_payload: dict[str, Any], temperature: float) -> dict[str, Any]:
        return await self.llm.generate_json(
            dump_json(user_payload),
            system_prompt=system_prompt,
            temperature=temperature,
        )

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

    def _recent_context(self, *, limit: int) -> list[dict[str, str]]:
        if limit <= 0:
            return []
        return [dict(message) for message in self.messages[-limit:]]

    def _latest_user_message(self) -> str:
        for message in reversed(self.messages):
            if message.get("role") == "user":
                return str(message.get("content", "")).strip()
        return ""

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

    def _normalize_twin_dossier(self, dossier: TwinDossier) -> TwinDossier:
        dossier.routing_snapshot = self._normalize_routing_snapshot(dossier.routing_snapshot)
        return dossier

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
