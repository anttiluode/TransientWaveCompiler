import unittest

import numpy as np

from transientwave.circuit_architecture import (
    TW1ACircuitProfile,
    bits_for_absolute_lsb,
    decompose_local_symmetric_q,
    gradient_hold_seconds,
    gradient_traversal_ticks,
    grid_edges,
    max_grid_degree,
    recompose_local_symmetric_q,
    required_self_path_full_scale,
    retention_time_constant_seconds,
    self_bits_matching_edge_lsb,
    signed_midtread_positive_codes,
)


class CircuitArchitectureTests(unittest.TestCase):
    def test_grid_has_64_nodes_and_112_edges(self):
        p = TW1ACircuitProfile()
        self.assertEqual(p.nodes, 64)
        self.assertEqual(p.edges, 112)
        self.assertEqual(len(grid_edges()), 112)
        self.assertEqual(max_grid_degree(), 4)

    def test_rank_one_edge_plus_self_decomposition_is_exact(self):
        rng = np.random.default_rng(23)
        n = 16
        edges = grid_edges(4, 4)
        Q = np.diag(rng.uniform(-1.2, 1.2, size=n))
        for i, j in edges:
            q = rng.uniform(-0.2, 0.2)
            Q[i, j] = q
            Q[j, i] = q
        d, a = decompose_local_symmetric_q(Q, edges=edges)
        recovered = recompose_local_symmetric_q(d, a)
        self.assertTrue(np.allclose(recovered, Q, atol=1e-12, rtol=0.0))

    def test_nonlocal_q_is_rejected(self):
        Q = np.eye(4)
        Q[0, 3] = Q[3, 0] = 0.1
        with self.assertRaisesRegex(ValueError, "nonlocal coupling"):
            decompose_local_symmetric_q(Q, edges=[(0, 1), (1, 2), (2, 3)])

    def test_self_path_range_exposes_rank_one_diagonal_stamp(self):
        self.assertAlmostEqual(required_self_path_full_scale(), 2.95, places=12)

    def test_12bit_self_path_matches_8bit_edge_absolute_lsb(self):
        edge_lsb = 0.25 / signed_midtread_positive_codes(8)
        self.assertEqual(
            self_bits_matching_edge_lsb(
                edge_bits=8, edge_full_scale=0.25, self_full_scale=3.0
            ),
            12,
        )
        self_lsb = 3.0 / signed_midtread_positive_codes(12)
        self.assertLessEqual(self_lsb, edge_lsb)
        self.assertEqual(bits_for_absolute_lsb(3.0, edge_lsb), 12)

    def test_dual_reverse_halves_sequential_reverse_traversal_count(self):
        self.assertEqual(gradient_traversal_ticks(210, objective_terms=1), 420)
        self.assertEqual(gradient_traversal_ticks(210, objective_terms=2), 840)

    def test_parameter_hold_window_is_submillisecond_at_1mhz_for_210_step_contrast(self):
        hold = gradient_hold_seconds(210, 1_000_000.0, objective_terms=2)
        self.assertGreater(hold, 0.00084)
        self.assertLess(hold, 0.00085)

    def test_leakage_recommendation_maps_to_about_one_millisecond_tau_at_1mhz(self):
        tau = retention_time_constant_seconds(1_000_000.0, 0.001)
        self.assertAlmostEqual(tau, 0.0009995, places=8)

    def test_reference_profile_enforces_structural_coherence(self):
        p = TW1ACircuitProfile()
        p.validate()
        c = p.coherence_contract()
        self.assertIn("lane A evolves F+A", c["reverse_pair"])
        self.assertIn("writes inhibited", c["edge_code_storage"])
        self.assertEqual(p.differential_state_registers, 256)
        self.assertEqual(p.scalar_sample_capacitors_minimum, 512)
        self.assertEqual(len(p.tick_microphases()), 8)


if __name__ == "__main__":
    unittest.main()
