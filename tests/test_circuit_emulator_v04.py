import unittest

import numpy as np

from transientwave.circuit_emulator import LockstepCircuitInterpreter
from transientwave.circuit_emulator_v04 import (
    TW1ACircuitTile,
    TW1ACircuitV04Config,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class CircuitV04CalibrationTests(unittest.TestCase):
    def test_edge_inverse_programming_cancels_large_raw_gain_with_ideal_code(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV04Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            edge_gain_cv=0.20,
            edge_calibration=True,
            edge_calibration_error_std=0.0,
            self_gain_cv=0.0,
            state_full_scale=20.0,
            clip_state=False,
            seed=401,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        _, raw_edges = tile._edge_cell_decomposition()
        desired = np.asarray(
            [raw_edges[p] for p in tile.backend.physical_edges()], dtype=float
        )
        _, _, actual = tile.physical_components()
        self.assertTrue(np.allclose(actual, desired, rtol=0.0, atol=2e-12))
        self.assertGreater(float(np.std(tile.edge_gain)), 0.01)

    def test_prev_trim_cancels_raw_ratio_to_trim_resolution(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV04Config(
            prev_ratio_error_std=0.05,
            prev_ratio_calibration=True,
            prev_ratio_calibration_error_std=0.0,
            prev_trim_bits=12,
            prev_trim_range=0.25,
            seed=402,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        raw_err = float(np.max(np.abs(tile.prev_ratio_gain_raw - 1.0)))
        trimmed_err = float(np.max(np.abs(tile.prev_ratio_gain - 1.0)))
        self.assertGreater(raw_err, 1e-3)
        self.assertLess(trimmed_err, 2e-4)

    def test_terminal_clone_trim_cancels_raw_copy_gain(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV04Config(
            terminal_clone_gain_std=0.05,
            terminal_clone_calibration=True,
            terminal_clone_calibration_error_std=0.0,
            terminal_clone_trim_bits=12,
            terminal_clone_trim_range=0.25,
            seed=403,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        raw = max(
            float(np.max(np.abs(tile.clone_gain_current_raw - 1.0))),
            float(np.max(np.abs(tile.clone_gain_previous_raw - 1.0))),
        )
        trimmed = max(
            float(np.max(np.abs(tile.clone_gain_current - 1.0))),
            float(np.max(np.abs(tile.clone_gain_previous - 1.0))),
        )
        self.assertGreater(raw, 1e-3)
        self.assertLess(trimmed, 2e-4)

    def test_perfect_charge_autozero_cancels_large_raw_packets(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV04Config(
            edge_charge_raw_common_std=1e-3,
            edge_charge_raw_differential_std=5e-4,
            edge_charge_autozero=True,
            edge_charge_cancellation_error_std=0.0,
            edge_charge_residual_common_floor_std=0.0,
            edge_charge_residual_differential_floor_std=0.0,
            state_full_scale=20.0,
            seed=404,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        self.assertGreater(float(np.std(tile.edge_injection_raw_common)), 1e-4)
        self.assertTrue(np.array_equal(tile.edge_injection_common, np.zeros_like(tile.edge_injection_common)))
        self.assertTrue(np.array_equal(tile.edge_injection_diff, np.zeros_like(tile.edge_injection_diff)))
        self.assertTrue(np.array_equal(tile.edge_injection_a, tile.edge_injection_b))

    def test_v03_charge_fields_are_rejected(self):
        cfg = TW1ACircuitV04Config(edge_charge_injection_common_std=1e-5)
        with self.assertRaisesRegex(ValueError, "v0.3"):
            cfg.validate()

    def test_clean_v04_executes_finite_nonzero_credit(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV04Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            state_full_scale=20.0,
            clip_state=False,
            seed=405,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        result = LockstepCircuitInterpreter(tile).execute(stochastic_forward=False)
        credit = np.asarray(result["credits"], dtype=float)
        self.assertTrue(np.all(np.isfinite(credit)))
        self.assertGreater(float(np.linalg.norm(credit)), 0.0)


if __name__ == "__main__":
    unittest.main()
