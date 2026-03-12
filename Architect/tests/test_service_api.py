from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from Architect.api import create_app
from Architect.api_models import BackendPhase, GenerateRequest, InterviewMessageRequest
from Architect.service import ArchitectService, ArchitectServiceError
from Architect.session_store import InMemorySessionStore


class ScriptedLLMClient:
    def __init__(self, *, json_responses: list[dict], generate_responses: list[str] | None = None) -> None:
        self.json_responses = list(json_responses)
        self.generate_responses = list(generate_responses or [])

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        raise AssertionError("chat() is not used in vNext tests.")

    async def generate(self, *, system_prompt, user_msg, temperature=0.7, response_format=None) -> str:
        if not self.generate_responses:
            raise AssertionError("No scripted generate response left.")
        return self.generate_responses.pop(0)

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict:
        if not self.json_responses:
            raise AssertionError("No scripted JSON response left.")
        return self.json_responses.pop(0)


class ServiceAndApiTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.llm = ScriptedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:social_friction"],
                        "exploring": [],
                        "excluded": [],
                        "untouched": ["dim:quest_system", "dim:intimacy"],
                    },
                    "world_dossier": {
                        "world_premise": "这是一个门阀森严的都市世界。",
                        "tension_guess": "上位秩序压着低位者。",
                        "scene_anchor": "高墙下的人抬头看向墙后。",
                        "open_threads": ["墙后掌权者是谁"],
                        "soft_signals": {"notable_imagery": ["高墙"], "unstable_hypotheses": []},
                    },
                    "player_dossier": {
                        "fantasy_vector": "从低位向上翻身的人。",
                        "emotional_seed": "被轻视后翻盘。",
                        "taste_bias": "压抑、克制。",
                        "language_register": "有画面感。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["门阀森严"],
                            "subtext_hypotheses": [],
                            "style_notes": "冷硬。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": ["dim:social_friction"],
                        "newly_rejected": [],
                        "needs_follow_up": ["墙后掌权者是谁"],
                    },
                },
                {"mode": "mirror", "mirror_text": "城墙上的人把秩序写成了血统，而你站在城下。"},
                {"mode": "landing", "visible_text": "最后两个问题。你的性别？化身的性别？", "question": "最后两个问题。"},
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:social_friction"],
                        "exploring": [],
                        "excluded": [],
                        "untouched": ["dim:quest_system", "dim:intimacy"],
                    },
                    "world_dossier": {
                        "world_premise": "这是一个门阀森严的都市世界。",
                        "tension_guess": "上位秩序压着低位者。",
                        "scene_anchor": "高墙下的人抬头看向墙后。",
                        "open_threads": [],
                        "soft_signals": {"notable_imagery": ["高墙"], "unstable_hypotheses": []},
                    },
                    "player_dossier": {
                        "fantasy_vector": "从低位向上翻身的人。",
                        "emotional_seed": "被轻视后翻盘。",
                        "taste_bias": "压抑、克制。",
                        "language_register": "有画面感。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["门阀森严"],
                            "subtext_hypotheses": [],
                            "style_notes": "冷硬。",
                        },
                    },
                    "change_log": {"newly_confirmed": [], "newly_rejected": [], "needs_follow_up": []},
                },
                {
                    "confirmed_dimensions": ["dim:social_friction"],
                    "emergent_dimensions": ["dim:quest_system", "dim:intimacy"],
                    "excluded_dimensions": [],
                    "narrative_briefing": "主角从城下起步，在门阀秩序里寻找翻身机会。",
                    "player_profile": "玩家偏好写实、压抑、阶层冲突清晰的成长叙事。",
                },
                {
                    "tone_primary": "写实",
                    "tone_secondary": "压抑",
                    "content_ceiling": "PG-13",
                    "humor_density": "严肃零幽默",
                    "sensory_smell_example": "潮湿墙根混着铁锈的气味",
                    "sensory_sound_example": "城门齿轮缓慢咬合的摩擦声",
                    "tone_filter": "冷硬而克制",
                    "ignorance_reaction": "Mockery",
                },
            ],
            generate_responses=[
                "把每一次寒暄都写成身份试探。",
            ],
        )
        self.service = ArchitectService(
            llm_client=self.llm,
            session_store=InMemorySessionStore(),
            conductor=AsyncSafeConductor(),
            result_packager=AsyncSafePackager(),
        )

    async def test_service_runs_vnext_flow_and_reuses_frozen_package(self) -> None:
        opening = await self.service.start_interview()
        self.assertEqual(opening.phase, BackendPhase.INTERVIEWING)

        mirror = await self.service.submit_interview_message(
            InterviewMessageRequest(
                session_id=opening.session_id,
                message="我想要一个门阀森严、普通人很难翻身的都市世界。",
            )
        )
        self.assertEqual(mirror.phase, BackendPhase.MIRROR)

        landing = await self.service.submit_interview_message(
            InterviewMessageRequest(session_id=opening.session_id, mirror_action="confirm")
        )
        self.assertEqual(landing.phase, BackendPhase.LANDING)

        completed = await self.service.submit_interview_message(
            InterviewMessageRequest(session_id=opening.session_id, message="男，化身也是男。")
        )
        self.assertEqual(completed.phase, BackendPhase.COMPLETE)
        record = self.service.session_store.get(opening.session_id)
        assert record is not None
        self.assertIsNotNone(record.compile_output)
        self.assertIsNotNone(record.frozen_compile_package)

        generated = await self.service.generate_world(GenerateRequest(session_id=opening.session_id))

        self.assertIn("把每一次寒暄都写成身份试探。", generated.system_prompt)
        self.assertEqual(generated.blueprint.confirmed_dimensions, ["dim:social_friction"])

    async def test_service_reports_missing_session(self) -> None:
        with self.assertRaises(ArchitectServiceError) as context:
            await self.service.submit_interview_message(
                InterviewMessageRequest(session_id="missing", message="hello")
            )
        self.assertEqual(context.exception.code, "session_expired")

    async def test_api_routes_wrap_success_and_service_errors(self) -> None:
        stub_service = AsyncMock()
        stub_service.start_interview.return_value = {
            "session_id": "session-1",
            "phase": "interviewing",
            "message": "opening",
            "raw_payload": None,
        }
        stub_service.submit_interview_message.return_value = {
            "phase": "mirror",
            "message": "mirror text",
            "raw_payload": None,
        }
        stub_service.generate_world.side_effect = ArchitectServiceError(
            code="generate_failed",
            message="upstream timeout",
            retryable=True,
            status_code=502,
        )

        client = TestClient(create_app(stub_service))

        start_response = client.post("/api/interview/start")
        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(start_response.json()["session_id"], "session-1")

        message_response = client.post(
            "/api/interview/message",
            json={"session_id": "session-1", "mirror_action": "confirm"},
        )
        self.assertEqual(message_response.status_code, 200)
        self.assertEqual(message_response.json()["phase"], "mirror")

        generate_response = client.post("/api/generate", json={"session_id": "session-1"})
        self.assertEqual(generate_response.status_code, 502)
        self.assertEqual(generate_response.json()["error"]["code"], "generate_failed")

    async def test_api_wraps_validation_errors_with_error_response(self) -> None:
        stub_service = AsyncMock()
        client = TestClient(create_app(stub_service))

        invalid_response = client.post("/api/interview/message", json={"session_id": "session-1"})

        self.assertEqual(invalid_response.status_code, 422)
        self.assertEqual(invalid_response.json()["error"]["code"], "validation_error")
        self.assertFalse(invalid_response.json()["error"]["retryable"])


class AsyncSafeConductor:
    def build_manifest(self, compile_output):
        from Architect.conductor import Conductor

        return Conductor().build_manifest(compile_output)


class AsyncSafePackager:
    def build_blueprint(self, *, compile_output, manifest):
        from Architect.result_packager import ResultPackager

        return ResultPackager().build_blueprint(compile_output=compile_output, manifest=manifest)


if __name__ == "__main__":
    unittest.main()
