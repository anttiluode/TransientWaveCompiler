import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.identifiability import (
    _explicit_port_lossy_channels_with_derivatives,
    multistate_candidate_identifiability,
    orthogonal_novelty_fraction,
)
from transientwave.multistate_filter import FilterMeasurementState


class IdentifiabilityTests(unittest.TestCase):
    def test_projection_metric_detects_aliased_and_novel_directions(self):
        j = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
                [0.0, 0.0],
            ]
        )
        aliased = orthogonal_novelty_fraction(j, np.array([2.0, -3.0, 0.0]))
        novel = orthogonal_novelty_fraction(j, np.array([0.0, 0.0, 4.0]))
        mixed = orthogonal_novelty_fraction(j, np.array([1.0, 0.0, 1.0]))

        self.assertAlmostEqual(aliased["novelty_fraction"], 0.0, places=12)
        self.assertAlmostEqual(novel["novelty_fraction"], 1.0, places=12)
        self.assertAlmostEqual(mixed["novelty_fraction"], 1.0 / np.sqrt(2.0), places=12)
        self.assertAlmostEqual(mixed["projected_energy_fraction"], 0.5, places=12)

    def test_s22_parameter_derivative_matches_finite_difference(self):
        parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        values = np.array([1.01, 0.58, 0.97])
        matrix = matrix_from_parameters(4, parameters, values)
        omega = np.linspace(-1.1, 1.1, 17)
        probe = MatrixParameter(1, 3, "m1L")
        response, deriv, _dloss = _explicit_port_lossy_channels_with_derivatives(
            matrix,
            omega,
            [probe],
            0.025,
            ("s11", "s21", "s22"),
        )

        eps = 1e-7
        stamp = probe.stamp(4)
        plus, _, _ = _explicit_port_lossy_channels_with_derivatives(
            matrix + eps * stamp,
            omega,
            [],
            0.025,
            ("s22",),
        )
        minus, _, _ = _explicit_port_lossy_channels_with_derivatives(
            matrix - eps * stamp,
            omega,
            [],
            0.025,
            ("s22",),
        )
        fd = (plus["s22"] - minus["s22"]) / (2.0 * eps)
        np.testing.assert_allclose(deriv["s22"][:, 0], fd, atol=3e-8, rtol=3e-7)
        self.assertEqual(response["s22"].shape, omega.shape)

    def test_multistate_metric_includes_state_nuisance_and_s22_columns(self):
        shared_parameters = [
            MatrixParameter(0, 1, "mS1"),
            MatrixParameter(1, 2, "m12"),
            MatrixParameter(2, 3, "m2L"),
        ]
        shared_values = np.array([1.0, 0.62, 1.0])
        omega = np.linspace(-1.2, 1.2, 41)
        zeros = np.zeros_like(omega, dtype=complex)
        states = [
            FilterMeasurementState(
                name="BASE",
                fixed_parameters=(),
                fixed_values=np.array([], dtype=float),
                measured_s11=zeros,
                measured_s21=zeros,
            ),
            FilterMeasurementState(
                name="R1_UP",
                fixed_parameters=(MatrixParameter(1, 1, "known_d1"),),
                fixed_values=np.array([0.08]),
                measured_s11=zeros,
                measured_s21=zeros,
            ),
        ]
        nuisance = [
            np.array([0.02, 0.05, 0.01, -0.03, -0.02]),
            np.array([0.02, -0.04, 0.02, 0.02, 0.01]),
        ]
        candidate = MatrixParameter(1, 3, "m1L")

        two_channel = multistate_candidate_identifiability(
            shared_values,
            n=4,
            shared_parameters=shared_parameters,
            candidate=candidate,
            omega=omega,
            states=states,
            nuisance_blocks=nuisance,
            channels=("s11", "s21"),
        )
        three_channel = multistate_candidate_identifiability(
            shared_values,
            n=4,
            shared_parameters=shared_parameters,
            candidate=candidate,
            omega=omega,
            states=states,
            nuisance_blocks=nuisance,
            channels=("s11", "s21", "s22"),
        )

        self.assertEqual(two_channel.nuisance_per_state, 5)
        self.assertEqual(two_channel.jacobian_columns, 3 + 2 * 5)
        self.assertEqual(three_channel.nuisance_per_state, 7)
        self.assertEqual(three_channel.jacobian_columns, 3 + 2 * 7)
        self.assertGreaterEqual(two_channel.novelty_fraction, 0.0)
        self.assertLessEqual(two_channel.novelty_fraction, 1.0)
        self.assertGreaterEqual(three_channel.novelty_fraction, 0.0)
        self.assertLessEqual(three_channel.novelty_fraction, 1.0)
        self.assertIsNotNone(two_channel.state_shape_max_line_angle_deg)
        self.assertGreaterEqual(two_channel.state_shape_max_line_angle_deg, 0.0)
        self.assertLessEqual(two_channel.state_shape_max_line_angle_deg, 90.0)


if __name__ == "__main__":
    unittest.main()
