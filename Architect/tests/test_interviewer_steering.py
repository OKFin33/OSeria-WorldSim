from __future__ import annotations

import unittest

from Architect.interview_controller import InterviewPhase
from Architect.interviewer import Interviewer


class RecordedLLMClient:
    def __init__(self, *, json_responses: list[dict], generate_responses: list[str] | None = None) -> None:
        self.json_responses = list(json_responses)
        self.generate_responses = list(generate_responses or [])
        self.system_prompts: list[str | None] = []
        self.prompts: list[str] = []
        self.generate_json_kwargs: list[dict[str, object]] = []

    async def chat(
        self,
        messages,
        *,
        system_prompt=None,
        temperature=0.7,
        response_format=None,
        timeout=None,
        max_retries=None,
        observer=None,
    ) -> str:
        raise AssertionError("chat() is not used in vNext interviewer tests.")

    async def generate(
        self,
        *,
        system_prompt,
        user_msg,
        temperature=0.7,
        response_format=None,
        timeout=None,
        max_retries=None,
        observer=None,
    ) -> str:
        if not self.generate_responses:
            raise AssertionError("No scripted generate response left.")
        return self.generate_responses.pop(0)

    async def generate_json(
        self,
        prompt,
        *,
        system_prompt=None,
        temperature=0.2,
        timeout=None,
        max_retries=None,
        observer=None,
    ) -> dict:
        self.system_prompts.append(system_prompt)
        self.prompts.append(prompt)
        self.generate_json_kwargs.append({"timeout": timeout, "max_retries": max_retries})
        if not self.json_responses:
            raise AssertionError("No scripted JSON response left.")
        return self.json_responses.pop(0)


