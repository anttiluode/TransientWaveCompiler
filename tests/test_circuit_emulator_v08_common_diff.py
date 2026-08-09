import unittest

import numpy as np

from transientwave.circuit_emulator_v08_common_diff import (
    CommonDiffLockstepInterpreter,
    TW1ACommonDiffConfig,
    TW1ACommonDiffTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class CommonDiffV08CircuitTests(unittest.TestCase):
    def config(self):
        return TW1ACommonDiffConfig(
            weight_bits=8,
            self_bits=12,
            dac_bits=8,
            error_dac_bits=10,
            adc_bits=8,
            state_full_scale=20.0,
            state_noise_std=0.0,
            leakage_rate=0.0,
            leakage_cv=0.0,
            credit_noise_fraction=0.0,
            credit_offset_fraction=0.0,
            edge_gain_cv=0.0,
            edge_calibration=True,
            edge_calibration_error_std=0.0,
            edge_common_settling_loss=0.0,
            edge_lane_match_std=0.0,
            edge_unit_cap_sigma=0.0,
            edge_cunit_over_csum=0.255 / 127.0,
            edge_ktc_base_fraction=0.0,
            self_gain_cv=0.0,
            self_calibration=True,
            self_calibration_error_std=0.0,
            terminal_clone_gain_std=0.25,
            terminal_clone_noise_std=0.0,
            terminal_clone_calibration=True,
            terminal_clone_calibration_error_std=0.25,
            prev_ratio_error_std=0.0,
            prev_ratio_calibration=False,
            prev_ratio_calibration_error_std=0.0,
            error_dac_sign_asymmetry=0.75,
            edge_charge_raw_common_std=0.0,
            edge_charge_raw_differential_std=0.0,
            edge_charge_cancellation_error_std=0.0,
            edge_charge_residual_common_floor_std=0.0,
            edge_charge_residual_differential_floor_std=0.0,
            lcc_curvature=0.0,
            credit_accumulator_leakage=0.0,
            seed=8801,
        )

    def test_terminal_boundary_ignores_clone_and_plus_minus_sign_gain(self):
        task = compile_temporal_order_task(55)
        tile = TW1ACommonDiffTile(task["target"], self.config(), sense_gain=1.0)
        interp = CommonDiffLockstepInterpreter(tile)
        interp._run_forward(stochastic=False)
        forward_cur = interp.a_current.copy()
        forward_prev = interp.a_previous.copy()
        interp._build_error_schedule()
        qT = interp.error_schedule[tile.steps].copy()
        interp._clone_and_mirror(interp.error_schedule, stochastic=False)

        self.assertTrue(np.array_equal(interp.a_current, forward_prev))
        self.assertTrue(np.array_equal(interp.a_previous, forward_cur))
        self.assertTrue(np.array_equal(interp.b_current, qT))
        self.assertTrue(np.array_equal(interp.b_previous, np.zeros(tile.nodes)))

    def test_mutating_obsolete_clone_and_sign_fields_does_not_change_boundary(self):
        task = compile_temporal_order_task(56)
        tile = TW1ACommonDiffTile(task["target"], self.config(), sense_gain=1.0)
        interp = CommonDiffLockstepInterpreter(tile)
        interp._run_forward(stochastic=False)
        interp._build_error_schedule()
        q = interp.error_schedule.copy()
        forward_cur = interp.a_current.copy()
        forward_prev = interp.a_previous.copy()

        tile.clone_gain_current[:] = 123.0
        tile.clone_gain_previous[:] = -77.0
        object.__setattr__(tile.config, "error_dac_sign_asymmetry", 0.99)
        interp._clone_and_mirror(q, stochastic=False)

        self.assertTrue(np.array_equal(interp.a_current, forward_prev))
        self.assertTrue(np.array_equal(interp.a_previous, forward_cur))
        self.assertTrue(np.array_equal(interp.b_current, q[tile.steps]))
        self.assertTrue(np.array_equal(interp.b_previous, np.zeros(tile.nodes)))


if __name__ == "__main__":
    unittest.main()
