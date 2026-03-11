from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from Architect.api import create_app
from Architect.api_models import (
    BackendPhase,
    BlueprintSummary,
    ForgeModuleSummary,
    GenerateRequest,
    InterviewArtifactsModel,
    InterviewMessageRequest,
)
from Architect.conductor import ForgeManifest
from Architect.interviewer import InterviewArtifacts
from Architect.service import ArchitectService, ArchitectServiceError
from Architect.session_store import InMemorySessionStore


class ScriptedLLMClient:
    def __init__(
        self,
        *,
        chat_responses: list[str] | None = None,
        generate_responses: list[str] | None = None,
    ) -> None:
        self.chat_responses = list(chat_responses or [])
        self.generate_responses = list(generate_responses or [])

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        if not self.chat_responses:
            raise AssertionError("No scripted chat response left.")
        return self.chat_responses.pop(0)

    async def generate(self, *, system_prompt, user_msg, temperature=0.7, response_format=None) -> str:
        if not self.generate_responses:
            raise AssertionError("No scripted generate response left.")
        return self.generate_responses.pop(0)

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict:
        raise AssertionError("JSON generation is not used in this test.")


class ServiceAndApiTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.llm = ScriptedLLMClient(
            chat_responses=[
                """<<VISIBLE>>
你已经站在高墙下了。我只想再知道一点点，谁在墙后掌握生死？
<<END_VISIBLE>>
<<SYSTEM_JSON>>
{"turn": 1, "question": "谁在墙后掌握生死？", "suggested_tags": ["城墙下的灰", "门阀的余烬"], "routing_snapshot": {"confirmed": ["dim:social_friction"], "exploring": [], "excluded": [], "untouched": ["dim:intimacy", "dim:quest_system"]}, "vibe_flavor": "grim_urban"}
<<END_SYSTEM_JSON>>"""
            ],
            generate_responses=[
                "城墙上的人把秩序写成了血统，而你站在城下。",
                "最后两个问题。你的性别？化身的性别？",
                """{
                  "confirmed_dimensions": ["dim:social_friction"],
                  "emergent_dimensions": ["dim:quest_system", "dim:intimacy"],
                  "excluded_dimensions": [],
                  "narrative_briefing": "主角从城墙下起步，在门阀秩序里寻找翻身机会。世界的核心冲突来自阶层与资源垄断。",
                  "player_profile": "玩家偏好写实、压抑、阶层冲突清晰的成长叙事。"
                }""",
            ],
        )
        self.service = ArchitectService(
            llm_client=self.llm,
            session_store=InMemorySessionStore(),
            conductor=AsyncSafeConductor(),
            result_packager=AsyncSafePackager(),
        )

    async def test_service_accepts_structured_mirror_action_and_reuses_stored_artifacts(self) -> None:
        opening = await self.service.start_interview()
        self.assertEqual(opening.phase, BackendPhase.INTERVIEWING)
        self.assertTrue(opening.session_id)

        mirror = await self.service.submit_interview_message(
            InterviewMessageRequest(
                session_id=opening.session_id,
                message="我想要一个门阀森严、普通人很难翻身的都市世界。",
            )
        )
        self.assertEqual(mirror.phase, BackendPhase.MIRROR)

        landing = await self.service.submit_interview_message(
            InterviewMessageRequest(
                session_id=opening.session_id,
                mirror_action="confirm",
            )
        )
        self.assertEqual(landing.phase, BackendPhase.LANDING)

        completed = await self.service.submit_interview_message(
            InterviewMessageRequest(
                session_id=opening.session_id,
                message="男，化身也是男。",
            )
        )
        self.assertEqual(completed.phase, BackendPhase.COMPLETE)
        self.assertIsNotNone(completed.artifacts)

        with (
            patch("Architect.service.Forge.execute", new=AsyncMock(return_value={"dim:social_friction": "forged"})),
            patch("Architect.service.Assembler.assemble", new=AsyncMock(return_value="FINAL PROMPT")),
        ):
            generated = await self.service.generate_world(
                GenerateRequest(session_id=opening.session_id)
            )

        self.assertEqual(generated.system_prompt, "FINAL PROMPT")
        self.assertTrue(generated.blueprint.title.startswith("主角从城墙下起步"))
        self.assertEqual(
            [item.pack_id for item in generated.blueprint.forged_modules],
            ["pack.urban.friction"],
        )

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
            "artifacts": None,
            "raw_payload": {"suggested_tags": ["a"]},
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

        generate_response = client.post(
            "/api/generate",
            json={"session_id": "session-1"},
        )
        self.assertEqual(generate_response.status_code, 502)
        self.assertEqual(generate_response.json()["error"]["code"], "generate_failed")


class AsyncSafeConductor:
    def process_interview_results(
        self,
        routing_tags: dict[str, list[str]],
        narrative_briefing: str,
        player_profile: str,
    ) -> ForgeManifest:
        from Architect.conductor import Conductor

        return Conductor().process_interview_results(routing_tags, narrative_briefing, player_profile)


class AsyncSafePackager:
    def build_blueprint_summary(
        self,
        *,
        artifacts: InterviewArtifacts,
        manifest: ForgeManifest,
        system_prompt: str,
    ) -> BlueprintSummary:
        from Architect.result_packager import ResultPackager

        return ResultPackager().build_blueprint_summary(
            artifacts=artifacts,
            manifest=manifest,
            system_prompt=system_prompt,
        )


class ApiModelValidationTestCase(unittest.TestCase):
    def test_interview_request_requires_message_or_mirror_action(self) -> None:
        with self.assertRaises(ValueError):
            InterviewMessageRequest(session_id="session-1")

    def test_generate_request_accepts_serialized_artifacts(self) -> None:
        request = GenerateRequest(
            session_id="session-1",
            artifacts=InterviewArtifactsModel(
                confirmed_dimensions=["dim:social_friction"],
                emergent_dimensions=["dim:intimacy"],
                excluded_dimensions=[],
                narrative_briefing="brief",
                player_profile="profile",
            ),
        )
        self.assertEqual(request.artifacts.confirmed_dimensions, ["dim:social_friction"])


if __name__ == "__main__":
    unittest.main()
