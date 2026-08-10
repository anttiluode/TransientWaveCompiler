import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from transientwave.filter_cli import main as filter_cli_main
from transientwave.touchstone import (
    inject_touchstone_measurement,
    normalized_omega_bandpass,
    normalized_omega_linear,
    parse_touchstone_2port_text,
)


class TouchstoneTests(unittest.TestCase):
    def test_version1_ri_uses_standard_21_12_order(self):
        text = """! two-port RI example
# MHz S RI R 50
100 1 0  0.1 -0.2  0.3 0.4  0 0
200 0.5 0.1  0.2 -0.3  0.4 0.5  0.1 0.2
"""
        data = parse_touchstone_2port_text(text)
        np.testing.assert_allclose(data.frequency_hz, [100e6, 200e6])
        np.testing.assert_allclose(data.s11, [1 + 0j, 0.5 + 0.1j])
        np.testing.assert_allclose(data.s21, [0.1 - 0.2j, 0.2 - 0.3j])
        np.testing.assert_allclose(data.s12, [0.3 + 0.4j, 0.4 + 0.5j])
        self.assertEqual(data.data_order, "21_12")
        self.assertEqual(data.data_format, "RI")
        self.assertEqual(data.reference_ohm, 50.0)

    def test_version2_ma_respects_12_21_order(self):
        text = """[Version] 2.0
# GHz S MA R 50
[Number of Ports] 2
[Two-Port Data Order] 12_21
[Number of Frequencies] 1
[Network Data]
1 1 0  0.5 90  0.25 -90  0 0
[End]
"""
        data = parse_touchstone_2port_text(text)
        np.testing.assert_allclose(data.s11, [1 + 0j], atol=1e-14)
        np.testing.assert_allclose(data.s12, [0 + 0.5j], atol=1e-14)
        np.testing.assert_allclose(data.s21, [0 - 0.25j], atol=1e-14)
        self.assertEqual(data.data_order, "12_21")
        self.assertEqual(data.version, "2.0")

    def test_db_format_converts_to_linear_complex(self):
        text = """# GHz S DB R 50
1 -6.020599913 0  -20 90  -20 90  -6.020599913 180
2 -6.020599913 0  -20 90  -20 90  -6.020599913 180
"""
        data = parse_touchstone_2port_text(text)
        np.testing.assert_allclose(np.abs(data.s11), [0.5, 0.5], atol=1e-10)
        np.testing.assert_allclose(data.s21, [0 + 0.1j, 0 + 0.1j], atol=1e-12)

    def test_linear_omega_mapping_is_explicit(self):
        omega = normalized_omega_linear(
            np.array([100e6, 150e6, 200e6]), center_hz=150e6, scale_hz=50e6
        )
        np.testing.assert_allclose(omega, [-1.0, 0.0, 1.0])

    def test_classical_bandpass_omega_mapping(self):
        omega = normalized_omega_bandpass(
            np.array([0.95e9, 1.0e9, 1.05e9]),
            center_hz=1.0e9,
            bandwidth_hz=100e6,
        )
        np.testing.assert_allclose(
            omega,
            [10.0 * (0.95 - 1.0 / 0.95), 0.0, 10.0 * (1.05 - 1.0 / 1.05)],
        )
        flipped = normalized_omega_bandpass(
            np.array([0.95e9, 1.0e9, 1.05e9]),
            center_hz=1.0e9,
            bandwidth_hz=100e6,
            omega_sign=-1.0,
        )
        np.testing.assert_allclose(flipped, -omega)

    def test_prepare_s2p_cli_injects_linear_measurement_into_topology(self):
        topology = {
            "name": "touchstone-test",
            "model": "explicit-port",
            "nodes": 4,
            "parameters": [
                {"name": "mS1", "i": 0, "j": 1, "initial": 0.8, "min": 0.3, "max": 1.4},
                {"name": "m12", "i": 1, "j": 2, "initial": 0.7, "min": 0.2, "max": 1.2},
                {"name": "m2L", "i": 2, "j": 3, "initial": 0.8, "min": 0.3, "max": 1.4},
            ],
        }
        trace = """# MHz S RI R 50
100 1 0  0.1 0  0.1 0  0 0
150 0.8 0  0.2 0  0.2 0  0.1 0
200 0.5 0  0.3 0  0.3 0  0.2 0
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            topology_path = root / "topology.json"
            trace_path = root / "trace.s2p"
            output_path = root / "prepared.json"
            topology_path.write_text(json.dumps(topology), encoding="utf-8")
            trace_path.write_text(trace, encoding="ascii")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = filter_cli_main(
                    [
                        "prepare-s2p",
                        str(topology_path),
                        str(trace_path),
                        "--center-hz",
                        "150000000",
                        "--scale-hz",
                        "50000000",
                        "-o",
                        str(output_path),
                    ]
                )
            self.assertEqual(rc, 0)
            prepared = json.loads(output_path.read_text(encoding="utf-8"))
            np.testing.assert_allclose(prepared["omega"], [-1.0, 0.0, 1.0])
            np.testing.assert_allclose(prepared["frequency_hz"], [100e6, 150e6, 200e6])
            self.assertEqual(prepared["measurement_source"]["format"], "touchstone")
            self.assertEqual(prepared["measurement_source"]["reference_ohm"], 50.0)
            self.assertEqual(prepared["measurement_source"]["omega_mapping"]["mode"], "linear")
            self.assertIn("mapping=linear", buf.getvalue())

    def test_prepare_s2p_cli_classical_bandpass_mapping(self):
        topology = {
            "name": "touchstone-bandpass-test",
            "model": "explicit-port",
            "nodes": 4,
            "parameters": [
                {"name": "mS1", "i": 0, "j": 1, "initial": 0.8, "min": 0.3, "max": 1.4},
                {"name": "m12", "i": 1, "j": 2, "initial": 0.7, "min": 0.2, "max": 1.2},
                {"name": "m2L", "i": 2, "j": 3, "initial": 0.8, "min": 0.3, "max": 1.4},
            ],
        }
        trace = """# MHz S RI R 50
