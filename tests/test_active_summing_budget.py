import math
import unittest

from transientwave.active_summing_budget import (
    CostAssumptions,
    edge_colored_beta,
    edge_parallel_beta,
    finite_dc_gain_error,
    required_gbw,
    required_open_loop_gain,
    self_packet_beta,
    state_cap_area_summary,
    state_capacitance_for_ktc,
)


class ActiveSummingBudgetTests(unittest.TestCase):
    def test_ktc_scalar_formula(self):
        c = state_capacitance_for_ktc(3e-5, 1.0, temperature_k=300.0)
        self.assertAlmostEqual(c, 4.601e-12, delta=0.01e-12)

    def test_claude_area_claim_is_not_silently_baked_in(self):
        # With the scalar b=sqrt(kT/C)/VFS law, b=3e-5 at 1 V is about
        # 4.6 pF, not 1.15 pF.  Keep this numerical identity pinned because
        # area/crossover scales directly with it.
        summary = state_cap_area_summary(3e-5, CostAssumptions())
        self.assertGreater(summary["state_cap_area_mm2"], 1.1)
        self.assertLess(summary["state_cap_area_mm2"], 1.3)
        self.assertGreater(summary["tape_crossover_steps_state_caps_only"], 850)
        self.assertLess(summary["tape_crossover_steps_state_caps_only"], 1000)

    def test_edge_coloring_improves_feedback_factor(self):
        self.assertGreater(edge_colored_beta(), edge_parallel_beta())
        self.assertAlmostEqual(edge_colored_beta(), 1.0 / 1.255, places=12)
        self.assertAlmostEqual(edge_parallel_beta(), 1.0 / 2.02, places=12)

    def test_self_slicing_improves_feedback_factor(self):
        self.assertAlmostEqual(self_packet_beta(slices=1), 0.25)
        self.assertGreater(self_packet_beta(slices=4), 0.5)

    def test_300mhz_covers_direct_self_packet_at_20ns_to_sub_permille(self):
        beta = self_packet_beta(slices=1)
        needed = required_gbw(1e-3, beta, 20e-9)
        self.assertLess(needed, 300e6)

    def test_a0_1e5_is_far_below_permille_static_error_even_at_beta_point2(self):
        self.assertLess(finite_dc_gain_error(1e5, 0.2), 1e-4)
        self.assertLess(required_open_loop_gain(1e-3, 0.2), 5.1e3)


if __name__ == "__main__":
    unittest.main()
