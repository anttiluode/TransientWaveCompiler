import unittest

import numpy as np

from transientwave.emulator import MicrocodeInterpreter, TW1APhysicalTileConfig
from transientwave.emulator_v03 import (
    TW1APhysicalTile,
    _initial_raw_peak,
    recommend_sense_gain,
)
from transientwave.order_benchmarks import compile_temporal_order_task


class StaticPGATests(unittest.TestCase):
    def test_recommended_gain_is_binary_and_respects_initial_headroom(self):
        task = compile_temporal_order_task(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=8,
            dac_bits=8,
            adc_bits=8,
            state_full_scale=20.0,
            clip_state=True,
            adc_full_scale=2.0,
            seed=5,
        )
        gain = recommend_sense_gain(task, cfg)
        self.assertGreaterEqual(gain, 1.0)
        self.assertLessEqual(gain, 16384.0)
        self.assertEqual(int(gain) & (int(gain) - 1), 0)

        peak = max(
            _initial_raw_peak(task["target"], cfg),
            _initial_raw_peak(task["distractor"], cfg),
        )
        if gain > 1:
            self.assertLessEqual(peak * gain, 0.25 * cfg.adc_full_scale + 1e-12)
        if gain < 16384 and peak * (gain * 2) <= 0.25 * cfg.adc_full_scale:
            self.fail("gain selector did not choose the largest legal ladder gain")

    def test_pga_is_invisible_with_ideal_adc(self):
        task = compile_temporal_order_task(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=None,
            dac_bits=None,
            adc_bits=None,
            state_noise_std=0.0,
            state_full_scale=20.0,
            clip_state=True,
            leakage_rate=0.0,
            mirror_error=0.0,
            differential_pass_drift=0.0,
            credit_noise_fraction=0.0,
            credit_offset_fraction=0.0,
            seed=8,
        )
        a = TW1APhysicalTile(task["target"], cfg, sense_gain=1.0)
        b = TW1APhysicalTile(task["target"], cfg, sense_gain=1024.0)
        ia = MicrocodeInterpreter(a)
        ib = MicrocodeInterpreter(b)
        la = ia.deterministic_forward_loss()
        lb = ib.deterministic_forward_loss()
        self.assertAlmostEqual(la, lb, places=14)
        self.assertTrue(np.allclose(ia.forward_trace, ib.forward_trace, rtol=0, atol=1e-14))


if __name__ == "__main__":
    unittest.main()
