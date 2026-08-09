import unittest

import numpy as np

from transientwave.circuit_emulator_v05_edge_thermal import (
    TW1AEdgeThermalConfig,
    TW1AEdgeThermalTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class EdgeThermalNoiseTests(unittest.TestCase):
    def test_legacy_full_node_noise_is_rejected(self):
        cfg = TW1AEdgeThermalConfig(state_noise_std=1e-6)
        with self.assertRaisesRegex(ValueError, "legacy independent"):
            cfg.validate()

    def test_zero_edge_code_has_zero_thermal_packet_sigma(self):
        task = compile_temporal_order_task(810)
        cfg = TW1AEdgeThermalConfig(
            state_noise_std=0.0,
            edge_ktc_base_fraction=1e-3,
            edge_unit_cap_sigma=0.03,
            seed=801,
        )
        tile = TW1AEdgeThermalTile(task["target"], cfg, sense_gain=1.0)
        zero = np.zeros(len(tile.backend.physical_edges()), dtype=float)
        self.assertTrue(np.array_equal(tile.edge_selected_cap_ratios(zero), np.zeros_like(zero)))
        self.assertTrue(np.array_equal(tile.edge_thermal_sigma_fraction(zero), np.zeros_like(zero)))

    def test_thermal_packet_is_equal_opposite_over_tile(self):
        task = compile_temporal_order_task(810)
        cfg = TW1AEdgeThermalConfig(
            state_noise_std=0.0,
            edge_ktc_base_fraction=1e-3,
            edge_unit_cap_sigma=0.03,
            seed=802,
        )
        tile = TW1AEdgeThermalTile(task["target"], cfg, sense_gain=1.0)
        _, _, amounts = tile.physical_components()
        noise = tile.edge_thermal_node_noise(amounts)
        self.assertAlmostEqual(float(np.sum(noise)), 0.0, places=14)

    def test_sigma_uses_charge_sharing_attenuation(self):
        task = compile_temporal_order_task(810)
        base = 2e-4
        cfg = TW1AEdgeThermalConfig(
            state_noise_std=0.0,
            edge_ktc_base_fraction=base,
            edge_unit_cap_sigma=0.0,
            edge_gain_cv=0.0,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            seed=803,
        )
        tile = TW1AEdgeThermalTile(task["target"], cfg, sense_gain=1.0)
        # Construct a synthetic vector corresponding to full-scale physical code
        # on every edge.  With nominal Cunit/Cstate=1e-3, alpha=0.127.
        full = tile.edge_cap_levels[:, -1] * tile.edge_effective_gain_raw
        alpha = tile.edge_selected_cap_ratios(full)
        sigma = tile.edge_thermal_sigma_fraction(full)
        expected = base * np.sqrt(alpha) / (1.0 + 2.0 * alpha)
        self.assertTrue(np.allclose(alpha, 0.127, rtol=0, atol=2e-14))
        self.assertTrue(np.allclose(sigma, expected, rtol=0, atol=2e-14))
        self.assertLess(float(np.max(sigma)), base * 0.30)


if __name__ == "__main__":
    unittest.main()
