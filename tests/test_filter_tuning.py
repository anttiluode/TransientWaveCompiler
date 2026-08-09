import contextlib
import io
import json
import tempfile
import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.filter_cli import main as filter_cli_main
from transientwave.filter_tuning import parse_filter_spec, tune_filter_spec
from transientwave.generalized_coupling_matrix import generalized_scattering


class FilterTuningTests(unittest.TestCase):
    def make_spec(self):
        parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        target_values = np.array([1.0, 0.62, 1.0], dtype=float)
        target = matrix_from_parameters(4, parameters, target_values)
        omega = np.linspace(-2.5, 2.5, 121)
        s11, s21 = generalized_scattering(target, omega)
        return {
            "name": "two-resonator-test",
            "model": "explicit-port",
            "nodes": 4,
            "parameters": [
                {"name": "mS1", "i": 0, "j": 1, "initial": 0.72, "min": 0.3, "max": 1.4},
                {"name": "m12", "i": 1, "j": 2, "initial": 0.88, "min": 0.2, "max": 1.2},
                {"name": "m2L", "i": 2, "j": 3, "initial": 1.20, "min": 0.3, "max": 1.4},
            ],
            "omega": omega.tolist(),
            "s11": {"real": np.real(s11).tolist(), "imag": np.imag(s11).tolist()},
            "s21": {"real": np.real(s21).tolist(), "imag": np.imag(s21).tolist()},
            "optimizer": {"iterations": 350, "learning_rate": 0.02},
        }

    def test_parse_filter_spec(self):
        nodes, knobs, omega, s11, s21, opt = parse_filter_spec(self.make_spec())
        self.assertEqual(nodes, 4)
        self.assertEqual([k.name for k in knobs], ["mS1", "m12", "m2L"])
        self.assertEqual(len(omega), 121)
        self.assertEqual(s11.shape, (121,))
        self.assertEqual(s21.shape, (121,))
        self.assertEqual(opt.iterations, 350)

    def test_generic_tuner_recovers_synthetic_matrix(self):
        result = tune_filter_spec(self.make_spec())
        np.testing.assert_allclose(result["final_values"], [1.0, 0.62, 1.0], atol=5e-4, rtol=0.0)
        self.assertLess(result["final_loss"], 1e-8)
        self.assertGreater(result["loss_reduction_factor"], 1e5)
        self.assertEqual(result["parameter_order"], ["mS1", "m12", "m2L"])

    def test_cli_validate_only(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(self.make_spec(), f)
            path = f.name
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = filter_cli_main(["fit", path, "--validate-only"])
        self.assertEqual(rc, 0)
        self.assertIn("valid explicit-port filter spec", buf.getvalue())

    def test_rejects_duplicate_reciprocal_entry(self):
        spec = self.make_spec()
        spec["parameters"].append(
            {"name": "duplicate", "i": 1, "j": 0, "initial": 0.8, "min": 0.3, "max": 1.4}
        )
        with self.assertRaisesRegex(ValueError, "duplicate reciprocal matrix entry"):
            parse_filter_spec(spec)


if __name__ == "__main__":
    unittest.main()
