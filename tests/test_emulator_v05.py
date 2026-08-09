import unittest

import numpy as np

from transientwave.emulator import TW1APhysicalTileConfig
from transientwave.emulator_v05 import TW1APhysicalTile
from transientwave.order_benchmarks import compile_temporal_order_task


class EdgeCellQuantizationTests(unittest.TestCase):
    def test_one_edge_code_stamps_exact_rank_one_matrix(self):
        task = compile_temporal_order_task(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=8,
            dac_bits=None,
            adc_bits=None,
            state_full_scale=20.0,
            clip_state=True,
            seed=1,
        )
        tile = TW1APhysicalTile(task["target"], cfg, sense_gain=1.0)
        before = tile.quantized_Q()
        amounts_before = tile.quantized_edge_amounts()

        # Find a trainable edge and move theta until its physical code changes.
        k = 0
        i, j = tile._train_pairs[k]
        pair = (i, j)
        start = amounts_before[pair]
        for delta in np.linspace(0.05, 2.0, 80):
            tile.theta[k] += float(delta)
            tile._rebuild_programmed_Q()
            after_amounts = tile.quantized_edge_amounts()
            if after_amounts[pair] != start:
                break
            tile.theta[k] -= float(delta)
            tile._rebuild_programmed_Q()
        else:
            self.fail("could not cross an edge-cell code boundary")

        after = tile.quantized_Q()
        da = after_amounts[pair] - start
        expected = np.zeros_like(before)
        expected[i, i] += da
        expected[j, j] += da
        expected[i, j] -= da
        expected[j, i] -= da
        self.assertTrue(np.allclose(after - before, expected, rtol=0, atol=1e-14))

    def test_disabled_physical_edges_remain_exactly_zero(self):
        task = compile_temporal_order_task(810)
        cfg = TW1APhysicalTileConfig(weight_bits=5, dac_bits=None, adc_bits=None, seed=2)
        tile = TW1APhysicalTile(task["target"], cfg, sense_gain=1.0)
        active = {tuple(map(int, e["edge"])) for e in tile.trainable}
        amounts = tile.quantized_edge_amounts()
        for pair, amount in amounts.items():
            if pair not in active:
                self.assertEqual(amount, 0.0, msg=f"inactive edge {pair} was programmed")

    def test_ideal_precision_matches_compiled_Q(self):
        task = compile_temporal_order_task(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=None,
            dac_bits=None,
            adc_bits=None,
            state_full_scale=20.0,
            clip_state=False,
            seed=3,
        )
        tile = TW1APhysicalTile(task["target"], cfg, sense_gain=1.0)
        self.assertTrue(
            np.allclose(tile.quantized_Q(), np.asarray(task["target"]["Q"], dtype=float), rtol=0, atol=2e-12)
        )


if __name__ == "__main__":
    unittest.main()
