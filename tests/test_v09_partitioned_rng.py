import unittest

import numpy as np

from transientwave.circuit_emulator_v09_drift_kick import TW1ADriftKickConfig
from transientwave.circuit_emulator_v09_partitioned_rng import (
    PartitionedRNGInterpreter,
    TW1APartitionedRNGTile,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class PartitionedRNGTests(unittest.TestCase):
    def make_tile(self):
        task = compile_temporal_order_task(17)
        cfg = TW1ADriftKickConfig(
            seed=123,
            edge_ktc_base_fraction=2e-5,
            self_ktc_base_fraction=2e-5,
            drift_ktc_base_fraction=2e-5,
            drift_kick_common_rms_fraction=5e-6,
            drift_kick_diff_rms_fraction=5e-6,
            prev_ratio_error_std=0.0,
            prev_ratio_calibration=False,
        )
        return TW1APartitionedRNGTile(task["target"], cfg, sense_gain=1.0)

    def test_reseed_does_not_change_static_silicon(self):
        tile = self.make_tile()
        edge_units = tile.edge_cap_units.copy()
        site_scale = tile.edge_site_ratio_scale.copy()
        drift_common = tile.drift_kick_common_unit.copy()
        tile.reseed_dynamic_streams(9999)
        np.testing.assert_array_equal(tile.edge_cap_units, edge_units)
        np.testing.assert_array_equal(tile.edge_site_ratio_scale, site_scale)
        np.testing.assert_array_equal(tile.drift_kick_common_unit, drift_common)

    def test_credit_stream_independent_of_edge_thermal_draws(self):
        tile = self.make_tile()
        interp = PartitionedRNGInterpreter(tile)
        raw = np.linspace(-0.02, 0.03, len(tile.trainable))
        sigma = np.full(len(tile.backend.physical_edges()), 1e-5)

        tile.reseed_dynamic_streams(4242)
        _ = tile.draw_edge_thermal_noise(sigma)
        credit_after_edge = interp._finalize_credit(raw)

        tile.reseed_dynamic_streams(4242)
        credit_without_edge = interp._finalize_credit(raw)
        np.testing.assert_array_equal(credit_after_edge, credit_without_edge)

    def test_edge_stream_independent_of_credit_draws(self):
        tile = self.make_tile()
        interp = PartitionedRNGInterpreter(tile)
        raw = np.linspace(-0.02, 0.03, len(tile.trainable))
        sigma = np.full(len(tile.backend.physical_edges()), 1e-5)

        tile.reseed_dynamic_streams(5151)
        edge_before_credit = tile.draw_edge_thermal_noise(sigma)

        tile.reseed_dynamic_streams(5151)
        _ = interp._finalize_credit(raw)
        edge_after_credit = tile.draw_edge_thermal_noise(sigma)
        np.testing.assert_array_equal(edge_before_credit, edge_after_credit)

    def test_each_dynamic_stream_repeats_under_same_seed(self):
        tile = self.make_tile()
        sigma = np.full(len(tile.backend.physical_edges()), 1e-5)
        kself = np.full(tile.nodes, 0.01)

        tile.reseed_dynamic_streams(6161)
        a = (
            tile.draw_edge_thermal_noise(sigma),
            tile.draw_self_thermal_noise(kself),
            tile.draw_drift_thermal_noise(),
        )
        tile.reseed_dynamic_streams(6161)
        b = (
            tile.draw_edge_thermal_noise(sigma),
            tile.draw_self_thermal_noise(kself),
            tile.draw_drift_thermal_noise(),
        )
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x, y)


if __name__ == "__main__":
    unittest.main()
