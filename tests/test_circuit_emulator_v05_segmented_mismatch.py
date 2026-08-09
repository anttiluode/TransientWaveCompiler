import unittest

import numpy as np

from transientwave.circuit_emulator_v05_segmented_mismatch import (
    TW1ASegmentedMismatchConfig,
    TW1ASegmentedMismatchTile,
    segmented_capacitance_codes,
)
from transientwave.circuit_emulator_v05_capcodebook import capacitor_magnitude_levels
from transientwave.order_benchmarks import compile_temporal_order_task


class SegmentedMismatchCodebookTests(unittest.TestCase):
    def test_nominal_segmented_codebook_matches_nominal_c0c_levels(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ASegmentedMismatchConfig(
            weight_bits=8,
            edge_unit_cap_sigma=0.0,
            edge_gain_cv=0.0,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            self_gain_cv=0.0,
            self_calibration_error_std=0.0,
            seed=701,
        )
        tile = TW1ASegmentedMismatchTile(task["target"], cfg, sense_gain=1.0)
        nominal = capacitor_magnitude_levels(0.25, cunit_over_csum=1e-3)
        self.assertTrue(np.allclose(tile.edge_cap_levels, nominal[None, :], rtol=0, atol=2e-14))

    def test_segmented_nominal_selection_equals_code_m_units(self):
        units = np.ones((3, 127), dtype=float)
        caps = segmented_capacitance_codes(units)
        expected = np.arange(128, dtype=float)
        self.assertTrue(np.array_equal(caps, np.repeat(expected[None, :], 3, axis=0)))

    def test_three_percent_draw_is_edge_specific_and_exact_zero(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ASegmentedMismatchConfig(
            edge_unit_cap_sigma=0.03,
            edge_gain_cv=0.0,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            self_gain_cv=0.0,
            self_calibration_error_std=0.0,
            seed=702,
        )
        tile = TW1ASegmentedMismatchTile(task["target"], cfg, sense_gain=1.0)
        self.assertTrue(np.array_equal(tile.edge_cap_levels[:, 0], np.zeros(tile.edge_cap_levels.shape[0])))
        self.assertGreater(float(np.max(np.abs(tile.edge_cap_levels[0] - tile.edge_cap_levels[1]))), 1e-5)
        self.assertTrue(tile.all_edge_codebooks_monotonic)

    def test_programmed_edges_land_on_their_own_measured_levels(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ASegmentedMismatchConfig(
            weight_bits=8,
            edge_unit_cap_sigma=0.03,
            edge_gain_cv=0.0,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            self_gain_cv=0.0,
            self_calibration_error_std=0.0,
            seed=703,
        )
        tile = TW1ASegmentedMismatchTile(task["target"], cfg, sense_gain=1.0)
        _, _, amounts = tile.physical_components()
        for k, value in enumerate(amounts):
            err = np.min(np.abs(tile.edge_cap_levels[k] - abs(value)))
            self.assertLess(float(err), 1e-13)


if __name__ == "__main__":
    unittest.main()
