import unittest

import numpy as np

from transientwave.circuit_emulator_v07_active_summing import (
    TW1AActiveSummingConfig,
    TW1AActiveSummingTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class ActiveSummingV07Tests(unittest.TestCase):
    def cfg(self, **updates):
        kwargs = dict(
            edge_gain_cv=0.0,
            edge_common_settling_loss=0.0,
            prev_ratio_error_std=0.0,
            prev_ratio_calibration=False,
            prev_ratio_calibration_error_std=0.0,
            state_noise_std=0.0,
            edge_unit_cap_sigma=0.0,
            edge_cunit_over_csum=0.255 / 127.0,
            edge_ktc_base_fraction=1e-5,
            seed=77,
        )
        kwargs.update(updates)
        return TW1AActiveSummingConfig(**kwargs)

    def manifest(self):
        return compile_temporal_order_task(41)["target"]

    def test_legacy_edge_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cfg(edge_gain_cv=0.01).validate()

    def test_legacy_common_settling_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cfg(edge_common_settling_loss=0.01).validate()

    def test_legacy_prev_ratio_error_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cfg(prev_ratio_error_std=1e-4).validate()

    def test_nominal_codebook_is_direct_capacitor_ratio(self):
        tile = TW1AActiveSummingTile(self.manifest(), self.cfg(), sense_gain=1.0)
        self.assertAlmostEqual(tile.edge_cap_levels[0, 0], 0.0, places=15)
        self.assertAlmostEqual(tile.edge_cap_levels[0, -1], 0.255, places=12)
        self.assertAlmostEqual(tile.nominal_edge_full_scale, 0.255, places=12)
        self.assertGreater(tile.minimum_edge_full_scale, 0.25)

    def test_history_coefficient_is_exact_topological_minus_one(self):
        tile = TW1AActiveSummingTile(self.manifest(), self.cfg(), sense_gain=1.0)
        self.assertTrue(np.array_equal(tile.prev_ratio_gain, np.ones(tile.nodes)))

    def test_active_thermal_law_has_no_passive_sharing_denominator(self):
        tile = TW1AActiveSummingTile(self.manifest(), self.cfg(), sense_gain=1.0)
        # Ask the helper about a synthetic max-code vector.  With raw transfer
        # gain exactly one, every edge is code 127 and alpha=0.255.
        amounts = np.full(len(tile.backend.physical_edges()), 0.255)
        sigma = tile.edge_thermal_sigma_fraction(amounts)
        expected = 1e-5 * np.sqrt(0.255)
        self.assertTrue(np.allclose(sigma, expected, rtol=0, atol=1e-15))

    def test_three_percent_fabrication_keeps_full_scale_headroom_for_fixed_seed(self):
        tile = TW1AActiveSummingTile(
            self.manifest(), self.cfg(edge_unit_cap_sigma=0.03, seed=1234), sense_gain=1.0
        )
        self.assertTrue(tile.all_edge_codebooks_monotonic)
        self.assertGreater(tile.minimum_edge_full_scale, 0.25)


if __name__ == "__main__":
    unittest.main()
