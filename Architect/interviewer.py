"""Stateful interview runtime for the Architect intake flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import OPENING_QUESTION, PROMPTS_DIR, extract_first_json_object, extract_tagged_block, load_text
from .interview_controller import InterviewController, InterviewPhase
from .llm_client import LLMClientProtocol

VISIBLE_START = "<<VISIBLE>>"
VISIBLE_END = "<<END_VISIBLE>>"
JSON_START = "<<SYSTEM_JSON>>"
JSON_END = "<<END_SYSTEM_JSON>>"

INTERVIEW_RESPONSE_RULES = f"""
Return the response in exactly this shape:
{VISIBLE_START}
<one natural-language reply for the user>
{VISIBLE_END}
{JSON_START}
<one JSON object for the system>
{JSON_END}
Do not use markdown fences.
""".strip()


@dataclass
class InterviewArtifacts:
    routing_tags: dict[str, list[str]]
    narrative_briefing: str
    player_profile: str


@dataclass
class InterviewStepResult:
    phase: InterviewPhase
    message: str | None = None
    artifacts: InterviewArtifacts | None = None
    raw_payload: dict[str, Any] | None = None


class Interviewer:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        *,
        controller: InterviewController | None = None,
        prompt_path: str | None = None,
    ) -> None:
        self.llm = llm_client
        self.controller = controller or InterviewController()
        self.system_prompt = load_text(prompt_path or PROMPTS_DIR / "interviewer_system_prompt.md")
        self.messages: list[dict[str, str]] = []
        self.started = False

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
            return await self._run_interview_turn()
        if self.controller.phase == InterviewPhase.MIRROR:
            return await self._handle_mirror_feedback(user_message)
        if self.controller.phase == InterviewPhase.LANDING:
            return await self._complete_interview()

        raise RuntimeError(f"Unsupported interview phase: {self.controller.phase}")

    async def _run_interview_turn(self) -> InterviewStepResult:
        raw_response = await self.llm.chat(
            self.messages,
            system_prompt=f"{self.system_prompt}\n\n{INTERVIEW_RESPONSE_RULES}",
            temperature=0.8,
        )
        visible_text, payload = self._parse_interview_response(raw_response)
        self.messages.append({"role": "assistant", "content": visible_text})

        next_phase = self.controller.process_turn(payload)
        if next_phase == InterviewPhase.INTERVIEWING:
            return InterviewStepResult(
                phase=next_phase,
                message=visible_text,
                raw_payload=payload,
            )

        phase_message = await self._generate_phase_message(next_phase)
        self.messages.append({"role": "assistant", "content": phase_message})
        return InterviewStepResult(
            phase=next_phase,
            message=phase_message,
            raw_payload=payload,
        )

    async def _handle_mirror_feedback(self, user_message: str) -> InterviewStepResult:
        disposition = self._classify_mirror_feedback(user_message)
        if disposition == "confirm":
            next_phase = self.controller.process_turn({})
            phase_message = await self._generate_phase_message(next_phase)
            self.messages.append({"role": "assistant", "content": phase_message})
            return InterviewStepResult(phase=next_phase, message=phase_message)

        if disposition == "reject":
            self.controller.phase = InterviewPhase.INTERVIEWING
            return await self._run_interview_turn()

        mirror_text = await self._generate_phase_message(InterviewPhase.MIRROR)
        self.messages.append({"role": "assistant", "content": mirror_text})
        return InterviewStepResult(phase=InterviewPhase.MIRROR, message=mirror_text)

    async def _complete_interview(self) -> InterviewStepResult:
        self.controller.process_turn({})
        instruction = (
            f"{self.system_prompt}\n\n"
            f"{self.controller.get_system_instruction()}\n"
            "Return exactly one JSON object with these keys: "
            "confirmed_dimensions, emergent_dimensions, excluded_dimensions, "
            "narrative_briefing, player_profile. No markdown fences."
        )
        raw_payload = await self.llm.generate(
            system_prompt=instruction,
            user_msg="请输出最终交付物。",
            temperature=0.4,
            response_format="json_object",
        )
        payload = extract_first_json_object(raw_payload)
        artifacts = self._build_artifacts(payload)
        return InterviewStepResult(
            phase=InterviewPhase.COMPLETE,
            artifacts=artifacts,
            raw_payload=payload,
        )

    async def _generate_phase_message(self, phase: InterviewPhase) -> str:
        instruction = self.controller.get_system_instruction()
        if phase == InterviewPhase.MIRROR:
            instruction = f"{instruction}\nReturn only the Mirror text. No JSON."
        elif phase == InterviewPhase.LANDING:
            instruction = f"{instruction}\nReturn only the landing question. No JSON."
        elif instruction is None:
            raise RuntimeError(f"No generation instruction available for phase {phase}.")

        return await self.llm.generate(
            system_prompt=f"{self.system_prompt}\n\n{instruction}",
            user_msg="继续当前阶段。",
            temperature=0.7,
        )

    def _parse_interview_response(self, raw_response: str) -> tuple[str, dict[str, Any]]:
        visible_text = extract_tagged_block(raw_response, VISIBLE_START, VISIBLE_END)
        json_block = extract_tagged_block(raw_response, JSON_START, JSON_END)

        if json_block is None:
            payload = extract_first_json_object(raw_response)
            visible_text = visible_text or raw_response.split("{", 1)[0].strip()
        else:
            payload = extract_first_json_object(json_block)
            visible_text = visible_text or ""

        if not visible_text:
            raise ValueError("Interview response did not contain a user-visible message.")
        if "routing_snapshot" not in payload:
            raise ValueError("Interview response JSON is missing routing_snapshot.")
        return visible_text, payload

    def _build_artifacts(self, payload: dict[str, Any]) -> InterviewArtifacts:
        finalized_routing = self.controller.finalize_routing()

        confirmed = payload.get("confirmed_dimensions") or finalized_routing["confirmed_dimensions"]
        emergent = list(
            dict.fromkeys(
                [*payload.get("emergent_dimensions", []), *finalized_routing["emergent_dimensions"]]
            )
        )
        excluded = payload.get("excluded_dimensions") or finalized_routing["excluded_dimensions"]

        return InterviewArtifacts(
            routing_tags={
                "confirmed_dimensions": confirmed,
                "emergent_dimensions": emergent,
                "excluded_dimensions": excluded,
            },
            narrative_briefing=str(payload.get("narrative_briefing", "")).strip(),
            player_profile=str(payload.get("player_profile", "")).strip(),
        )

    def _classify_mirror_feedback(self, user_message: str) -> str:
        lowered = user_message.strip().lower()
        if any(token in lowered for token in ("其实", "但是", "不过", "更想", "希望", "想要")):
            return "refine"
        if any(token in lowered for token in ("继续", "再聊", "再问", "重来", "不对", "不是")):
            return "reject"
        if any(token in lowered for token in ("是", "对", "没错", "可以", "就这", "推门", "yes", "correct", "exactly")):
            return "confirm"
        return "refine"

