import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.measurement_aware_filter import measurement_aware_response
from transientwave.topology_discovery import (
    absent_reciprocal_edges,
    score_missing_reciprocal_edges,
)


class TopologyDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        self.values = np.array([1.0, 0.62, 1.0], dtype=float)
        self.omega = np.unique(
            np.concatenate([np.linspace(-7.0, 7.0, 141), np.linspace(-2.0, 2.0, 121)])
        )

    def test_absent_edges_exclude_declared_reciprocal_entries(self):
        edges = absent_reciprocal_edges(4, self.parameters)
        pairs = {(edge.i, edge.j) for edge in edges}
        self.assertEqual(pairs, {(0, 2), (0, 3), (1, 3)})

    def test_clean_hidden_edge_ranks_first(self):
        hidden = MatrixParameter(0, 2, "hidden_02")
        hidden_value = 0.08
        measured11, measured21 = measurement_aware_response(
            [*self.values, hidden_value],
            n=4,
            parameters=[*self.parameters, hidden],
            omega=self.omega,
            resonator_loss=0.02,
            phi11=0.12,
            tau11=0.018,
            phi21=-0.08,
            tau21=-0.027,
        )
        scores = score_missing_reciprocal_edges(
            self.values,
            n=4,
            parameters=self.parameters,
            omega=self.omega,
            measured_s11=measured11,
            measured_s21=measured21,
            resonator_loss=0.02,
            phi11=0.12,
            tau11=0.018,
            phi21=-0.08,
            tau21=-0.027,
            max_abs_probe=0.15,
        )
        self.assertEqual((scores[0].i, scores[0].j), (0, 2))
        self.assertGreater(scores[0].loss_reduction, 0.0)
        self.assertAlmostEqual(scores[0].proposed_value, hidden_value, delta=0.02)
        self.assertLess(scores[0].probe_loss, 0.05 * scores[0].baseline_loss)

    def test_rejects_declared_candidate(self):
        measured11, measured21 = measurement_aware_response(
            self.values,
            n=4,
            parameters=self.parameters,
            omega=self.omega,
            resonator_loss=0.0,
            phi11=0.0,
            tau11=0.0,
            phi21=0.0,
            tau21=0.0,
        )
        with self.assertRaisesRegex(ValueError, "already declared"):
            score_missing_reciprocal_edges(
                self.values,
                n=4,
                parameters=self.parameters,
                omega=self.omega,
                measured_s11=measured11,
                measured_s21=measured21,
                candidates=[MatrixParameter(1, 0, "duplicate")],
            )


if __name__ == "__main__":
    unittest.main()
