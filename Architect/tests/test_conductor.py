from __future__ import annotations

import unittest

from Architect.conductor import Conductor
from Architect.domain import CompileOutput


class ConductorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conductor = Conductor()

    def test_core_modules_are_emitted_with_stable_order_and_modes(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:social_friction"],
                narrative_briefing="A stratified harbor city.",
                player_profile="Prefers pressure and slow-burn ascent.",
            )
        )

        self.assertEqual(manifest.tasks[0].module_id, "core.meta.role")
        self.assertEqual(manifest.tasks[0].forge_mode, "locked")
        self.assertEqual(manifest.tasks[1].module_id, "core.meta.experience")
        self.assertEqual(manifest.tasks[1].forge_mode, "soft_forged")
        self.assertEqual(manifest.tasks[2].section, "constitution")
        self.assertEqual(manifest.tasks[5].module_id, "core.eng.sensory")
        self.assertEqual(manifest.tasks[5].forge_mode, "soft_forged")
        self.assertEqual(manifest.tasks[6].module_id, "core.eng.physics")
        self.assertEqual(manifest.tasks[6].forge_mode, "parameterized")
        self.assertEqual(manifest.tasks[-1].section, "world_rules")

    def test_requires_pack_is_included_for_ability_loot(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:ability_loot"],
                narrative_briefing="A high-risk world built around stealing powers.",
                player_profile="Aggressive min-max player.",
            )
        )

        task = next(task for task in manifest.tasks if task.dimension == "dim:ability_loot")
        self.assertEqual(task.pack_id, "pack.power.plugin.loot")
        self.assertIn("Cognitive Augmentation Interface", task.supplementary_packs[0])
        self.assertEqual(task.forge_mode, "full_forged")

    def test_also_consider_is_skipped_when_primary_elsewhere(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:social_friction", "dim:command_friction"],
                narrative_briefing="Faction politics with heavy hierarchy.",
                player_profile="Patient strategist.",
            )
        )

        social_task = next(task for task in manifest.tasks if task.dimension == "dim:social_friction")
        self.assertEqual(social_task.pack_id, "pack.urban.friction")
        self.assertEqual(social_task.supplementary_packs, [])

    def test_unknown_dimension_runs_without_pack(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:craft_economy"],
                emergent_dimensions=["dim:intimacy"],
                narrative_briefing="A shopkeeping fantasy.",
                player_profile="Builder archetype.",
            )
        )

        task = next(task for task in manifest.tasks if task.dimension == "dim:craft_economy")
        self.assertIsNone(task.pack_id)
        self.assertEqual(task.source_content, "")
        self.assertEqual(manifest.emergent_dimensions, ["dim:intimacy"])
        self.assertEqual(task.forge_mode, "full_forged")

    def test_emergent_dimensions_do_not_create_world_rule_tasks(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:social_friction"],
                emergent_dimensions=["dim:ability_loot", "dim:wealth_system"],
                narrative_briefing="A hard city.",
                player_profile="Cold and strategic.",
            )
        )

        world_rule_dimensions = [task.dimension for task in manifest.tasks if task.section == "world_rules"]
        self.assertEqual(world_rule_dimensions, ["dim:social_friction"])
        self.assertEqual(manifest.emergent_dimensions, ["dim:ability_loot", "dim:wealth_system"])


if __name__ == "__main__":
    unittest.main()
