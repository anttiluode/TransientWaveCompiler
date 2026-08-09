import unittest

import numpy as np

from transientwave.emulator import MicrocodeInterpreter, TW1APhysicalTileConfig
from transientwave.emulator_v02 import TW1APhysicalTile
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import contrast_from_energies, contrast_gradient


class TemporalOrderTaskTests(unittest.TestCase):
    def test_target_and_distractor_share_hardware_and_drive_energy(self):
        task = compile_temporal_order_task(810)
        t = task["target"]
        d = task["distractor"]

        self.assertTrue(np.array_equal(np.asarray(t["Q"]), np.asarray(d["Q"])))
        self.assertEqual(t["trainable_edges"], d["trainable_edges"])

        def compiled_drive_energy(manifest):
            total = 0.0
            for p in manifest["ports"]:
                if p["kind"] == "drive":
                    w = np.asarray(p["compiled_waveform"], dtype=float)
                    total += float(np.dot(w, w))
            return total

        self.assertAlmostEqual(
            compiled_drive_energy(t), compiled_drive_energy(d), places=12
        )
        self.assertNotEqual(task["metadata"]["leaf_a"], task["metadata"]["leaf_b"])
        self.assertNotEqual(task["metadata"]["leaf_a"], 0)
        self.assertNotEqual(task["metadata"]["leaf_b"], 0)

    def test_clean_combined_physical_credit_matches_contrast_finite_difference(self):
        task = compile_temporal_order_task(810)
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
            seed=1234,
        )

        tt = TW1APhysicalTile(task["target"], cfg)
        td = TW1APhysicalTile(task["distractor"], cfg)
        td.theta = tt.theta.copy()
        td._rebuild_programmed_Q()

        rt = MicrocodeInterpreter(tt).execute(stochastic_forward=False)
        rd = MicrocodeInterpreter(td).execute(stochastic_forward=False)
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
                a = TW1APhysicalTile(task["target"], cfg)
                b = TW1APhysicalTile(task["distractor"], cfg)
                a.theta[idx] += delta
                b.theta[idx] += delta
                a._rebuild_programmed_Q()
                b._rebuild_programmed_Q()
                ea = MicrocodeInterpreter(a).deterministic_forward_loss()
                eb = MicrocodeInterpreter(b).deterministic_forward_loss()
                return contrast_from_energies(ea, eb)

            fd.append((contrast_at(eps) - contrast_at(-eps)) / (2.0 * eps))
            pg.append(physical[idx])

        fd = np.asarray(fd, dtype=float)
        pg = np.asarray(pg, dtype=float)
        rel = float(np.linalg.norm(pg - fd) / (np.linalg.norm(fd) + 1e-30))
        corr = float(np.corrcoef(pg, fd)[0, 1])
        self.assertLess(rel, 2e-5, msg=f"relative L2={rel}")
        self.assertGreater(corr, 0.999999, msg=f"corr={corr}")


if __name__ == "__main__":
    unittest.main()
