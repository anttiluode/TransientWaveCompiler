import unittest

import numpy as np

from transientwave.circuit_emulator import (
    LockstepCircuitInterpreter,
    TW1ACircuitEmulatorConfig,
    TW1ACircuitTile,
    copy_circuit_disorder,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import contrast_from_energies, contrast_gradient


class CircuitNativeGradientTests(unittest.TestCase):
    def ideal_config(self, seed=1234):
        return TW1ACircuitEmulatorConfig(
            weight_bits=None,
            self_bits=None,
            dac_bits=None,
            error_dac_bits=None,
            adc_bits=None,
            state_noise_std=0.0,
            state_full_scale=20.0,
            clip_state=False,
            leakage_rate=0.0,
            leakage_cv=0.0,
            credit_offset_fraction=0.0,
            credit_noise_fraction=0.0,
            edge_gain_cv=0.0,
            self_gain_cv=0.0,
            terminal_clone_gain_std=0.0,
            terminal_clone_noise_std=0.0,
            edge_settling_error=0.0,
            ab_edge_memory=0.0,
            edge_charge_injection_std=0.0,
            prev_ratio_error_std=0.0,
            error_dac_sign_asymmetry=0.0,
            lcc_curvature=0.0,
            credit_accumulator_leakage=0.0,
            adc_full_scale=20.0,
            seed=seed,
        )

    def test_legacy_long_pass_errors_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "mirror_error"):
            TW1ACircuitEmulatorConfig(mirror_error=0.01).validate()
        with self.assertRaisesRegex(ValueError, "differential_pass_drift"):
            TW1ACircuitEmulatorConfig(differential_pass_drift=1e-4).validate()

    def test_zero_error_lockstep_credit_matches_finite_difference(self):
        task = compile_temporal_order_task(810)
        cfg = self.ideal_config()

        tt = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
        td = TW1ACircuitTile(task["distractor"], cfg, sense_gain=1.0)
        copy_circuit_disorder(tt, td)
        td.theta = tt.theta.copy()
        td._rebuild_programmed_Q()

        rt = LockstepCircuitInterpreter(tt).execute(stochastic_forward=False)
        rd = LockstepCircuitInterpreter(td).execute(stochastic_forward=False)
        physical = contrast_gradient(
            float(rt["objective"]),
            float(rd["objective"]),
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
        )

        eps = 1e-5
        sample = np.linspace(0, len(tt.theta) - 1, min(10, len(tt.theta)), dtype=int)
        fd = []
        pg = []

        for idx in sample:
            def contrast_at(delta):
                a = TW1ACircuitTile(task["target"], cfg, sense_gain=1.0)
                b = TW1ACircuitTile(task["distractor"], cfg, sense_gain=1.0)
                copy_circuit_disorder(a, b)
                a.theta[idx] += delta
                b.theta[idx] += delta
                a._rebuild_programmed_Q()
                b._rebuild_programmed_Q()
                ea = LockstepCircuitInterpreter(a).deterministic_forward_loss()
                eb = LockstepCircuitInterpreter(b).deterministic_forward_loss()
                return contrast_from_energies(ea, eb)

            fd.append((contrast_at(eps) - contrast_at(-eps)) / (2.0 * eps))
            pg.append(physical[idx])

        fd = np.asarray(fd, dtype=float)
        pg = np.asarray(pg, dtype=float)
        rel = float(np.linalg.norm(pg - fd) / (np.linalg.norm(fd) + 1e-30))
        corr = float(np.corrcoef(pg, fd)[0, 1])
        self.assertLessEqual(rel, 2e-5, msg=f"relative L2={rel}")
        self.assertGreaterEqual(corr, 0.999999, msg=f"corr={corr}")


class CircuitNativeReferenceLearningTests(unittest.TestCase):
    def test_preregistered_quantized_reference_learns_five_fresh_arbors(self):
        improvements = []
        gaps = []
        final_wins = 0

        for seed in range(1100, 1105):
            task = compile_temporal_order_task(seed)
            cfg = TW1ACircuitEmulatorConfig(
                weight_bits=8,
                self_bits=12,
                dac_bits=8,
                error_dac_bits=10,
                adc_bits=8,
                state_noise_std=0.0,
                state_full_scale=20.0,
                clip_state=True,
                leakage_rate=0.0,
                leakage_cv=0.0,
                credit_offset_fraction=0.0,
                credit_noise_fraction=0.0,
                adc_full_scale=2.0,
                seed=40_000 + seed,
            )
            result, gain = run_order_contrast_training(
                task,
                cfg,
                iterations=30,
                step_size=0.20,
            )
            improvements.append(result.exact_improvement)
            gaps.append(result.placement_gap)
            final_wins += int(result.exact_contrast[-1] > result.shuffled_contrast[-1])
            print(
                f"circuit-ref seed={seed} PGA={gain:g} "
                f"DeltaC={result.exact_improvement:+.6f} "
                f"gap={result.placement_gap:+.6f} "
                f"Cfinal={result.exact_contrast[-1]:+.6f} "
                f"Cshuffle={result.shuffled_contrast[-1]:+.6f}"
            )

        self.assertEqual(sum(v >= 0.10 for v in improvements), 5, msg=str(improvements))
        self.assertEqual(final_wins, 5, msg=f"final wins={final_wins}, gaps={gaps}")
        self.assertGreaterEqual(float(np.median(gaps)), 0.25, msg=str(gaps))


if __name__ == "__main__":
    unittest.main()
