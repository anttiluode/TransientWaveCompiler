import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from transientwave.filter_analysis import (
    compare_fit_result_ensembles,
    summarize_fit_results,
)
from transientwave.filter_cli import main as filter_cli_main


class FilterAnalysisTests(unittest.TestCase):
    def result(self, d1, d2, coupling, phi11, loss=1e-6):
        return {
            "name": "repeat",
            "final_loss": loss,
            "parameters": [
                {"name": "d1", "i": 1, "j": 1, "final": d1, "nominal": 0.0},
                {"name": "d2", "i": 2, "j": 2, "final": d2, "nominal": 0.0},
                {"name": "m12", "i": 1, "j": 2, "final": coupling, "nominal": 0.70},
            ],
            "nuisance": {
                "parameters": [
                    {"name": "resonator_loss", "final": 0.02},
                    {"name": "phi11", "final": phi11},
                ]
            },
        }

    def baseline(self):
        return [
            self.result(-0.001, +0.002, 0.700, 0.10),
            self.result(+0.001, +0.001, 0.701, 0.12),
            self.result(+0.000, +0.003, 0.699, 0.08),
        ]

    def perturbed(self):
        return [
            self.result(-0.081, +0.002, 0.700, 0.18),
            self.result(-0.079, +0.001, 0.701, 0.16),
            self.result(-0.080, +0.003, 0.699, 0.20),
        ]

    def test_summarize_reports_repeatability(self):
        summary = summarize_fit_results(self.baseline())
        rows = {row["name"]: row for row in summary["physical_parameters"]}
        self.assertEqual(summary["runs"], 3)
        self.assertAlmostEqual(rows["d1"]["mean"], 0.0, places=12)
        self.assertAlmostEqual(rows["m12"]["mean"], 0.7, places=12)
        self.assertGreater(rows["d1"]["std"], 0.0)
        nuisance = {row["name"]: row for row in summary["nuisance_parameters"]}
        self.assertAlmostEqual(nuisance["phi11"]["mean"], 0.10, places=12)

    def test_compare_localizes_deliberate_resonator_shift(self):
        result = compare_fit_result_ensembles(self.baseline(), self.perturbed())
        rows = {row["name"]: row for row in result["physical_shifts"]}
        self.assertAlmostEqual(rows["d1"]["mean_shift"], -0.080, places=12)
        self.assertEqual(rows["d1"]["absolute_shift_rank_within_kind"], 1)
        self.assertGreater(rows["d1"]["shift_over_baseline_std"], 50.0)
        self.assertAlmostEqual(rows["d2"]["mean_shift"], 0.0, places=12)
        nuisance = {row["name"]: row for row in result["nuisance_shifts"]}
        self.assertAlmostEqual(nuisance["phi11"]["mean_shift"], 0.08, places=12)

    def test_cli_compare_writes_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline_paths = []
            perturbed_paths = []
            for index, result in enumerate(self.baseline()):
                path = root / f"baseline_{index}.json"
                path.write_text(json.dumps(result), encoding="utf-8")
                baseline_paths.append(str(path))
            for index, result in enumerate(self.perturbed()):
                path = root / f"perturbed_{index}.json"
                path.write_text(json.dumps(result), encoding="utf-8")
                perturbed_paths.append(str(path))
            output = root / "compare.json"
            argv = [
                "compare-results",
                "--baseline",
                *baseline_paths,
                "--perturbed",
                *perturbed_paths,
                "-o",
                str(output),
            ]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = filter_cli_main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())
            saved = json.loads(output.read_text(encoding="utf-8"))
            d1 = next(row for row in saved["physical_shifts"] if row["name"] == "d1")
            self.assertEqual(d1["absolute_shift_rank_within_kind"], 1)
            self.assertIn("physical shifts", buf.getvalue())

    def test_rejects_mismatched_parameter_schema(self):
        bad = self.perturbed()
        bad[0] = dict(bad[0])
        bad[0]["parameters"] = [dict(item) for item in bad[0]["parameters"]]
        bad[0]["parameters"][0]["name"] = "different"
        with self.assertRaisesRegex(ValueError, "parameter order/schema"):
            compare_fit_result_ensembles(self.baseline(), bad)


if __name__ == "__main__":
    unittest.main()
