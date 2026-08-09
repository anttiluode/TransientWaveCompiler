import unittest

import numpy as np

from transientwave.circuit_emulator_v08_site_ratio import (
    TW1ACommonDiffSiteConfig,
    TW1ACommonDiffSiteTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class V08SiteRatioTests(unittest.TestCase):
    def config(self, sigma):
        return TW1ACommonDiffSiteConfig(
            edge_gain_cv=0.0,
            edge_common_settling_loss=0.0,
            prev_ratio_error_std=0.0,
            prev_ratio_calibration=False,
            prev_ratio_calibration_error_std=0.0,
            state_noise_std=0.0,
            edge_unit_cap_sigma=0.03,
            edge_cunit_over_csum=0.265 / 127.0,
            edge_site_ratio_sigma=sigma,
            edge_ktc_base_fraction=1e-5,
            seed=8808,
        )

    def manifest(self):
        return compile_temporal_order_task(88)["target"]

    def test_site_axis_does_not_redraw_existing_disorder(self):
        a = TW1ACommonDiffSiteTile(self.manifest(), self.config(0.0), sense_gain=1.0)
        b = TW1ACommonDiffSiteTile(self.manifest(), self.config(0.01), sense_gain=1.0)
        for name in (
            "retention",
            "self_gain",
            "self_gain_measured",
            "edge_lane_gain_a",
            "edge_lane_gain_b",
            "edge_injection_a",
            "edge_injection_b",
            "clone_gain_current",
            "clone_gain_previous",
        ):
            self.assertTrue(np.array_equal(getattr(a, name), getattr(b, name)), name)
        self.assertFalse(np.array_equal(a.edge_site_ratio_scale, b.edge_site_ratio_scale))

    def test_zero_site_sigma_is_unity_scale(self):
        tile = TW1ACommonDiffSiteTile(self.manifest(), self.config(0.0), sense_gain=1.0)
        self.assertTrue(np.array_equal(tile.edge_site_ratio_scale, np.ones(112)))

    def test_measured_codebook_contains_site_scale(self):
        tile = TW1ACommonDiffSiteTile(self.manifest(), self.config(0.01), sense_gain=1.0)
        # Reconstruct the unscaled active-ratio codebook from the stored unit sums.
        nominal = tile.edge_selected_capacitance_codes * (0.265 / 127.0)
        self.assertTrue(
            np.allclose(
                tile.edge_cap_levels,
                nominal * tile.edge_site_ratio_scale[:, None],
                rtol=2e-15,
                atol=2e-15,
            )
        )

    def test_selected_thermal_ratio_uses_scaled_physical_level(self):
        tile = TW1ACommonDiffSiteTile(self.manifest(), self.config(0.01), sense_gain=1.0)
        # Program maximum available level at every edge; true edge gain is unity
        # in v0.8 active-ratio physics, so selected alpha should be the scaled
        # code-127 physical ratio itself.
        amounts = tile.edge_cap_levels[:, -1].copy()
        alpha = tile.edge_selected_cap_ratios(amounts)
        self.assertTrue(np.allclose(alpha, tile.edge_cap_levels[:, -1], rtol=0, atol=1e-15))


if __name__ == "__main__":
    unittest.main()
