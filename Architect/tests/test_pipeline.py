from __future__ import annotations

import unittest

from Architect.assembler import Assembler
from Architect.conductor import Conductor
from Architect.forge import Forge
from Architect.interview_controller import InterviewPhase
from Architect.interviewer import Interviewer


class ScriptedLLMClient:
    def __init__(
        self,
        *,
        chat_responses: list[str] | None = None,
        generate_responses: list[str] | None = None,
        json_responses: list[dict] | None = None,
    ) -> None:
        self.chat_responses = list(chat_responses or [])
        self.generate_responses = list(generate_responses or [])
        self.json_responses = list(json_responses or [])

    async def chat(self, messages, *, system_prompt=None, temperature=0.7, response_format=None) -> str:
        if not self.chat_responses:
            raise AssertionError("No scripted chat response left.")
        return self.chat_responses.pop(0)

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
            chat_responses=[
                """<<VISIBLE>>
你已经站在高墙下了。我只想再知道一点点，谁在墙后掌握生死？
<<END_VISIBLE>>
<<SYSTEM_JSON>>
{"turn": 1, "question": "谁在墙后掌握生死？", "suggested_tags": ["城墙下的灰", "门阀的余烬", "想往上爬的人"], "routing_snapshot": {"confirmed": ["dim:social_friction"], "exploring": [], "excluded": [], "untouched": ["dim:quest_system", "dim:intimacy"]}, "vibe_flavor": "grim_urban"}
<<END_SYSTEM_JSON>>"""
            ],
            generate_responses=[
                "城墙上的人把秩序写成了血统，而你站在城下，知道每一次抬头都要付出代价。门阀、贫民与想翻盘的人彼此拉扯，连空气都像旧债。门快开了，你准备带着什么走进去？",
                "那么，最后两个很简单的问题。\n你的性别？以及，在这个世界里推开那扇门的你的化身，是男是女？",
                """{
                  "confirmed_dimensions": ["dim:social_friction"],
                  "emergent_dimensions": ["dim:quest_system", "dim:intimacy"],
                  "excluded_dimensions": [],
                  "narrative_briefing": "这是一个由门阀、血统与阶层固化构成的都市世界。主角从城墙下的低位者起步，向上攀爬不是荣耀，而是一次次与秩序正面相撞。世界的核心张力来自身份差、资源垄断和被看不起之后仍然选择往上走的执念。",
                  "player_profile": "玩家偏好压迫感明确、阶层冲突清晰的叙事，愿意承受缓慢推进与社会阻力，核心情绪种子是被认可与向上翻盘。"
                }""",
                "把每一次寒暄都写成身份试探，把每一次施舍都写成秩序的价格。主角若想跨过门槛，必须先学会读懂轻蔑、怜悯与交易背后的阶层坐标。",
            ],
            json_responses=[
                {
                    "tone_primary": "写实",
                    "tone_secondary": "压抑",
                    "content_ceiling": "PG-13",
                    "humor_density": "严肃零幽默",
                    "sensory_smell_example": "潮湿墙根混着铁锈的气味",
                    "sensory_sound_example": "城门齿轮缓慢咬合的摩擦声",
                    "tone_filter": "冷硬而克制",
                    "ignorance_reaction": "Mockery",
                }
            ],
        )

        interviewer = Interviewer(llm)
        opening = await interviewer.start()
        self.assertIn("闭上眼", opening.message)

        mirror_step = await interviewer.process_user_message("我想要一个门阀森严、普通人很难翻身的都市世界。")
        self.assertEqual(mirror_step.phase, InterviewPhase.MIRROR)
        self.assertIn("城墙上的人", mirror_step.message)

        landing_step = await interviewer.process_user_message("是，就是这个。")
        self.assertEqual(landing_step.phase, InterviewPhase.LANDING)
        self.assertIn("最后两个很简单的问题", landing_step.message)

        final_step = await interviewer.process_user_message("男，化身也是男。")
        self.assertEqual(final_step.phase, InterviewPhase.COMPLETE)
        self.assertIsNotNone(final_step.artifacts)

        conductor = Conductor()
        manifest = conductor.process_interview_results(
            final_step.artifacts.routing_tags,
            final_step.artifacts.narrative_briefing,
            final_step.artifacts.player_profile,
        )

        forged = await Forge(llm).execute(manifest)
        final_prompt = await Assembler(llm).assemble(forged, manifest)

        self.assertIn("## V. World-Specific Rules", final_prompt)
        self.assertIn("把每一次寒暄都写成身份试探", final_prompt)
        self.assertIn("dim:quest_system", final_prompt)
        self.assertNotIn("{{ tone_primary }}", final_prompt)


if __name__ == "__main__":
    unittest.main()
