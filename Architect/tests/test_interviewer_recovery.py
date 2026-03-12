from __future__ import annotations

import unittest

from Architect.interview_controller import InterviewPhase
from Architect.interviewer import Interviewer


class FailingUpdaterLLMClient:
    def __init__(self, *, fail_count: int, json_responses: list[dict]) -> None:
        self.fail_count = fail_count
        self.json_responses = list(json_responses)

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        raise AssertionError("chat() is not used in vNext interviewer tests.")

    async def generate(self, *, system_prompt, user_msg, temperature=0.7, response_format=None) -> str:
        raise AssertionError("generate() is not used in this recovery test.")

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict:
        if self.fail_count > 0 and system_prompt and "静默档案官" in system_prompt:
            self.fail_count -= 1
            raise RuntimeError("upstream timeout")
        if not self.json_responses:
            raise AssertionError("No scripted JSON response left.")
        return self.json_responses.pop(0)


class InterviewerRecoveryTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_soft_failure_keeps_previous_dossier_and_continues(self) -> None:
        llm = FailingUpdaterLLMClient(
            fail_count=2,
            json_responses=[
                {
                    "mode": "interview",
                    "visible_text": "我先不急着扩写。告诉我，在这座城里最先压住你的，会是人，还是规矩？",
                    "question": "在这座城里最先压住你的，会是人，还是规矩？",
                },
                {"bubble_candidates": []},
            ],
        )
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.twin_dossier.world_dossier.world_premise = "这是一个秩序压顶的都市世界。"
        interviewer.twin_dossier.player_dossier.fantasy_vector = "从低位翻身的人。"
        interviewer.twin_dossier.routing_snapshot.confirmed = ["dim:social_friction"]
        interviewer.twin_dossier.routing_snapshot.untouched = ["dim:quest_system", "dim:intimacy", "dim:combat_rules"]

        step = await interviewer.process_user_message("再压一点。")

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(interviewer.dossier_update_status, "update_skipped")
        self.assertEqual(interviewer.twin_dossier.world_dossier.world_premise, "这是一个秩序压顶的都市世界。")


if __name__ == "__main__":
    unittest.main()