950 1 0  0.1 0  0.1 0  0 0
1000 0.8 0  0.2 0  0.2 0  0.1 0
1050 0.5 0  0.3 0  0.3 0  0.2 0
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            topology_path = root / "topology.json"
            trace_path = root / "trace.s2p"
            output_path = root / "prepared.json"
            topology_path.write_text(json.dumps(topology), encoding="utf-8")
            trace_path.write_text(trace, encoding="ascii")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = filter_cli_main(
                    [
                        "prepare-s2p",
                        str(topology_path),
                        str(trace_path),
                        "--center-hz",
                        "1000000000",
                        "--bandwidth-hz",
                        "100000000",
                        "-o",
                        str(output_path),
                    ]
                )
            self.assertEqual(rc, 0)
            prepared = json.loads(output_path.read_text(encoding="utf-8"))
            expected = normalized_omega_bandpass(
                np.array([950e6, 1000e6, 1050e6]),
                center_hz=1e9,
                bandwidth_hz=100e6,
            )
            np.testing.assert_allclose(prepared["omega"], expected)
            mapping = prepared["measurement_source"]["omega_mapping"]
            self.assertEqual(mapping["mode"], "bandpass")
            self.assertEqual(mapping["bandwidth_hz"], 100e6)
            self.assertIn("mapping=bandpass", buf.getvalue())

    def test_version2_requires_explicit_two_port_order(self):
        text = """[Version] 2.0
# GHz S RI R 50
[Number of Ports] 2
[Number of Frequencies] 1
[Network Data]
1 1 0  0 0  0 0  1 0
[End]
"""
        with self.assertRaisesRegex(ValueError, "missing \\[Two-Port Data Order\\]"):
            parse_touchstone_2port_text(text)


if __name__ == "__main__":
    unittest.main()