class SelectiveFailLLMClient(RecordedLLMClient):
    def __init__(self, *, json_responses: list[dict]) -> None:
        super().__init__(json_responses=json_responses)
        self.dossier_failures = 0

    async def generate_json(
        self,
        prompt,
        *,
        system_prompt=None,
        temperature=0.2,
        timeout=None,
        max_retries=None,
        observer=None,
    ) -> dict:
        self.system_prompts.append(system_prompt)
        self.prompts.append(prompt)
        self.generate_json_kwargs.append({"timeout": timeout, "max_retries": max_retries})
        if system_prompt and "静默档案官" in system_prompt:
            self.dossier_failures += 1
            raise TimeoutError("dossier updater timeout")
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
        self.assertEqual(
            interviewer.messages[-1]["content"],
            "高墙已经在眼前。我想再知道一点，墙后到底是谁在发号施令？\n墙后到底是谁在发号施令？",
        )

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

    async def test_landing_falls_back_when_composer_returns_mirror_like_text(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "mode": "mirror",
                    "mirror_text": "城墙上的人把秩序写成了血统，而你站在城下。",
                },
                {
                    "mode": "mirror",
                    "mirror_text": "城墙上的人把秩序写成了血统，而你站在城下。",
                },
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.controller.phase = InterviewPhase.MIRROR
        interviewer.messages.append({"role": "assistant", "content": "城墙上的人把秩序写成了血统，而你站在城下。"})

        step = await interviewer.process_user_message("推门")

        self.assertEqual(step.phase, InterviewPhase.LANDING)
        self.assertEqual(
            step.message,
            "最后两个问题。你本人的性别是什么？你想进入这个世界时，化身希望是什么性别？",
        )

    async def test_landing_submission_skips_dossier_updater_and_completes(self) -> None:
        llm = RecordedLLMClient(json_responses=[])
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.controller.phase = InterviewPhase.LANDING

        step = await interviewer.process_user_message("我本人男，化身也男。")

        self.assertEqual(step.phase, InterviewPhase.COMPLETE)
        self.assertEqual(interviewer.dossier_update_status, "update_skipped")
        self.assertEqual(llm.system_prompts, [])

    async def test_dossier_updater_payload_uses_minimal_context(self) -> None:
        llm = RecordedLLMClient(json_responses=[])
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.messages.append({"role": "user", "content": "第一轮回答"})
        interviewer.messages.append({"role": "assistant", "content": "上一轮回声\n上一轮问题"})
        interviewer.messages.append({"role": "user", "content": "最新回答"})
        interviewer.twin_dossier.routing_snapshot.confirmed = ["dim:emotional_bonds"]
        interviewer.twin_dossier.routing_snapshot.untouched = ["dim:quest_system"]
        interviewer.controller.turn = 4

        payload = interviewer._build_dossier_updater_payload(interviewer.twin_dossier)

        self.assertNotIn("recent_context", payload)
        self.assertEqual(payload["last_assistant_prompt"], "上一轮回声\n上一轮问题")
        self.assertEqual(payload["previous_user_message"], "第一轮回答")
        self.assertEqual(payload["latest_user_message"], "最新回答")
        self.assertNotIn("untouched", payload["previous_routing_snapshot"])

    async def test_dossier_updater_can_use_dedicated_llm_client(self) -> None:
        dossier_llm = RecordedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": [],
                        "exploring": ["dim:emotional_bonds"],
                        "excluded": [],
                        "untouched": [
                            "dim:social_friction",
                            "dim:quest_system",
                            "dim:wealth_system",
                        ],
                    },
                    "world_dossier": {
                        "world_premise": "云海上的小镇以护山阵法维持平静。",
                        "tension_guess": "平静生活需要被悄悄守住。",
                        "scene_anchor": "清晨云海漫过药田边缘。",
                        "open_threads": ["谁在维护阵法"],
                        "soft_signals": {
                            "notable_imagery": ["云海", "药田"],
                            "unstable_hypotheses": [],
                        },
                    },
                    "player_dossier": {
                        "fantasy_vector": "从被照顾的人慢慢长成能照顾别人的人。",
                        "emotional_seed": "被温柔接住后学会把温柔传下去。",
                        "taste_bias": "温和、明亮、有人情味。",
                        "language_register": "轻柔但不甜腻。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["被接住"],
                            "subtext_hypotheses": [],
                            "style_notes": "合家欢但不幼稚。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": [],
                        "newly_rejected": [],
                        "needs_follow_up": ["谁在维护阵法"],
                    },
                }
            ]
        )
        main_llm = RecordedLLMClient(
            json_responses=[
                {
                    "mode": "interview",
                    "visible_text": "药田边的风已经吹过来了，我想知道，最先把你留在这里的人是谁？",
                    "question": "最先把你留在这里的人是谁？",
                },
                {
                    "bubble_candidates": [
                        {"text": "一个总把灵果塞给我的师姐", "kind": "answer"},
                        {"text": "守着药田的老药师", "kind": "answer"},
                    ]
                },
            ]
        )
        interviewer = Interviewer(main_llm, dossier_llm_client=dossier_llm)
        await interviewer.start()

        step = await interviewer.process_user_message("我想要一个云海上的修仙小镇，大家彼此照看。")

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(len(dossier_llm.prompts), 1)
        self.assertEqual(len(main_llm.prompts), 2)
        self.assertIn("latest_user_message", dossier_llm.prompts[0])
        self.assertNotIn("latest_user_message", main_llm.prompts[0])

    async def test_stabilize_timeout_reuses_previous_dossier_without_second_outer_retry(self) -> None:
        llm = SelectiveFailLLMClient(
            json_responses=[
                {
                    "mode": "interview",
                    "visible_text": "我先沿着上一轮的理解继续问。",
                    "question": "这份温暖里，你最怕失去的是哪一部分？",
                },
                {
                    "bubble_candidates": [
                        {"text": "我怕失去那种被看见的感觉。", "kind": "answer"},
                    ]
                },
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.controller.turn = 4
        interviewer.twin_dossier.world_dossier.world_premise = "这是一个云海上的温暖修仙小镇。"
        interviewer.twin_dossier.player_dossier.fantasy_vector = "从被照顾走向照顾他人的位置。"
        interviewer.twin_dossier.routing_snapshot.exploring = ["dim:emotional_bonds"]
        interviewer.twin_dossier.routing_snapshot.untouched = [
            "dim:quest_system",
            "dim:intimacy",
            "dim:wealth_system",
        ]

        step = await interviewer.process_user_message("我想把这种温暖继续传下去。")

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(interviewer.dossier_update_status, "update_skipped")
        self.assertEqual(llm.dossier_failures, 1)
        self.assertEqual(llm.generate_json_kwargs[0]["timeout"], 20.0)
        self.assertEqual(llm.generate_json_kwargs[0]["max_retries"], 0)
        self.assertTrue(step.debug_trace["fallback_used"])
        self.assertEqual(step.debug_trace["llm_observations"][0]["call_name"], "dossier_updater")
        self.assertEqual(step.debug_trace["llm_observations"][0]["status"], "error")

    async def test_stabilize_guardrails_demote_new_confirmed_without_strong_history(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:emotional_bonds", "dim:command_friction"],
                        "exploring": ["dim:power_progression"],
                        "excluded": [],
                        "untouched": [
                            "dim:social_friction",
                            "dim:quest_system",
                            "dim:intimacy",
                            "dim:wealth_system",
                        ],
                    },
                    "world_dossier": {
                        "world_premise": "这是一个云海上的修仙小镇，大家一起守着药田和灵兽。",
                        "tension_guess": "山外风浪逼近时，镇上人如何共同守住家。",
                        "scene_anchor": "主角站在镇口，身后是需要守住的人。",
                        "open_threads": ["山外风浪究竟是什么"],
                        "soft_signals": {
                            "notable_imagery": ["云海", "镇口"],
                            "unstable_hypotheses": [],
                        },
                    },
                    "player_dossier": {
                        "fantasy_vector": "成为能照顾别人、稳住场面的人。",
                        "emotional_seed": "把被接住的感觉继续传下去。",
                        "taste_bias": "温和、合家欢。",
                        "language_register": "轻柔克制。",
                        "user_no_go_zones": ["不要太残酷血腥"],
                        "soft_signals": {
                            "notable_phrasing": ["一起把山外的风浪挡住"],
                            "subtext_hypotheses": [],
                            "style_notes": "有人情味。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": ["dim:command_friction"],
                        "newly_rejected": [],
                        "needs_follow_up": ["怎么一起挡住"],
                    },
                },
                {
                    "mode": "interview",
                    "visible_text": "你已经很明确地站在‘留下来一起守住’这边了。",
                    "question": "那当你真的要稳住场面时，最先依靠的是人心、阵法，还是你自己的承担？",
                },
                {
                    "bubble_candidates": [
                        {"text": "先稳住大家的人心。", "kind": "answer"},
                    ]
                },
            ]
        )
        interviewer = Interviewer(llm)
        await interviewer.start()
        interviewer.controller.turn = 4
        interviewer.controller.history = [
            {
                "confirmed": ["dim:emotional_bonds"],
                "exploring": ["dim:command_friction"],
                "excluded": [],
                "untouched": ["dim:quest_system", "dim:intimacy", "dim:wealth_system"],
            }
        ]
        interviewer.twin_dossier.routing_snapshot.confirmed = ["dim:emotional_bonds"]
        interviewer.twin_dossier.routing_snapshot.exploring = ["dim:command_friction", "dim:power_progression"]
        interviewer.twin_dossier.routing_snapshot.untouched = [
            "dim:social_friction",
            "dim:quest_system",
            "dim:intimacy",
            "dim:wealth_system",
        ]

        step = await interviewer.process_user_message(
            "如果一定要有更远一点的目标，我希望最后我能带着镇上的人一起把山外的风浪挡住，而不是一个人飞升离开。"
        )

        self.assertEqual(step.phase, InterviewPhase.INTERVIEWING)
        self.assertEqual(interviewer.twin_dossier.routing_snapshot.confirmed, ["dim:emotional_bonds"])
        self.assertIn("dim:command_friction", interviewer.twin_dossier.routing_snapshot.exploring)
        self.assertNotIn("dim:command_friction", interviewer.twin_dossier.change_log.newly_confirmed)

    async def test_stabilize_guardrails_keep_long_supported_confirmed_dimension(self) -> None:
        llm = RecordedLLMClient(json_responses=[])
        interviewer = Interviewer(llm)
        interviewer.controller.history = [
            {"confirmed": [], "exploring": ["dim:command_friction"], "excluded": [], "untouched": []},
            {"confirmed": [], "exploring": ["dim:command_friction"], "excluded": [], "untouched": []},
            {"confirmed": ["dim:command_friction"], "exploring": [], "excluded": [], "untouched": []},
        ]
        previous = interviewer.twin_dossier
        previous.routing_snapshot.confirmed = ["dim:emotional_bonds"]

        dossier = previous.from_dict(
            {
                "routing_snapshot": {
                    "confirmed": ["dim:emotional_bonds", "dim:command_friction"],
                    "exploring": [],
                    "excluded": [],
                    "untouched": ["dim:quest_system"],
                },
                "world_dossier": {},
                "player_dossier": {},
                "change_log": {"newly_confirmed": ["dim:command_friction"], "newly_rejected": [], "needs_follow_up": []},
            }
        )

        normalized = interviewer._normalize_twin_dossier(
            dossier,
            updater_mode="stabilize",
            previous=previous,
        )

        self.assertIn("dim:command_friction", normalized.routing_snapshot.confirmed)

    async def test_compile_output_promotes_stable_dimensions_and_caps_emergent(self) -> None:
        llm = RecordedLLMClient(
            json_responses=[
                {
                    "confirmed_dimensions": [],
                    "emergent_dimensions": [
                        "dim:combat_rules",
                        "dim:power_progression",
                        "dim:command_friction",
                        "dim:quest_system",
                        "dim:intimacy",
                        "dim:wealth_system",
                    ],
                    "excluded_dimensions": [],
                    "narrative_briefing": "一个规矩压着人的修仙世界。",
                    "player_profile": "偏冷硬、克制。",
                }
            ]
        )
        interviewer = Interviewer(llm)
        interviewer.twin_dossier.routing_snapshot.confirmed = []
        interviewer.twin_dossier.routing_snapshot.exploring = [
            "dim:command_friction",
            "dim:combat_rules",
            "dim:power_progression",
        ]
        interviewer.twin_dossier.routing_snapshot.untouched = [
            "dim:quest_system",
            "dim:intimacy",
            "dim:wealth_system",
            "dim:skill_shop",
        ]
        interviewer.controller.history = [
            {"confirmed": [], "exploring": ["dim:command_friction"], "excluded": [], "untouched": []},
            {"confirmed": [], "exploring": ["dim:command_friction", "dim:combat_rules"], "excluded": [], "untouched": []},
        ]

        compile_output = await interviewer.compile_output()

        self.assertEqual(compile_output.confirmed_dimensions, ["dim:command_friction", "dim:combat_rules"])
        self.assertLessEqual(len(compile_output.emergent_dimensions), 4)
        self.assertNotIn("dim:command_friction", compile_output.emergent_dimensions)
        self.assertNotIn("dim:combat_rules", compile_output.emergent_dimensions)


if __name__ == "__main__":
    unittest.main()
