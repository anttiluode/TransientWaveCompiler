import unittest

import numpy as np

from transientwave.filter_units import (
    frequency_from_normalized_omega,
    resonator_frequency_diagnosis,
    resonator_frequency_from_diagonal,
)
from transientwave.touchstone import normalized_omega_bandpass, normalized_omega_linear


class FilterUnitsTests(unittest.TestCase):
    def test_linear_inverse_matches_forward_mapping(self):
        mapping = {"mode": "linear", "center_hz": 150e6, "scale_hz": 50e6}
        for frequency in [100e6, 150e6, 200e6]:
            omega = normalized_omega_linear(
                np.asarray([frequency]), center_hz=150e6, scale_hz=50e6
            )[0]
            self.assertAlmostEqual(frequency_from_normalized_omega(omega, mapping), frequency)

    def test_bandpass_inverse_matches_forward_mapping(self):
        mapping = {
            "mode": "bandpass",
            "center_hz": 1e9,
            "bandwidth_hz": 100e6,
            "omega_sign": 1.0,
        }
        for frequency in [0.95e9, 1.0e9, 1.05e9]:
            omega = normalized_omega_bandpass(
                np.asarray([frequency]), center_hz=1e9, bandwidth_hz=100e6
            )[0]
            self.assertAlmostEqual(
                frequency_from_normalized_omega(omega, mapping),
                frequency,
                delta=1e-6,
            )

    def test_diagonal_sign_is_resonance_omega_equals_minus_d(self):
        mapping = {"mode": "linear", "center_hz": 1e9, "scale_hz": 50e6}
        # Positive d moves the uncoupled resonance to negative Omega, hence
        # lower physical frequency for a positive linear scale.
        self.assertAlmostEqual(resonator_frequency_from_diagonal(+0.10, mapping), 995e6)
        self.assertAlmostEqual(resonator_frequency_from_diagonal(-0.10, mapping), 1005e6)

    def test_bandpass_resonator_diagnosis_reports_exact_hz_shift(self):
        mapping = {
            "mode": "bandpass",
            "center_hz": 2.45e9,
            "bandwidth_hz": 100e6,
            "omega_sign": 1.0,
        }
        diagnosis = resonator_frequency_diagnosis(0.0, +0.04, mapping)
        self.assertAlmostEqual(diagnosis["nominal_resonance_hz"], 2.45e9, delta=1e-6)
        self.assertLess(diagnosis["fitted_resonance_hz"], 2.45e9)
        self.assertLess(diagnosis["resonance_deviation_hz"], 0.0)
        # First-order expectation is about -d*BW/2 = -2 MHz; the exact
        # inversion should remain very close at this small detuning.
        self.assertAlmostEqual(diagnosis["resonance_deviation_hz"], -2e6, delta=5000.0)


if __name__ == "__main__":
    unittest.main()
