import json
import math
import unittest
from pathlib import Path

import numpy as np

from transientwave.compiler import CompileError, compile_program, simulate_compiled, simulate_source
from transientwave.ir import program_from_dict
from transientwave.physical import compile_tw1a


ROOT = Path(__file__).resolve().parents[1]


class CompilerTests(unittest.TestCase):
    def load_example(self):
        return program_from_dict(json.loads((ROOT / "examples" / "three_node.json").read_text()))

    def load_continuous_example(self):
        return program_from_dict(
            json.loads((ROOT / "examples" / "continuous_three_node.json").read_text())
        )

    def assert_source_compiled_equivalent(self, p, tol=2e-9):
        man = compile_program(p)
        x = simulate_source(p)
        z = simulate_compiled(p, man)
        r = man["gauge"]["r"]
        scale = r ** np.arange(len(z), dtype=float)
        reconstructed = z * scale[:, None]
        rel = np.linalg.norm(reconstructed - x) / (np.linalg.norm(x) + 1e-30)
        self.assertLess(rel, tol)

    def test_damping_gauge_reconstructs_source_trajectory(self):
        self.assert_source_compiled_equivalent(self.load_example())

    def test_continuous_wave_lowering_reconstructs_discretized_source(self):
        p = self.load_continuous_example()
        man = compile_program(p)
        self.assertEqual(man["source_lowering"]["kind"], "continuous_damped_wave")
        self.assertAlmostEqual(man["source_lowering"]["a"], 0.99)
        self.assertAlmostEqual(man["source_lowering"]["drive_scale"], 0.05**2)
        self.assert_source_compiled_equivalent(p)

    def test_continuous_stiffness_edge_gets_correct_credit_scale(self):
        p = self.load_continuous_example()
        man = compile_program(p)
        r = man["gauge"]["r"]
        edge = man["trainable_edges"][0]
        self.assertEqual(edge["parameter_space"], "stiffness_H")
        self.assertAlmostEqual(edge["source_matrix_scale"], -(p.dt**2), places=14)
        self.assertAlmostEqual(edge["compiled_credit_scale"], -(p.dt**2) / r, places=14)

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

    def test_nonreciprocal_continuous_stiffness_is_rejected(self):
        d = json.loads((ROOT / "examples" / "continuous_three_node.json").read_text())
        d["dynamics"]["H"][0][1] += 1.0
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

    def test_tw1a_local_graph_routes(self):
        man = compile_tw1a(self.load_continuous_example())
        self.assertEqual(man["backend"], "tw1a-8x8-v0")
        self.assertEqual(man["physical"]["active_edges"], 2)
        self.assertEqual(man["resources"]["physical_edge_capacity"], 112)
        self.assertEqual(len(man["physical"]["trainable_edge_map"]), 2)

    def test_tw1a_rejects_mathematically_valid_nonlocal_wire(self):
        d = json.loads((ROOT / "examples" / "three_node.json").read_text())
        # Add a symmetric 0<->2 coupling. The reversible math remains legal,
        # but row-major physical nodes 0 and 2 are not four-neighbor connected.
        d["dynamics"]["M"][0][2] = 0.01
        d["dynamics"]["M"][2][0] = 0.01
        p = program_from_dict(d)
        compile_program(p)  # algebraic compiler accepts it
        with self.assertRaises(CompileError) as cm:
            compile_tw1a(p)
        self.assertEqual(cm.exception.code, "E410 ROUTING_FAILURE")


if __name__ == "__main__":
    unittest.main()
