import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.measurement_aware_filter import (
    measurement_aware_loss_and_gradient,
    measurement_aware_response,
    wrap_phase_error,
)


class MeasurementAwareFilterTests(unittest.TestCase):
    def setUp(self):
        self.parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        self.omega = np.unique(
            np.concatenate([np.linspace(-8.0, 8.0, 91), np.linspace(-2.0, 2.0, 91)])
        )
        self.target_matrix = np.array([1.0, 0.62, 1.0], dtype=float)
        self.target_nuisance = [0.025, 0.12, 0.018, -0.08, -0.027]
        self.s11, self.s21 = measurement_aware_response(
            self.target_matrix,
            n=4,
            parameters=self.parameters,
            omega=self.omega,
            resonator_loss=self.target_nuisance[0],
            phi11=self.target_nuisance[1],
            tau11=self.target_nuisance[2],
            phi21=self.target_nuisance[3],
            tau21=self.target_nuisance[4],
        )

    def test_full_aware_gradient_matches_central_difference(self):
        x = np.array([0.82, 0.79, 1.13, 0.011, -0.04, 0.007, 0.05, -0.012], dtype=float)
        loss, grad = measurement_aware_loss_and_gradient(
            x,
            n=4,
            parameters=self.parameters,
            omega=self.omega,
            measured_s11=self.s11,
            measured_s21=self.s21,
        )
        self.assertGreater(loss, 1e-6)
        h = 1e-6
        fd = np.empty_like(x)
        for i in range(len(x)):
            xp = x.copy(); xp[i] += h
            xm = x.copy(); xm[i] -= h
            lp, _ = measurement_aware_loss_and_gradient(
                xp, n=4, parameters=self.parameters, omega=self.omega,
                measured_s11=self.s11, measured_s21=self.s21,
            )
            lm, _ = measurement_aware_loss_and_gradient(
                xm, n=4, parameters=self.parameters, omega=self.omega,
                measured_s11=self.s11, measured_s21=self.s21,
            )
            fd[i] = (lp - lm) / (2.0 * h)
        np.testing.assert_allclose(grad, fd, rtol=8e-5, atol=8e-7)

    def test_zero_loss_at_exact_hidden_parameters(self):
        x = np.array([*self.target_matrix, *self.target_nuisance], dtype=float)
        loss, grad = measurement_aware_loss_and_gradient(
            x,
            n=4,
            parameters=self.parameters,
            omega=self.omega,
            measured_s11=self.s11,
            measured_s21=self.s21,
        )
        self.assertLess(loss, 1e-28)
        self.assertLess(float(np.max(np.abs(grad))), 1e-11)

    def test_phase_error_wrap(self):
        self.assertAlmostEqual(wrap_phase_error(np.pi + 0.1, -np.pi + 0.1), 0.0, places=12)
        self.assertAlmostEqual(wrap_phase_error(-np.pi + 0.2, np.pi - 0.2), 0.4, places=12)


if __name__ == "__main__":
    unittest.main()
