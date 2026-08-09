import unittest

import numpy as np

from transientwave.circuit_emulator_v05 import (
    PhaseSymmetricLockstepInterpreter,
    TW1ACircuitTile,
    TW1ACircuitV05Config,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class CircuitV05PhaseSymmetryTests(unittest.TestCase):
    def test_common_10pct_settling_is_absorbed_by_ideal_edge_calibration(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV05Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            edge_gain_cv=0.20,
            edge_calibration=True,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.10,
            edge_lane_match_std=0.0,
            state_full_scale=20.0,
            clip_state=False,
            seed=501,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        _, raw_edges = tile._edge_cell_decomposition()
        desired = np.asarray(
            [raw_edges[p] for p in tile.backend.physical_edges()], dtype=float
        )
        _, _, actual = tile.physical_components()
        self.assertTrue(np.allclose(actual, desired, rtol=0.0, atol=2e-12))
        self.assertTrue(np.allclose(tile.edge_common_settling_gain, 0.90))

    def test_lane_hold_mismatch_has_exact_common_average(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV05Config(edge_lane_match_std=0.01, seed=502)
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        avg = 0.5 * (tile.edge_lane_gain_a + tile.edge_lane_gain_b)
        self.assertTrue(np.allclose(avg, 1.0, rtol=0.0, atol=2e-16))
        self.assertGreater(float(np.std(tile.edge_lane_gain_a - tile.edge_lane_gain_b)), 1e-4)

    def test_legacy_b_only_settling_is_rejected(self):
        cfg = TW1ACircuitV05Config(edge_settling_error=0.01)
        with self.assertRaisesRegex(ValueError, "B-only"):
            cfg.validate()

    def test_legacy_ab_memory_is_rejected(self):
        cfg = TW1ACircuitV05Config(ab_edge_memory=0.01)
        with self.assertRaisesRegex(ValueError, "A->B"):
            cfg.validate()

    def test_clean_phase_symmetric_gradient_is_finite(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV05Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            state_full_scale=20.0,
            clip_state=False,
            seed=503,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        result = PhaseSymmetricLockstepInterpreter(tile).execute(stochastic_forward=False)
        credit = np.asarray(result["credits"], dtype=float)
        self.assertTrue(np.all(np.isfinite(credit)))
        self.assertGreater(float(np.linalg.norm(credit)), 0.0)


if __name__ == "__main__":
    unittest.main()
