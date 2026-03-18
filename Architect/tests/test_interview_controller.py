from __future__ import annotations

import unittest

from Architect.interview_controller import InterviewController, InterviewPhase, MAX_TURNS


class InterviewControllerTestCase(unittest.TestCase):
    def test_mirror_triggers_when_untouched_threshold_is_reached(self) -> None:
        controller = InterviewController()
        next_phase = controller.process_turn(
            {
                "routing_snapshot": {
                    "confirmed": ["dim:social_friction"],
                    "exploring": [],
                    "excluded": [],
                    "untouched": ["dim:intimacy", "dim:combat_rules"],
                }
            }
        )
        self.assertEqual(next_phase, InterviewPhase.MIRROR)

    def test_mirror_triggers_on_turn_cap(self) -> None:
        controller = InterviewController()
        response = {
            "routing_snapshot": {
                "confirmed": [],
                "exploring": [],
                "excluded": [],
                "untouched": [f"dim:{index}" for index in range(8)],
            }
        }
        phase = InterviewPhase.INTERVIEWING
        for _ in range(MAX_TURNS):
            phase = controller.process_turn(response)
        self.assertEqual(phase, InterviewPhase.MIRROR)

    def test_finalize_routing_turns_untouched_into_emergent(self) -> None:
        controller = InterviewController()
        controller.process_turn(
            {
                "routing_snapshot": {
                    "confirmed": ["dim:social_friction"],
                    "exploring": [],
                    "excluded": ["dim:intimacy"],
                    "untouched": ["dim:combat_rules", "dim:wealth_system"],
                }
            }
        )
        finalized = controller.finalize_routing()
        self.assertEqual(finalized["confirmed_dimensions"], ["dim:social_friction"])
        self.assertEqual(finalized["emergent_dimensions"], ["dim:combat_rules", "dim:wealth_system"])
        self.assertEqual(finalized["excluded_dimensions"], ["dim:intimacy"])


if __name__ == "__main__":
    unittest.main()

