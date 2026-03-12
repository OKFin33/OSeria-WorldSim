from __future__ import annotations

import unittest

from Architect.assembler import Assembler
from Architect.conductor import Conductor
from Architect.forge import Forge
from Architect.interview_controller import InterviewPhase
from Architect.interviewer import Interviewer


class ScriptedLLMClient:
    def __init__(self, *, json_responses: list[dict], generate_responses: list[str]) -> None:
        self.json_responses = list(json_responses)
        self.generate_responses = list(generate_responses)

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        raise AssertionError("chat() is not used in vNext pipeline tests.")

    async def generate(self, *, system_prompt, user_msg, temperature=0.7, response_format=None) -> str:
        if not self.generate_responses:
            raise AssertionError("No scripted generate response left.")
        return self.generate_responses.pop(0)

    async def generate_json(self, prompt, *, system_prompt=None, temperature=0.2) -> dict:
        if not self.json_responses:
            raise AssertionError("No scripted JSON response left.")
        return self.json_responses.pop(0)


class PipelineTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_mocked_pipeline_builds_final_prompt(self) -> None:
        llm = ScriptedLLMClient(
            json_responses=[
                {
                    "routing_snapshot": {
                        "confirmed": ["dim:social_friction"],
                        "exploring": [],
                        "excluded": [],
                        "untouched": ["dim:quest_system", "dim:intimacy"],
                    },
                    "world_dossier": {
                        "world_premise": "这是一个由门阀与高墙组成的都市世界。",
                        "tension_guess": "上位秩序压着低位者往上爬。",
                        "scene_anchor": "高墙下的人抬头看向墙后的掌权者。",
                        "open_threads": ["墙后掌权者究竟是谁"],
                        "soft_signals": {"notable_imagery": ["高墙"], "unstable_hypotheses": []},
                    },
                    "player_dossier": {
                        "fantasy_vector": "从低位向上翻身的人。",
                        "emotional_seed": "被看轻后夺回主动权。",
                        "taste_bias": "压抑、阶层森严、克制。",
                        "language_register": "有画面感，但不过满。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["门阀森严"],
                            "subtext_hypotheses": [],
                            "style_notes": "要冷硬。",
                        },
                    },
                    "change_log": {
                        "newly_confirmed": ["dim:social_friction"],
                        "newly_rejected": [],
                        "needs_follow_up": ["墙后掌权者究竟是谁"],
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
                        "world_premise": "这是一个由门阀与高墙组成的都市世界。",
                        "tension_guess": "上位秩序压着低位者往上爬。",
                        "scene_anchor": "高墙下的人抬头看向墙后的掌权者。",
                        "open_threads": [],
                        "soft_signals": {"notable_imagery": ["高墙"], "unstable_hypotheses": []},
                    },
                    "player_dossier": {
                        "fantasy_vector": "从低位向上翻身的人。",
                        "emotional_seed": "被看轻后夺回主动权。",
                        "taste_bias": "压抑、阶层森严、克制。",
                        "language_register": "有画面感，但不过满。",
                        "user_no_go_zones": [],
                        "soft_signals": {
                            "notable_phrasing": ["门阀森严"],
                            "subtext_hypotheses": [],
                            "style_notes": "要冷硬。",
                        },
                    },
                    "change_log": {"newly_confirmed": [], "newly_rejected": [], "needs_follow_up": []},
                },
                {
                    "confirmed_dimensions": ["dim:social_friction"],
                    "emergent_dimensions": ["dim:quest_system", "dim:intimacy"],
                    "excluded_dimensions": [],
                    "narrative_briefing": "这是一个由门阀、血统与高墙构成的都市世界。主角从城下低位者起步，向上攀爬必须承受秩序的轻蔑与价格。",
                    "player_profile": "玩家偏好压抑、写实、阶层冲突清晰的成长叙事，核心情绪种子是被轻视后翻盘。",
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
                "把每一次寒暄都写成身份试探，把每一次施舍都写成秩序的价格。",
            ],
        )

        interviewer = Interviewer(llm)
        opening = await interviewer.start()
        self.assertIn("闭上眼", opening.message)

        mirror_step = await interviewer.process_user_message("我想要一个门阀森严、普通人很难翻身的都市世界。")
        self.assertEqual(mirror_step.phase, InterviewPhase.MIRROR)

        landing_step = await interviewer.process_user_message("推门")
        self.assertEqual(landing_step.phase, InterviewPhase.LANDING)

        final_step = await interviewer.process_user_message("男，化身也是男。")
        self.assertEqual(final_step.phase, InterviewPhase.COMPLETE)

        compile_output = await interviewer.compile_output()
        frozen_package = interviewer.freeze_compile_package(compile_output)
        manifest = Conductor().build_manifest(compile_output)
        forged = await Forge(llm).execute(manifest, frozen_package.forge_context)
        final_prompt = await Assembler(llm).assemble(forged, manifest, frozen_package.assembler_context)

        self.assertIn("## V. World-Specific Rules", final_prompt)
        self.assertIn("把每一次寒暄都写成身份试探", final_prompt)
        self.assertIn("## VII. Player Calibration", final_prompt)
        self.assertNotIn("{{ tone_primary }}", final_prompt)


if __name__ == "__main__":
    unittest.main()
