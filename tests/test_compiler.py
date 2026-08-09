import json
import math
import unittest
from pathlib import Path

import numpy as np

from transientwave.compiler import CompileError, compile_program, simulate_compiled, simulate_source
from transientwave.ir import program_from_dict


ROOT = Path(__file__).resolve().parents[1]


class CompilerTests(unittest.TestCase):
    def load_example(self):
        return program_from_dict(json.loads((ROOT / "examples" / "three_node.json").read_text()))

    def test_damping_gauge_reconstructs_source_trajectory(self):
        p = self.load_example()
        man = compile_program(p)
        x = simulate_source(p)
        z = simulate_compiled(p, man)
        r = man["gauge"]["r"]
        scale = r ** np.arange(len(z), dtype=float)
        reconstructed = z * scale[:, None]
        rel = np.linalg.norm(reconstructed - x) / (np.linalg.norm(x) + 1e-30)
        self.assertLess(rel, 2e-9)

    def test_previous_state_transform_is_exact(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        d["state"]["initial"] = [0.2, -0.1, 0.4]
        d["state"]["initial_previous"] = [0.3, 0.5, -0.2]
        p = program_from_dict(d)
        man = compile_program(p)
        r = math.sqrt(d["dynamics"]["a"])
        np.testing.assert_allclose(
            np.asarray(man["initial_previous"]),
            r * np.asarray(d["state"]["initial_previous"]),
            atol=1e-12,
            rtol=0,
        )

    def test_nonreciprocal_operator_is_rejected(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        d["dynamics"]["M"][0][1] += 0.01
        with self.assertRaises(CompileError) as cm:
            compile_program(program_from_dict(d))
        self.assertEqual(cm.exception.code, "E101 NONRECIPROCAL")

    def test_unstable_operator_is_rejected(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        d["dynamics"]["M"][0][0] = 2.5
        with self.assertRaises(CompileError) as cm:
            compile_program(program_from_dict(d))
        self.assertEqual(cm.exception.code, "E211 STABILITY_MARGIN")

    def test_boundary_gain_is_rejected(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        d["steps"] = 500
        d["dynamics"]["a"] = 0.90
        with self.assertRaises(CompileError) as cm:
            compile_program(program_from_dict(d))
        self.assertEqual(cm.exception.code, "E305 BOUNDARY_GAIN")

    def test_reversible_program_uses_identity_gauge(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        a = d["dynamics"]["a"]
        r = math.sqrt(a)
        q = (np.asarray(d["dynamics"]["M"], dtype=float) / r).tolist()
        d["dynamics"] = {"form": "reversible_second_order", "Q": q}
        p = program_from_dict(d)
        man = compile_program(p)
        self.assertEqual(man["gauge"]["kind"], "identity")
        self.assertAlmostEqual(man["gauge"]["max_input_gain"], 1.0)

    def test_credit_scale_tracks_conformal_parameterization(self):
        p = self.load_example()
        man = compile_program(p)
        r = man["gauge"]["r"]
        self.assertAlmostEqual(
            man["trainable_edges"][0]["compiled_credit_scale"],
            -0.05 / r,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
