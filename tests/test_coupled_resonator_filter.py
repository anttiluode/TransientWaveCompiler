import unittest

import numpy as np

from transientwave.coupled_resonator_filter import (
    CouplingEdge,
    MatrixParameter,
    magnitude_response_loss_and_gradient,
    magnitude_response_loss_and_parameter_gradient,
    matrix_from_edges,
    matrix_from_parameters,
    scattering,
)


class CoupledResonatorFilterTests(unittest.TestCase):
    def setUp(self):
        self.edges = [CouplingEdge(0, 1), CouplingEdge(1, 2), CouplingEdge(0, 2)]
        self.target_values = np.array([0.6, 0.6, 0.2], dtype=float)
        self.target = matrix_from_edges(3, self.edges, self.target_values)
        self.gamma = np.linspace(-2.5, 2.5, 161)
        self.t11, self.t21 = scattering(self.target, self.gamma, r_in=1.0, r_out=1.0)

    def test_published_three_resonator_matrix_is_symmetric(self):
        np.testing.assert_array_equal(self.target, self.target.T)
        np.testing.assert_allclose(
            self.target,
            np.array([[0.0, 0.6, 0.2], [0.6, 0.0, 0.6], [0.2, 0.6, 0.0]]),
            rtol=0.0,
            atol=0.0,
        )

    def test_loss_is_zero_at_target(self):
        loss, grad = magnitude_response_loss_and_gradient(
            self.target_values,
            n=3,
            edges=self.edges,
            gamma=self.gamma,
            target_s11=self.t11,
            target_s21=self.t21,
        )
        self.assertLess(loss, 1e-28)
        self.assertLess(float(np.max(np.abs(grad))), 1e-12)

    def test_analytic_gradient_matches_central_difference(self):
        x = np.array([0.42, 0.77, -0.08], dtype=float)
        loss, grad = magnitude_response_loss_and_gradient(
            x,
            n=3,
            edges=self.edges,
            gamma=self.gamma,
            target_s11=self.t11,
            target_s21=self.t21,
        )
        self.assertGreater(loss, 1e-6)
        h = 1e-6
        fd = np.empty_like(x)
        for i in range(len(x)):
            xp = x.copy(); xp[i] += h
            xm = x.copy(); xm[i] -= h
            lp, _ = magnitude_response_loss_and_gradient(
                xp, n=3, edges=self.edges, gamma=self.gamma,
                target_s11=self.t11, target_s21=self.t21,
            )
            lm, _ = magnitude_response_loss_and_gradient(
                xm, n=3, edges=self.edges, gamma=self.gamma,
                target_s11=self.t11, target_s21=self.t21,
            )
            fd[i] = (lp - lm) / (2.0 * h)
        np.testing.assert_allclose(grad, fd, rtol=2e-5, atol=2e-7)

    def test_diagonal_and_edge_gradient_matches_central_difference(self):
        parameters = [
            MatrixParameter(0, 0, "d1"),
            MatrixParameter(1, 1, "d2"),
            MatrixParameter(2, 2, "d3"),
            MatrixParameter(0, 1, "m12"),
            MatrixParameter(1, 2, "m23"),
            MatrixParameter(0, 2, "m13"),
        ]
        target_values = np.array([0.0, 0.0, 0.0, 0.6, 0.6, 0.2])
        target = matrix_from_parameters(3, parameters, target_values)
        t11, t21 = scattering(target, self.gamma)
        x = np.array([0.21, -0.17, 0.08, 0.43, 0.76, -0.09])
        loss, grad = magnitude_response_loss_and_parameter_gradient(
            x,
            n=3,
            parameters=parameters,
            gamma=self.gamma,
            target_s11=t11,
            target_s21=t21,
        )
        self.assertGreater(loss, 1e-6)
        h = 1e-6
        fd = np.empty_like(x)
        for i in range(len(x)):
            xp = x.copy(); xp[i] += h
            xm = x.copy(); xm[i] -= h
            lp, _ = magnitude_response_loss_and_parameter_gradient(
                xp, n=3, parameters=parameters, gamma=self.gamma,
                target_s11=t11, target_s21=t21,
            )
            lm, _ = magnitude_response_loss_and_parameter_gradient(
                xm, n=3, parameters=parameters, gamma=self.gamma,
                target_s11=t11, target_s21=t21,
            )
            fd[i] = (lp - lm) / (2.0 * h)
        np.testing.assert_allclose(grad, fd, rtol=3e-5, atol=3e-7)


if __name__ == "__main__":
    unittest.main()
