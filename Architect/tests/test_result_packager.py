from __future__ import annotations

import unittest

from Architect.conductor import ForgeManifest, ForgeTask
from Architect.interviewer import InterviewArtifacts
from Architect.result_packager import ResultPackager


class ResultPackagerTestCase(unittest.TestCase):
    def test_build_blueprint_summary_extracts_product_fields(self) -> None:
        artifacts = InterviewArtifacts(
            routing_tags={
                "confirmed_dimensions": ["dim:social_friction", "dim:quest_system"],
                "emergent_dimensions": ["dim:intimacy"],
                "excluded_dimensions": ["dim:combat_rules"],
            },
            narrative_briefing=(
                "主角从城墙下的低位者起步，在都市门阀的夹缝里寻找翻身机会。"
                "世界的核心冲突来自阶层秩序、资源垄断和向上攀爬必须付出的代价。"
            ),
            player_profile="玩家偏好写实、压抑、慢热成长，也接受强烈的阶层阻力。",
        )
        manifest = ForgeManifest(
            tasks=[
                ForgeTask(
                    dimension="dim:social_friction",
                    pack_id="pack.urban.friction",
                    pack_content="social pack",
                    supplementary_packs=[],
                    narrative_briefing=artifacts.narrative_briefing,
                    player_profile=artifacts.player_profile,
                ),
                ForgeTask(
                    dimension="dim:quest_system",
                    pack_id="pack.power.quest",
                    pack_content="quest pack",
                    supplementary_packs=[],
                    narrative_briefing=artifacts.narrative_briefing,
                    player_profile=artifacts.player_profile,
                ),
            ],
            emergent_dimensions=["dim:intimacy"],
            excluded_dimensions=["dim:combat_rules"],
            narrative_briefing=artifacts.narrative_briefing,
            player_profile=artifacts.player_profile,
        )

        summary = ResultPackager().build_blueprint_summary(
            artifacts=artifacts,
            manifest=manifest,
            system_prompt="unused in current heuristic",
        )

        self.assertTrue(summary.title)
        self.assertIn("主角", summary.protagonist_hook)
        self.assertIn("冲突", summary.core_tension)
        self.assertEqual(summary.confirmed_dimensions, ["dim:social_friction", "dim:quest_system"])
        self.assertEqual(summary.emergent_dimensions, ["dim:intimacy"])
        self.assertEqual(
            [item.pack_id for item in summary.forged_modules],
            ["pack.urban.friction", "pack.power.quest"],
        )
        self.assertIn("写实", summary.tone_keywords)
        self.assertIn("压抑", summary.tone_keywords)


if __name__ == "__main__":
    unittest.main()
