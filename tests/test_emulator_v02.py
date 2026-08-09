import unittest

import numpy as np

from transientwave.benchmarks import compile_irregular_arbor
from transientwave.emulator_v02 import (
    MicrocodeInterpreter,
    TW1APhysicalTile,
    TW1APhysicalTileConfig,
    signed_midtread_quantize,
)


class ZeroPreservingQuantizerTests(unittest.TestCase):
    def test_signed_midtread_has_exact_zero(self):
        for bits in (3, 4, 5, 6, 8, 10, 12):
            x = np.asarray([-1.0, -0.1, 0.0, 0.1, 1.0])
            y = signed_midtread_quantize(x, bits, 1.0)
            self.assertEqual(float(y[2]), 0.0)
            self.assertEqual(float(signed_midtread_quantize(np.asarray([0.0]), bits, 0.25)[0]), 0.0)

    def test_inactive_physical_edges_stay_off(self):
        manifest = compile_irregular_arbor(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=8,
            dac_bits=8,
            adc_bits=8,
            mirror_error=0.0,
            differential_pass_drift=0.0,
            credit_noise_fraction=0.0,
            seed=5,
        )
        tile = TW1APhysicalTile(manifest, cfg)
        src = tile.programmed_Q
        q = tile.quantized_Q()
        checked = 0
        for i, j in tile.backend.physical_edges():
            if src[i, j] == 0.0 and src[j, i] == 0.0:
                checked += 1
                self.assertEqual(float(q[i, j]), 0.0)
                self.assertEqual(float(q[j, i]), 0.0)
        self.assertGreater(checked, 0)

    def test_silent_drive_half_stays_zero(self):
        manifest = compile_irregular_arbor(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=8,
            dac_bits=8,
            adc_bits=8,
            mirror_error=0.0,
            differential_pass_drift=0.0,
            credit_noise_fraction=0.0,
            seed=6,
        )
        tile = TW1APhysicalTile(manifest, cfg)
        interp = MicrocodeInterpreter(tile)
        src = interp._forward_source_schedule()
        self.assertTrue(np.all(src[manifest["steps"] // 2 :] == 0.0))


if __name__ == "__main__":
    unittest.main()
