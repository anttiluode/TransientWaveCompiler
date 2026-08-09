import unittest

import numpy as np

from transientwave.circuit_emulator_v08_self_thermal import (
    TW1ACommonDiffSelfThermalConfig,
    TW1ACommonDiffSelfThermalTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class V08SelfThermalTests(unittest.TestCase):
    def cfg(self, b):
        return TW1ACommonDiffSelfThermalConfig(
            edge_gain_cv=0.0,
            edge_common_settling_loss=0.0,
            prev_ratio_error_std=0.0,
            prev_ratio_calibration=False,
            prev_ratio_calibration_error_std=0.0,
            state_noise_std=0.0,
            edge_unit_cap_sigma=0.03,
            edge_cunit_over_csum=0.265 / 127.0,
            edge_site_ratio_sigma=0.01,
            edge_ktc_base_fraction=1e-5,
            self_ktc_base_fraction=b,
            edge_charge_cancellation_error_std=0.005,
            seed=8818,
        )

    def manifest(self):
        return compile_temporal_order_task(818)["target"]

    def test_two_slice_total_law_is_b_sqrt_abs_self_coeff(self):
        tile = TW1ACommonDiffSelfThermalTile(self.manifest(), self.cfg(1e-5), sense_gain=1.0)
        coeff = np.asarray([0.0, 0.25, 1.0, 1.5, 3.0])
        sigma = tile.self_thermal_sigma_fraction(coeff)
        self.assertTrue(np.allclose(sigma, 1e-5 * np.sqrt(coeff), rtol=0, atol=1e-16))

    def test_sign_does_not_change_thermal_rms(self):
        tile = TW1ACommonDiffSelfThermalTile(self.manifest(), self.cfg(1e-5), sense_gain=1.0)
        coeff = np.asarray([-3.0, -1.5, -0.25, 0.25, 1.5, 3.0])
        sigma = tile.self_thermal_sigma_fraction(coeff)
        self.assertTrue(np.allclose(sigma[:3], sigma[-1:-4:-1], rtol=0, atol=1e-16))

    def test_zero_self_coefficient_has_zero_sampling_noise(self):
        tile = TW1ACommonDiffSelfThermalTile(self.manifest(), self.cfg(1e-5), sense_gain=1.0)
        sigma = tile.self_thermal_sigma_fraction(np.zeros(tile.nodes))
        self.assertTrue(np.array_equal(sigma, np.zeros(tile.nodes)))

    def test_enabling_self_thermal_does_not_redraw_static_silicon(self):
        a = TW1ACommonDiffSelfThermalTile(self.manifest(), self.cfg(0.0), sense_gain=1.0)
        b = TW1ACommonDiffSelfThermalTile(self.manifest(), self.cfg(1e-5), sense_gain=1.0)
        for name in (
            "retention",
            "self_gain",
            "self_gain_measured",
            "edge_lane_gain_a",
            "edge_lane_gain_b",
            "edge_injection_a",
            "edge_injection_b",
            "edge_cap_levels",
            "edge_site_ratio_scale",
        ):
            self.assertTrue(np.array_equal(getattr(a, name), getattr(b, name)), name)


if __name__ == "__main__":
    unittest.main()
