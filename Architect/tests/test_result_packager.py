from __future__ import annotations

import unittest

from Architect.conductor import ForgeManifest, ForgeTask
from Architect.domain import CompileOutput
from Architect.result_packager import ResultPackager


class ResultPackagerTestCase(unittest.TestCase):
    def test_build_blueprint_extracts_product_fields(self) -> None:
        compile_output = CompileOutput(
            confirmed_dimensions=["dim:social_friction", "dim:quest_system"],
            emergent_dimensions=["dim:intimacy"],
            excluded_dimensions=["dim:combat_rules"],
            narrative_briefing=(
                "这是一座被高墙和雾包裹的近未来海港城市，霓虹映在潮湿路面上，社会分层森严。"
                "主角从城墙下的低位者起步，在都市门阀的夹缝里寻找翻身机会。"
                "世界的核心冲突来自阶层秩序、资源垄断和向上攀爬必须付出的代价。"
            ),
            player_profile="玩家偏好写实、压抑、慢热成长，也接受强烈的阶层阻力。",
        )
        manifest = ForgeManifest(
            tasks=[
                ForgeTask(
                    module_id="core.meta.role",
                    section="meta",
                    forge_mode="locked",
                    source_content="meta",
                    dimension=None,
                    pack_id=None,
                    supplementary_packs=[],
                    supplementary_pack_ids=[],
                    module_scope="meta",
                    rewrite_budget="none",
                ),
                ForgeTask(
                    module_id="pack.urban.friction",
                    section="world_rules",
                    forge_mode="full_forged",
                    source_content="social pack",
                    dimension="dim:social_friction",
                    pack_id="pack.urban.friction",
                    supplementary_packs=[],
                    supplementary_pack_ids=[],
                    module_scope="social friction",
                    rewrite_budget="high",
                ),
                ForgeTask(
                    module_id="pack.power.quest",
                    section="world_rules",
                    forge_mode="full_forged",
                    source_content="quest pack",
                    dimension="dim:quest_system",
                    pack_id="pack.power.quest",
                    supplementary_packs=[],
                    supplementary_pack_ids=[],
                    module_scope="quest system",
                    rewrite_budget="high",
                ),
            ],
            emergent_dimensions=["dim:intimacy"],
            excluded_dimensions=["dim:combat_rules"],
            compile_output=compile_output,
        )

        summary = ResultPackager().build_blueprint(
            compile_output=compile_output,
            manifest=manifest,
        )

        self.assertEqual(summary.title, "高墙海港城")
        self.assertIn("海港城市", summary.protagonist_hook)
        self.assertNotIn("主角", summary.protagonist_hook)
        self.assertIn("冲突", summary.core_tension)
        self.assertNotEqual(summary.protagonist_hook, summary.core_tension)
        self.assertEqual(summary.confirmed_dimensions, ["dim:social_friction", "dim:quest_system"])
        self.assertEqual(summary.emergent_dimensions, ["dim:intimacy"])
        self.assertEqual(
            [item.pack_id for item in summary.forged_modules],
            ["pack.urban.friction", "pack.power.quest"],
        )
        self.assertIn("写实", summary.tone_keywords)
        self.assertIn("压抑", summary.tone_keywords)

    def test_build_blueprint_preserves_town_titles_without_mid_word_truncation(self) -> None:
        compile_output = CompileOutput(
            confirmed_dimensions=["dim:emotional_bonds"],
            emergent_dimensions=[],
            excluded_dimensions=[],
            narrative_briefing=(
                "这是一个云海之上的修仙小镇，山门、药田、灵兽和凡人邻里构成一个秩序可亲、合家欢气息浓厚的世界。"
                "玩家将从一个被照顾的普通孩子起步，在师兄妹的陪伴和日常温暖中成长。"
            ),
            player_profile="玩家偏好温暖、归属感与成长。",
        )
        manifest = ForgeManifest(
            tasks=[],
            emergent_dimensions=[],
            excluded_dimensions=[],
            compile_output=compile_output,
        )

        summary = ResultPackager().build_blueprint(
            compile_output=compile_output,
            manifest=manifest,
        )

        self.assertEqual(summary.title, "云海之上的修仙小镇")


if __name__ == "__main__":
    unittest.main()
