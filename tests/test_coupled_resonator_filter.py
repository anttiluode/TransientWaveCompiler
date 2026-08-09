import unittest

import numpy as np

from transientwave.coupled_resonator_filter import (
    CouplingEdge,
    magnitude_response_loss_and_gradient,
    matrix_from_edges,
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


if __name__ == "__main__":
    unittest.main()
