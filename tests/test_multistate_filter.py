import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.measurement_aware_filter import measurement_aware_response
from transientwave.multistate_filter import (
    FilterMeasurementState,
    multistate_loss_and_gradient,
    score_missing_reciprocal_edges_multistate,
)


class MultistateFilterTests(unittest.TestCase):
    def setUp(self):
        self.shared_parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        self.shared_values = np.array([1.0, 0.62, 1.0], dtype=float)
        self.omega = np.linspace(-4.0, 4.0, 161)
        self.nuisance = np.array([0.02, 0.08, 0.015, -0.06, -0.02], dtype=float)

    def make_state(self, name, fixed_parameters=(), fixed_values=(), hidden=None):
        parameters = list(self.shared_parameters)
        values = list(self.shared_values)
        if hidden is not None:
            parameter, value = hidden
            parameters.append(parameter)
            values.append(value)
        parameters.extend(fixed_parameters)
        values.extend(fixed_values)
        s11, s21 = measurement_aware_response(
            values,
            n=4,
            parameters=parameters,
            omega=self.omega,
            resonator_loss=float(self.nuisance[0]),
            phi11=float(self.nuisance[1]),
            tau11=float(self.nuisance[2]),
            phi21=float(self.nuisance[3]),
            tau21=float(self.nuisance[4]),
        )
        return FilterMeasurementState(
            name=name,
            fixed_parameters=tuple(fixed_parameters),
            fixed_values=np.asarray(fixed_values, dtype=float),
            measured_s11=s11,
            measured_s21=s21,
        )

    def test_multistate_exact_gradient_matches_finite_difference(self):
        states = [
            self.make_state("base"),
            self.make_state(
                "detuned",
                fixed_parameters=(MatrixParameter(1, 1, "known_d1"),),
                fixed_values=(0.07,),
            ),
        ]
        x = np.concatenate([self.shared_values + np.array([0.03, -0.02, 0.01]), self.nuisance, self.nuisance])
        loss, grad = multistate_loss_and_gradient(
            x,
            n=4,
            shared_parameters=self.shared_parameters,
            omega=self.omega,
            states=states,
        )
        self.assertGreater(loss, 0.0)
        h = 1e-6
        fd = np.zeros_like(x)
        for i in range(len(x)):
            xp = x.copy(); xp[i] += h
            xm = x.copy(); xm[i] -= h
            lp, _ = multistate_loss_and_gradient(
                xp, n=4, shared_parameters=self.shared_parameters, omega=self.omega, states=states
            )
            lm, _ = multistate_loss_and_gradient(
                xm, n=4, shared_parameters=self.shared_parameters, omega=self.omega, states=states
            )
            fd[i] = (lp - lm) / (2.0 * h)
        np.testing.assert_allclose(grad, fd, atol=2e-6, rtol=2e-4)

    def test_shared_hidden_edge_ranks_first_across_known_states(self):
        hidden = (MatrixParameter(0, 2, "hidden_02"), 0.07)
        states = [
            self.make_state("base", hidden=hidden),
            self.make_state(
                "d1up",
                fixed_parameters=(MatrixParameter(1, 1, "known_d1"),),
                fixed_values=(0.08,),
                hidden=hidden,
            ),
            self.make_state(
                "d2down",
                fixed_parameters=(MatrixParameter(2, 2, "known_d2"),),
                fixed_values=(-0.06,),
                hidden=hidden,
            ),
        ]
        scores = score_missing_reciprocal_edges_multistate(
            self.shared_values,
            n=4,
            shared_parameters=self.shared_parameters,
            omega=self.omega,
            states=states,
            nuisance_blocks=[self.nuisance, self.nuisance, self.nuisance],
            max_abs_probe=0.15,
        )
        self.assertEqual((scores[0].i, scores[0].j), (0, 2))
        self.assertAlmostEqual(scores[0].proposed_value, 0.07, delta=0.02)
        self.assertGreater(scores[0].relative_loss_reduction, 0.8)


if __name__ == "__main__":
    unittest.main()
