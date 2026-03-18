from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from Runtime.api import create_app
from Runtime.api_models import RuntimeStartRequest, RuntimeTurnRequest
from Runtime.domain import RuntimeMessage
from Runtime.llm_client import OpenAICompatibleLLMClient
from Runtime.service import RuntimeService, RuntimeServiceError
from Runtime.store import JsonRuntimeSessionStore


class StubLLM:
    def __init__(self, responses: list[object], *, delay_seconds: float = 0.0) -> None:
        self.responses = list(responses)
        self.delay_seconds = delay_seconds
        self.calls: list[dict[str, object]] = []

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        raise NotImplementedError

    async def stream_chat(
        self,
        messages,
        *,
        system_prompt=None,
        temperature=0.7,
        response_format=None,
    ):
        self.calls.append(
            {
                "messages": messages,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "response_format": response_format,
                "stream": True,
            }
        )
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if not self.responses:
            raise RuntimeError("No stub response remaining.")
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        payload = next_response if isinstance(next_response, str) else json.dumps(next_response, ensure_ascii=False)
        chunk_size = max(1, len(payload) // 3)
        for index in range(0, len(payload), chunk_size):
            yield payload[index : index + chunk_size]

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict[str, object]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature})
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if not self.responses:
            raise RuntimeError("No stub response remaining.")
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return dict(next_response)


def _start_request() -> RuntimeStartRequest:
    return RuntimeStartRequest(
        system_prompt="You are the world.",
        title="冷光山门",
        world_summary="一个被森严剑规压住呼吸的修仙世界。",
        tone_keywords=["冷硬", "克制"],
        confirmed_dimensions=["dim:command_friction"],
        emergent_dimensions=["dim:power_progression"],
        player_profile="偏向被秩序压住、但仍想试探边界的位置感。",
    )


def _intro_response() -> dict[str, object]:
    return {
        "assistant_text": "夜风擦过山门，剑光像一条不许越线的河。",
        "turn_summary": "世界开场，规矩先于人物出现。",
        "world_state_patch": {
            "protagonist_name": "沈砚",
            "protagonist_gender": "male",
            "current_timestamp": "子时",
            "current_location": "冷光山门",
            "active_threads": ["山门禁线"],
            "status_flags": {"phase": "opening"},
        },
        "meta": {"mood": "cold"},
    }


def _turn_response(
    *,
    assistant_text: str,
    turn_summary: str,
    current_location: str = "",
    current_timestamp: str = "",
) -> dict[str, object]:
    return {
        "assistant_text": assistant_text,
        "turn_summary": turn_summary,
        "world_state_patch": {
            "current_timestamp": current_timestamp,
            "current_location": current_location,
        },
        "meta": {},
    }


class RuntimeServiceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = JsonRuntimeSessionStore(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _make_service(
        self,
        responses: list[object],
        *,
        delay_seconds: float = 0.0,
    ) -> tuple[RuntimeService, StubLLM]:
        llm = StubLLM(responses, delay_seconds=delay_seconds)
        return RuntimeService(llm_client=llm, store=self.store), llm

    def test_llm_timeout_can_be_overridden_by_env(self) -> None:
        env = {
            "RUNTIME_LLM_API_KEY": "test-key",
            "RUNTIME_LLM_BASE_URL": "https://example.com/v1",
            "RUNTIME_LLM_MODEL": "test-model",
            "RUNTIME_LLM_TIMEOUT_SECONDS": "75",
        }
        with patch.dict(os.environ, env, clear=False):
            client = OpenAICompatibleLLMClient.from_env()
        self.assertEqual(client.timeout, 75.0)

    def test_create_session_is_non_blocking_until_bootstrap(self) -> None:
        service, _ = self._make_service([_intro_response()])

        created = self._run(service.create_session(_start_request()))
        self.assertEqual(created.turn_count, 0)
        self.assertIsNone(created.intro_message)
        self.assertEqual(created.boot_status, "pending")

        stored = self.store.get(created.runtime_session_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(len(stored.messages), 0)
        self.assertEqual(stored.boot_status, "pending")

        bootstrapped = self._run(service.bootstrap_session(created.runtime_session_id))
        self.assertEqual(bootstrapped.boot_status, "ready")
        self.assertEqual(len(bootstrapped.messages), 1)
        self.assertEqual(bootstrapped.messages[0].turn_number, 0)
        self.assertEqual(bootstrapped.world_stats.protagonist_name, "沈砚")
        self.assertEqual(bootstrapped.world_stats.current_location, "冷光山门")
        self.assertGreater(bootstrapped.boot_generation_count, 0)

    def test_ready_bootstrap_is_idempotent(self) -> None:
        service, llm = self._make_service([_intro_response()])
        created = self._run(service.create_session(_start_request()))

        first = self._run(service.bootstrap_session(created.runtime_session_id))
        second = self._run(service.bootstrap_session(created.runtime_session_id))

        self.assertEqual(first.boot_status, "ready")
        self.assertEqual(second.boot_status, "ready")
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(len(second.messages), 1)

    def test_concurrent_bootstrap_singleflights_llm_call(self) -> None:
        service, llm = self._make_service([_intro_response()], delay_seconds=0.05)
        created = self._run(service.create_session(_start_request()))

        async def run_both():
            return await asyncio.gather(
                service.bootstrap_session(created.runtime_session_id),
                service.bootstrap_session(created.runtime_session_id),
            )

        first, second = self._run(run_both())
        statuses = {first.boot_status, second.boot_status}
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(statuses, {"booting", "ready"})

        stored = self.store.get(created.runtime_session_id)
        assert stored is not None
        self.assertEqual(stored.boot_status, "ready")
        self.assertEqual(len(stored.messages), 1)

    def test_failed_bootstrap_can_be_retried_manually(self) -> None:
        service, llm = self._make_service([RuntimeError("boom"), _intro_response()])
        created = self._run(service.create_session(_start_request()))

        with self.assertRaises(RuntimeServiceError) as ctx:
            self._run(service.bootstrap_session(created.runtime_session_id))
        self.assertEqual(ctx.exception.code, "bootstrap_failed")

        failed = service.get_session(created.runtime_session_id)
        self.assertEqual(failed.boot_status, "failed")
        self.assertEqual(failed.boot_error, "boom")

        retried = self._run(service.bootstrap_session(created.runtime_session_id))
        self.assertEqual(retried.boot_status, "ready")
        self.assertEqual(len(retried.messages), 1)
        self.assertEqual(len(llm.calls), 2)

    def test_existing_opening_is_not_overwritten_on_retry(self) -> None:
        service, llm = self._make_service([_intro_response(), _turn_response(assistant_text="新的开场。", turn_summary="新的开场。")])
        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))

        stored = self.store.get(created.runtime_session_id)
        assert stored is not None
        stored.boot_status = "failed"
        stored.messages[0] = RuntimeMessage(role="assistant", content="冻结的旧开场。", turn_number=0)
        self.store.save(stored)

        retried = self._run(service.bootstrap_session(created.runtime_session_id))
        self.assertEqual(retried.boot_status, "ready")
        self.assertEqual(len(retried.messages), 1)
        self.assertEqual(retried.messages[0].content, "冻结的旧开场。")
        self.assertEqual(len(llm.calls), 2)

    def test_turn_updates_recent_memories_without_extra_lorebook_call(self) -> None:
        service, llm = self._make_service(
            [
                _intro_response(),
                _turn_response(
                    assistant_text="你踏进了风雪里的长阶。",
                    turn_summary="你正式进入山门长阶。",
                    current_timestamp="寅时将尽",
                    current_location="山门长阶",
                ),
            ]
        )

        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))
        response = self._run(
            service.run_turn(
                RuntimeTurnRequest(
                    runtime_session_id=created.runtime_session_id,
                    user_action="我踏上通往山门的长阶。",
                )
            )
        )

        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(len(response.recent_memories), 1)
        self.assertEqual(response.recent_memories[0]["summary"], "你正式进入山门长阶。")
        self.assertEqual(response.world_stats.current_location, "山门长阶")

    def test_stream_turn_emits_deltas_and_final_response(self) -> None:
        service, _ = self._make_service(
            [
                _intro_response(),
                _turn_response(
                    assistant_text="你踏进了风雪里的长阶。",
                    turn_summary="你正式进入山门长阶。",
                    current_timestamp="寅时将尽",
                    current_location="山门长阶",
                ),
            ]
        )
        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))

        async def scenario():
            events = []
            async for event in service.stream_turn(
                RuntimeTurnRequest(
                    runtime_session_id=created.runtime_session_id,
                    user_action="我踏上通往山门的长阶。",
                )
            ):
                events.append(event)
            return events

        events = self._run(scenario())
        delta_events = [event for event in events if event["event"] == "assistant_delta"]
        final_event = next(event for event in events if event["event"] == "turn_complete")
        self.assertGreaterEqual(len(delta_events), 1)
        self.assertEqual(final_event["data"]["turn_count"], 1)
        self.assertEqual(final_event["data"]["assistant_message"]["content"], "你踏进了风雪里的长阶。")
        snapshot = service.get_session(created.runtime_session_id)
        self.assertEqual(snapshot.turn_count, 1)
        self.assertEqual(snapshot.world_stats.current_location, "山门长阶")

    def test_turn_prompt_uses_trimmed_state_snapshot(self) -> None:
        service, llm = self._make_service([_intro_response(), _turn_response(assistant_text="继续推进。", turn_summary="继续推进。")])
        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))
        session = self.store.get(created.runtime_session_id)
        assert session is not None
        session.state_snapshot.update(
            {
                "current_situation": "外门规训压迫感持续增强。",
                "active_threads": ["进入山门"],
                "important_assets": ["残缺令牌"],
                "status_flags": {"should_not": "appear"},
                "last_scene": "不应注入 prompt",
            }
        )
        self.store.save(session)

        self._run(
            service.run_turn(
                RuntimeTurnRequest(
                    runtime_session_id=created.runtime_session_id,
                    user_action="我继续观察守门弟子的反应。",
                )
            )
        )
        turn_prompt = str(llm.calls[-1]["prompt"])
        self.assertIn("current_situation", turn_prompt)
        self.assertIn("残缺令牌", turn_prompt)
        self.assertNotIn("status_flags", turn_prompt)
        self.assertNotIn("last_scene", turn_prompt)

    def test_lorebook_extraction_triggers_on_fifth_turn(self) -> None:
        responses: list[object] = [_intro_response()]
        for index in range(1, 6):
            responses.append(
                {
                    "assistant_text": f"第{index}回合叙事。",
                    "turn_summary": f"第{index}回合变化。",
                    "world_state_patch": {"active_threads": [f"thread-{index}"]},
                    "meta": {},
                }
            )
        responses.append(
            {
                "entries": [
                    {
                        "type": "character",
                        "name": "林墨",
                        "aliases": ["墨师兄"],
                        "keywords": ["林墨", "墨师兄"],
                        "description": "守着山门旧规的人。",
                        "status": "active",
                    }
                ]
            }
        )

        service, _ = self._make_service(responses)

        async def scenario():
            created = await service.create_session(_start_request())
            await service.bootstrap_session(created.runtime_session_id)
            response = None
            for turn in range(1, 5):
                response = await service.run_turn(
                    RuntimeTurnRequest(
                        runtime_session_id=created.runtime_session_id,
                        user_action=f"执行动作 {turn}",
                    )
                )
                self.assertEqual(response.lorebook_update_stats.total, 0)
            response = await service.run_turn(
                RuntimeTurnRequest(
                    runtime_session_id=created.runtime_session_id,
                    user_action="执行动作 5",
                )
            )
            await service.wait_for_lorebook_jobs(created.runtime_session_id)
            return created, response

        created, response = self._run(scenario())
        self.assertEqual(response.turn_count, 5)
        self.assertEqual(response.lorebook_update_stats.inserted, 0)
        self.assertEqual(len(response.lorebook), 0)
        snapshot = service.get_session(created.runtime_session_id)
        debug = service.get_session_debug(created.runtime_session_id)
        self.assertEqual(len(snapshot.lorebook), 1)
        self.assertEqual(debug.last_lorebook_job_status, "ok")
        self.assertEqual(debug.last_lorebook_job_turn, 5)

    def test_lorebook_failure_does_not_fail_turn(self) -> None:
        responses: list[object] = [_intro_response()]
        for index in range(1, 6):
            responses.append(
                {
                    "assistant_text": f"第{index}回合叙事。",
                    "turn_summary": f"第{index}回合变化。",
                    "world_state_patch": {"active_threads": [f"thread-{index}"]},
                    "meta": {},
                }
            )
        responses.append(RuntimeError("extract down"))

        service, _ = self._make_service(responses)

        async def scenario():
            created = await service.create_session(_start_request())
            await service.bootstrap_session(created.runtime_session_id)
            response = None
            for turn in range(1, 6):
                response = await service.run_turn(
                    RuntimeTurnRequest(
                        runtime_session_id=created.runtime_session_id,
                        user_action=f"执行动作 {turn}",
                    )
                )
            await service.wait_for_lorebook_jobs(created.runtime_session_id)
            return created, response

        created, response = self._run(scenario())
        self.assertEqual(response.turn_count, 5)
        self.assertEqual(response.assistant_message.content, "第5回合叙事。")
        snapshot = service.get_session(created.runtime_session_id)
        debug = service.get_session_debug(created.runtime_session_id)
        self.assertEqual(len(snapshot.lorebook), 0)
        self.assertEqual(debug.last_lorebook_job_status, "failed")
        assert debug.last_lorebook_error is not None
        self.assertEqual(debug.last_lorebook_error.code, "lorebook_extract_failed")
        self.assertEqual(debug.last_lorebook_error.turn_number, 5)

    def test_relevant_lorebook_entries_are_injected(self) -> None:
        service, llm = self._make_service(
            [
                _intro_response(),
                _turn_response(assistant_text="林墨抬眼看你。", turn_summary="你和林墨重新碰面。"),
            ]
        )
        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))
        session = self.store.get(created.runtime_session_id)
        assert session is not None
        session.lorebook.append(
            __import__("Runtime.domain", fromlist=["LorebookEntry"]).LorebookEntry.create(
                entry_type="character",
                name="林墨",
                aliases=["墨师兄"],
                keywords=["林墨", "墨师兄", "山门守规人"],
                description="守着山门旧规的人。",
                turn_number=1,
            )
        )
        self.store.save(session)

        self._run(
            service.run_turn(
                RuntimeTurnRequest(
                    runtime_session_id=created.runtime_session_id,
                    user_action="我先试探林墨会不会放我过山门。",
                )
            )
        )
        self.assertGreaterEqual(len(llm.calls), 2)
        turn_prompt = str(llm.calls[-1]["prompt"])
        self.assertIn("林墨", turn_prompt)
        self.assertIn("守着山门旧规的人", turn_prompt)

    def test_run_turn_rejects_non_ready_boot_states_with_409(self) -> None:
        service, _ = self._make_service([_intro_response()])
        created = self._run(service.create_session(_start_request()))
        client = TestClient(create_app(service))

        for boot_status in ("pending", "booting", "failed"):
            session = self.store.get(created.runtime_session_id)
            assert session is not None
            session.boot_status = boot_status
            session.messages = []
            self.store.save(session)
            response = client.post(
                "/api/runtime/turn",
                json={
                    "runtime_session_id": created.runtime_session_id,
                    "user_action": "我向前一步。",
                },
            )
            self.assertEqual(response.status_code, 409)

    def test_debug_endpoint_exposes_last_turn_error(self) -> None:
        service, _ = self._make_service([_intro_response(), RuntimeError("provider down")])
        created = self._run(service.create_session(_start_request()))
        self._run(service.bootstrap_session(created.runtime_session_id))
        client = TestClient(create_app(service))

        response = client.post(
            "/api/runtime/turn",
            json={
                "runtime_session_id": created.runtime_session_id,
                "user_action": "我试着继续往前走。",
            },
        )
        self.assertEqual(response.status_code, 502)

        debug = client.get(f"/api/runtime/session/{created.runtime_session_id}/debug")
        self.assertEqual(debug.status_code, 200)
        payload = debug.json()
        self.assertEqual(payload["last_turn_error"]["code"], "generate_failed")
        self.assertEqual(payload["last_turn_error"]["turn_number"], 1)
        self.assertEqual(payload["last_turn_error"]["user_action"], "我试着继续往前走。")

    def test_api_lists_saved_worlds(self) -> None:
        service, _ = self._make_service([_intro_response()])
        created = self._run(service.create_session(_start_request()))
        client = TestClient(create_app(service))
        self.assertEqual(created.boot_status, "pending")
        response = client.get("/api/runtime/worlds")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "冷光山门")
        self.assertEqual(response.json()[0]["display_title"], "")

    def test_api_updates_display_title(self) -> None:
        service, _ = self._make_service([_intro_response()])
        created = self._run(service.create_session(_start_request()))
        client = TestClient(create_app(service))

        response = client.patch(
            f"/api/runtime/session/{created.runtime_session_id}/display-title",
            json={"display_title": "我的山门线"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_title"], "我的山门线")

        worlds = client.get("/api/runtime/worlds")
        self.assertEqual(worlds.status_code, 200)
        self.assertEqual(worlds.json()[0]["display_title"], "我的山门线")

    def test_api_bootstrap_returns_snapshot(self) -> None:
        service, _ = self._make_service([_intro_response()])
        created = self._run(service.create_session(_start_request()))
        client = TestClient(create_app(service))

        response = client.post(f"/api/runtime/session/{created.runtime_session_id}/bootstrap")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["boot_status"], "ready")
        self.assertEqual(len(response.json()["messages"]), 1)

    def _run(self, coroutine):
        return asyncio.run(coroutine)


if __name__ == "__main__":
    unittest.main()
