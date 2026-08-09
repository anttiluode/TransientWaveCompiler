import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.generalized_coupling_matrix import (
    complex_response_loss_and_gradient,
    generalized_scattering,
)


class GeneralizedCouplingMatrixTests(unittest.TestCase):
    def setUp(self):
        self.parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m23"),
            MatrixParameter(3, 4, "m34"),
            MatrixParameter(4, 5, "m4L"),
            MatrixParameter(1, 4, "m14"),
            MatrixParameter(0, 5, "mSL"),
        ]
        self.target_values = np.array([1.02, -0.86, 0.77, -0.86, 1.02, -0.19, 0.0005])
        self.target = matrix_from_parameters(6, self.parameters, self.target_values)
        self.omega = np.unique(
            np.concatenate([np.linspace(-30.0, 30.0, 241), np.linspace(-3.0, 3.0, 241)])
        )
        self.t11, self.t21 = generalized_scattering(self.target, self.omega)

    def test_published_matrix_entries(self):
        expected = np.array(
            [
                [0, 1.02, 0, 0, 0, 0.0005],
                [1.02, 0, -0.86, 0, -0.19, 0],
                [0, -0.86, 0, 0.77, 0, 0],
                [0, 0, 0.77, 0, -0.86, 0],
                [0, -0.19, 0, -0.86, 0, 1.02],
                [0.0005, 0, 0, 0, 1.02, 0],
            ],
            dtype=float,
        )
        np.testing.assert_allclose(self.target, expected, rtol=0.0, atol=0.0)

    def test_lossless_response_conserves_power(self):
        s11, s21 = generalized_scattering(self.target, self.omega)
        np.testing.assert_allclose(np.abs(s11) ** 2 + np.abs(s21) ** 2, 1.0, rtol=2e-10, atol=2e-10)

    def test_complex_gradient_matches_central_difference(self):
        x = np.array([0.91, -0.72, 0.91, -1.03, 1.13, -0.07, 0.012])
        loss, grad = complex_response_loss_and_gradient(
            x,
            n=6,
            parameters=self.parameters,
            omega=self.omega,
            target_s11=self.t11,
            target_s21=self.t21,
        )
        self.assertGreater(loss, 1e-6)
        h = 1e-6
        fd = np.empty_like(x)
        for i in range(len(x)):
            xp = x.copy(); xp[i] += h
            xm = x.copy(); xm[i] -= h
            lp, _ = complex_response_loss_and_gradient(
                xp, n=6, parameters=self.parameters, omega=self.omega,
                target_s11=self.t11, target_s21=self.t21,
            )
            lm, _ = complex_response_loss_and_gradient(
                xm, n=6, parameters=self.parameters, omega=self.omega,
                target_s11=self.t11, target_s21=self.t21,
            )
            fd[i] = (lp - lm) / (2.0 * h)
        np.testing.assert_allclose(grad, fd, rtol=5e-5, atol=5e-7)


if __name__ == "__main__":
    unittest.main()
