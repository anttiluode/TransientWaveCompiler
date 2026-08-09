import unittest

import numpy as np

from transientwave.benchmarks import compile_irregular_arbor
from transientwave.emulator import (
    MicrocodeInterpreter,
    TW1APhysicalTile,
    TW1APhysicalTileConfig,
    run_closed_loop_training,
)


class TW1AEmulatorGradientTests(unittest.TestCase):
    def test_clean_physical_credit_matches_finite_difference(self):
        manifest = compile_irregular_arbor(810)
        cfg = TW1APhysicalTileConfig(
            weight_bits=None,
            dac_bits=None,
            adc_bits=None,
            state_noise_std=0.0,
            state_full_scale=20.0,
            clip_state=False,
            leakage_rate=0.0,
            leakage_cv=0.0,
            mirror_error=0.0,
            differential_pass_drift=0.0,
            credit_offset_fraction=0.0,
            credit_noise_fraction=0.0,
            adc_full_scale=20.0,
            seed=123,
        )
        tile = TW1APhysicalTile(manifest, cfg)
        interp = MicrocodeInterpreter(tile)
        result = interp.execute(stochastic_forward=False)
        physical = np.asarray(result["credits"], dtype=float)

        eps = 1e-5
        sample = np.linspace(0, len(tile.theta) - 1, min(8, len(tile.theta)), dtype=int)
        fd = []
        pg = []
        for idx in sample:
            plus = TW1APhysicalTile(manifest, cfg)
            minus = TW1APhysicalTile(manifest, cfg)
            plus.theta[idx] += eps
            minus.theta[idx] -= eps
            plus._rebuild_programmed_Q()
            minus._rebuild_programmed_Q()
            lp = MicrocodeInterpreter(plus).deterministic_forward_loss()
            lm = MicrocodeInterpreter(minus).deterministic_forward_loss()
            fd.append((lp - lm) / (2.0 * eps))
            pg.append(physical[idx])

        fd = np.asarray(fd)
        pg = np.asarray(pg)
        denom = np.linalg.norm(fd) + 1e-30
        rel = float(np.linalg.norm(pg - fd) / denom)
        corr = float(np.corrcoef(pg, fd)[0, 1])
        self.assertLess(rel, 2e-5, msg=f"physical-vs-FD relative error {rel}")
        self.assertGreater(corr, 0.999999, msg=f"physical-vs-FD corr {corr}")


class TW1AEmulatorLearningTests(unittest.TestCase):
    def test_preregistered_baseline_learns_across_five_arbors(self):
        reductions = []
        shuffled = []
        exact_better = 0

        for seed in range(810, 815):
            manifest = compile_irregular_arbor(seed)
            cfg = TW1APhysicalTileConfig(
                weight_bits=8,
                weight_quantizer="uniform",
                dac_bits=8,
                adc_bits=8,
                state_noise_std=0.0,
                state_full_scale=2.0,
                clip_state=True,
                leakage_rate=0.0,
                leakage_cv=0.0,
                mirror_error=0.05,
                differential_pass_drift=0.002,
                credit_offset_fraction=0.0,
                credit_noise_fraction=0.05,
                adc_full_scale=2.0,
                seed=10_000 + seed,
            )
            result = run_closed_loop_training(
                manifest,
                cfg,
                iterations=30,
                step_size=0.25,
                normalize_rms=True,
                include_shuffle=True,
                shuffle_seed=20_000 + seed,
            )
            reductions.append(result.exact_reduction)
            shuffled.append(result.shuffled_reduction)
            if result.exact_loss[-1] < result.shuffled_loss[-1]:
                exact_better += 1
            print(
                f"seed={seed} exact_R={result.exact_reduction:+.5f} "
                f"shuffle_R={result.shuffled_reduction:+.5f} "
                f"L0={result.exact_loss[0]:.6g} Lf={result.exact_loss[-1]:.6g}"
            )

        reductions = np.asarray(reductions)
        shuffled = np.asarray(shuffled)

        # Frozen in docs/HARDWARE_ENVELOPE_PREREG_V01.md before execution.
        self.assertTrue(np.all(reductions > 0.0), reductions)
        self.assertTrue(np.all(reductions >= 0.10), reductions)
        self.assertGreaterEqual(float(np.median(reductions)), 0.15)
        self.assertGreaterEqual(exact_better, 4)
        self.assertGreaterEqual(
            float(np.median(reductions) - np.median(shuffled)), 0.10
        )
        self.assertTrue(np.all(np.isfinite(reductions)))


if __name__ == "__main__":
    unittest.main()
