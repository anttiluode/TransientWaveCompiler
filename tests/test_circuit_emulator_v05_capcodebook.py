import unittest

import numpy as np

from transientwave.circuit_emulator_v05 import TW1ACircuitV05Config
from transientwave.circuit_emulator_v05_capcodebook import (
    TW1ACapCodebookTile,
    capacitor_magnitude_levels,
    nearest_signed_codebook,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class CapacitorCodebookTests(unittest.TestCase):
    def test_codebook_is_exact_zero_monotonic_and_fullscale(self):
        levels = capacitor_magnitude_levels(0.25)
        self.assertEqual(levels[0], 0.0)
        self.assertTrue(np.all(np.diff(levels) > 0.0))
        self.assertAlmostEqual(float(levels[-1]), 0.25, places=14)

    def test_c0c_spacing_is_not_uniform(self):
        levels = capacitor_magnitude_levels(0.25)
        uniform64 = 0.25 * 64.0 / 127.0
        # C0c charge sharing compresses the upper end, so code 64 lies above
        # the value of an ideal uniformly spaced 7-bit magnitude ladder.
        self.assertGreater(float(levels[64]), uniform64 * 1.05)
        self.assertLess(float(levels[64]), uniform64 * 1.20)

    def test_signed_nearest_quantizer_preserves_exact_zero_and_sign(self):
        levels = capacitor_magnitude_levels(0.25)
        x = np.asarray([0.0, 0.001, -0.001, 0.12, -0.12, 1.0, -1.0])
        q = nearest_signed_codebook(x, levels)
        self.assertEqual(q[0], 0.0)
        self.assertGreater(q[1], 0.0)
        self.assertLess(q[2], 0.0)
        self.assertGreater(q[3], 0.0)
        self.assertLess(q[4], 0.0)
        self.assertEqual(q[5], levels[-1])
        self.assertEqual(q[6], -levels[-1])

    def test_tile_uses_a_physical_c0c_level_for_each_edge(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV05Config(
            weight_bits=8,
            self_bits=12,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            edge_gain_cv=0.0,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            self_gain_cv=0.0,
            self_calibration_error_std=0.0,
            state_full_scale=20.0,
            clip_state=False,
            seed=601,
        )
        tile = TW1ACapCodebookTile(task["target"], cfg, sense_gain=1.0)
        levels = capacitor_magnitude_levels(
            max(abs(tile.backend.q_edge_min), abs(tile.backend.q_edge_max))
        )
        _, _, amounts = tile.physical_components()
        for value in amounts:
            self.assertLess(float(np.min(np.abs(levels - abs(value)))), 1e-13)


if __name__ == "__main__":
    unittest.main()
