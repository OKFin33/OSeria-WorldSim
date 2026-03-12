from __future__ import annotations

import unittest

from Architect.conductor import Conductor
from Architect.domain import CompileOutput


class ConductorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.conductor = Conductor()

    def test_requires_pack_is_included_for_ability_loot(self) -> None:
        manifest = self.conductor.build_manifest(
            CompileOutput(
                confirmed_dimensions=["dim:ability_loot"],
                narrative_briefing="A high-risk world built around stealing powers.",
                player_profile="Aggressive min-max player.",
            )
        )

        self.assertEqual(len(manifest.tasks), 1)
        task = manifest.tasks[0]
        self.assertEqual(task.pack_id, "pack.power.plugin.loot")
        self.assertIn("Cognitive Augmentation Interface", task.supplementary_packs[0])

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

        self.assertEqual(len(manifest.tasks), 1)
        task = manifest.tasks[0]
        self.assertIsNone(task.pack_id)
        self.assertEqual(task.pack_content, "")
        self.assertEqual(manifest.emergent_dimensions, ["dim:intimacy"])


if __name__ == "__main__":
    unittest.main()
