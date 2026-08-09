import unittest

import numpy as np

from transientwave.circuit_emulator_v03 import (
    LockstepCircuitInterpreter,
    TW1ACircuitTile,
    TW1ACircuitV03Config,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class CircuitV03StructureTests(unittest.TestCase):
    def test_legacy_independent_charge_injection_is_rejected_in_balanced_mode(self):
        cfg = TW1ACircuitV03Config(edge_charge_injection_std=1e-5)
        with self.assertRaisesRegex(ValueError, "legacy independent"):
            cfg.validate()

    def test_perfect_self_calibration_cancels_large_raw_gain_mismatch(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV03Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            self_gain_cv=0.20,
            self_calibration=True,
            self_calibration_error_std=0.0,
            state_full_scale=20.0,
            clip_state=False,
            seed=17,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        desired, _ = tile._edge_cell_decomposition()
        qself, _, _ = tile.physical_components()
        self.assertTrue(np.allclose(qself, desired, atol=2e-12, rtol=0.0))
        self.assertGreater(float(np.std(tile.self_gain)), 0.01)

    def test_balanced_charge_injection_splits_common_and_differential_parts(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV03Config(
            edge_charge_injection_common_std=1e-4,
            edge_charge_injection_differential_std=2e-5,
            state_full_scale=20.0,
            seed=23,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        common = 0.5 * (tile.edge_injection_a + tile.edge_injection_b)
        diff = 0.5 * (tile.edge_injection_a - tile.edge_injection_b)
        self.assertTrue(np.allclose(common, tile.edge_injection_common, atol=0, rtol=0))
        self.assertTrue(np.allclose(diff, tile.edge_injection_diff, atol=1e-18, rtol=0))

    def test_common_only_edge_injection_is_identical_between_reverse_lanes(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV03Config(
            edge_charge_injection_common_std=1e-4,
            edge_charge_injection_differential_std=0.0,
            state_full_scale=20.0,
            seed=29,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        self.assertTrue(np.array_equal(tile.edge_injection_a, tile.edge_injection_b))

    def test_clean_v03_executes_finite_credit(self):
        task = compile_temporal_order_task(810)
        cfg = TW1ACircuitV03Config(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            state_full_scale=20.0,
            clip_state=False,
            seed=31,
        )
        tile = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        result = LockstepCircuitInterpreter(tile).execute(stochastic_forward=False)
        credit = np.asarray(result["credits"], dtype=float)
        self.assertTrue(np.all(np.isfinite(credit)))
        self.assertGreater(float(np.linalg.norm(credit)), 0.0)


if __name__ == "__main__":
    unittest.main()
