from __future__ import annotations

import unittest

from Architect.interview_controller import InterviewPhase
from Architect.interviewer import Interviewer


class RecordedLLMClient:
    def __init__(self, *, json_responses: list[dict], generate_responses: list[str] | None = None) -> None:
        self.json_responses = list(json_responses)
        self.generate_responses = list(generate_responses or [])
        self.system_prompts: list[str | None] = []

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        raise AssertionError("chat() is not used in vNext interviewer tests.")

    async def generate(self, *, system_prompt, user_msg, temperature=0.7, response_format=None) -> str:
        if not self.generate_responses:
            raise AssertionError("No scripted generate response left.")
        return self.generate_responses.pop(0)

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict:
        self.system_prompts.append(system_prompt)
        if not self.json_responses:
            raise AssertionError("No scripted JSON response left.")
        return self.json_responses.pop(0)


class InterviewerVNextTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_dossier_update_mode_follows_two_two_one_rhythm(self) -> None:
        llm = RecordedLLMClient(json_responses=[])
        interviewer = Interviewer(llm)

        interviewer.controller.turn = 0
        self.assertEqual(interviewer._dossier_update_mode(), "bootstrap")
        interviewer.controller.turn = 1
        self.assertEqual(interviewer._dossier_update_mode(), "bootstrap")
        interviewer.controller.turn = 2
        self.assertEqual(interviewer._dossier_update_mode(), "refine")
        interviewer.controller.turn = 3
        self.assertEqual(interviewer._dossier_update_mode(), "refine")
        interviewer.controller.turn = 4
        self.assertEqual(interviewer._dossier_update_mode(), "stabilize")

    async def test_interview_turn_returns_bubbles_and_typed_payload(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:social_friction"],
                        "exploring": ["dim:quest_system"],
                        "excluded": [],
                        "untouched": ["dim:intimacy", "dim:combat_rules", "dim:wealth_system"],
                    },
                    "world_dossier": {
                        "world_premise": "这是一个门阀森严、普通人很难翻身的都市世界。",
                        "tension_guess": "上位秩序对低位者的压迫。",
                        "scene_anchor": "高墙下的人抬头看向墙后掌权者。",
                        "open_threads": ["墙后掌权者究竟是谁"],
                        "soft_signals": {
                            "notable_imagery": ["高墙", "门阀"],
                            "unstable_hypotheses": [],
                        },
                    },
                    "player_dossier": {
                        "fantasy_vector": "从低位向上翻身的人。",
                        "emotional_seed": "被轻视后夺回主动权。",
                        "taste_bias": "压抑、冷硬、阶层明确。",
                        "language_register": "意象感强但不浮夸。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["门阀森严"],
                            "subtext_hypotheses": [],
                            "style_notes": "要有压迫感。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": ["dim:social_friction"],
                        "newly_rejected": [],
                        "needs_follow_up": ["墙后掌权者究竟是谁"],
                    },
                },
                {
                    "mode": "interview",
                    "visible_text": "高墙已经在眼前。我想再知道一点，墙后到底是谁在发号施令？",
                    "question": "墙后到底是谁在发号施令？",
                },
                {
                    "bubble_candidates": [
                        {"text": "一个门阀老祖", "kind": "answer"},
                        {"text": "一整个长老会", "kind": "answer"},
                        {"text": "更无形的规矩本身", "kind": "advance"},
                    ]
                },
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()

        step = await interviewer.process_user_message("我想要一个门阀森严、普通人很难翻身的都市世界。")

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(step.message, "高墙已经在眼前。我想再知道一点，墙后到底是谁在发号施令？")
        self.assertEqual(step.raw_payload["question"], "墙后到底是谁在发号施令？")
        self.assertEqual(
            step.raw_payload["bubble_candidates"],
            [
                {"text": "一个门阀老祖", "kind": "answer"},
                {"text": "一整个长老会", "kind": "answer"},
                {"text": "更无形的规矩本身", "kind": "advance"},
            ],
        )
        self.assertEqual(step.raw_payload["dossier_update_status"], "updated")
        self.assertEqual(step.raw_payload["routing_snapshot"]["confirmed"], ["dim:social_friction"])

    async def test_bootstrap_guardrails_soften_overcommitted_first_turn_dossier(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:power_progression", "dim:combat_rules"],
                        "exploring": [],
                        "excluded": [],
                        "untouched": ["dim:social_friction", "dim:quest_system", "dim:intimacy"],
                    },
                    "world_dossier": {
                        "world_premise": "一个修仙世界，主角追求成为大剑仙，以御剑飞行和剑光纵横为核心能力。",
                        "tension_guess": "主角从弱小到强大的成长。",
                        "scene_anchor": "主角御剑飞行，剑光划破天际。",
                        "open_threads": ["门派与规则是什么"],
                        "soft_signals": {
                            "notable_imagery": ["御剑飞行", "剑光纵横"],
                            "unstable_hypotheses": [],
                        },
                    },
                    "player_dossier": {
                        "fantasy_vector": "成为大剑仙，掌握御剑飞行和强大剑术。",
                        "emotional_seed": "追求强大、自由和掌控感。",
                        "taste_bias": "偏热血、爽感",
                        "language_register": "简洁、直接、带有武侠或仙侠色彩",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["我想要修仙，大剑仙那种，御剑飞行，剑光纵横。"],
                            "subtext_hypotheses": [],
                            "style_notes": "快节奏、高能量。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": ["修仙题材"],
                        "newly_rejected": [],
                        "needs_follow_up": ["这个世界真正压住人的是什么"],
                    },
                },
                {
                    "mode": "interview",
                    "visible_text": "剑光划破云霄，但那只是第一眼。告诉我，那股让你抬头的锋芒，第一次真正有了重量时，周围是什么样子？",
                    "question": "那股让你抬头的锋芒，第一次真正有了重量时，周围是什么样子？",
                },
                {"bubble_candidates": []},
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()

        await interviewer.process_user_message("我想要修仙，大剑仙那种，御剑飞行，剑光纵横。")

        self.assertNotIn("成为大剑仙", interviewer.twin_dossier.player_dossier.fantasy_vector)
        self.assertNotIn("主角追求成为大剑仙", interviewer.twin_dossier.world_dossier.world_premise)
        self.assertEqual(interviewer.twin_dossier.player_dossier.taste_bias, "")

    async def test_reject_returns_single_recovery_question_without_running_dossier_updater(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "mode": "interview",
                    "visible_text": "那我换个角度问。真正压在你头上的，是人，还是一整套谁都不敢违抗的规矩？",
                    "question": "真正压在你头上的，是人，还是一整套谁都不敢违抗的规矩？",
                },
                {
                    "bubble_candidates": [
                        {"text": "一个具体的人", "kind": "answer"},
                        {"text": "一整套不能违抗的规矩", "kind": "answer"},
                    ]
                },
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.controller.phase = InterviewPhase.MIRROR
        interviewer.twin_dossier.routing_snapshot.confirmed = ["dim:social_friction"]
        interviewer.twin_dossier.routing_snapshot.untouched = ["dim:quest_system", "dim:intimacy"]
        interviewer.twin_dossier.world_dossier.world_premise = "这是一个门阀压顶的都市世界。"
        interviewer.twin_dossier.player_dossier.fantasy_vector = "从低位向上翻身的人。"

        step = await interviewer.process_user_message("我得再想想")

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(step.raw_payload["follow_up_signal"], "mirror_rejected")
        self.assertTrue(
            all("静默档案官" not in (prompt or "") for prompt in llm.system_prompts),
            "reject recovery should not invoke the dossier updater before new user evidence arrives",
        )


if __name__ == "__main__":
    unittest.main()
