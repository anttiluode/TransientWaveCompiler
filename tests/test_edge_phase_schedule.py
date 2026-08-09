import unittest

from transientwave.backend import TW1AGridBackend
from transientwave.edge_phase_schedule import four_phase_edge_schedule, schedule_audit


class EdgePhaseScheduleTests(unittest.TestCase):
    def test_8x8_schedule_has_four_complete_matchings(self):
        audit = schedule_audit(TW1AGridBackend())
        # On an 8x8 grid, parity coloring produces 32/24 horizontal bonds and
        # 32/24 vertical bonds because there are four even starting columns /
        # rows and three odd ones. Equal phase sizes are not required; the
        # architectural invariant is one edge at most per node per phase.
        self.assertEqual(audit["phase_edge_counts"], [32, 24, 32, 24])
        self.assertEqual(sum(audit["phase_edge_counts"]), 112)
        self.assertEqual(audit["max_node_use_per_phase"], [1, 1, 1, 1])
        self.assertEqual(audit["duplicate_nodes_per_phase"], [[], [], [], []])
        self.assertTrue(audit["covers_all_edges_once"])

    def test_each_phase_is_node_disjoint(self):
        for phase in four_phase_edge_schedule(TW1AGridBackend()):
            nodes = [n for edge in phase for n in edge]
            self.assertEqual(len(nodes), len(set(nodes)))


if __name__ == "__main__":
    unittest.main()
