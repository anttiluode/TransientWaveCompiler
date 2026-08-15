import unittest

import numpy as np

from transientwave.measurement_capability import (
    conditional_candidate_information,
    nested_conditional_information_curve,
)


class ConditionalCandidateInformationTests(unittest.TestCase):
    def test_exact_alias_has_zero_information(self):
        j = np.array([[1.0], [0.0]])
        g = np.array([2.0, 0.0])
        result = conditional_candidate_information(j, g)
        self.assertAlmostEqual(result.conditional_information, 0.0, places=14)
        self.assertAlmostEqual(result.information_fraction, 0.0, places=14)
        self.assertAlmostEqual(result.novelty_fraction, 0.0, places=14)

    def test_orthogonal_candidate_keeps_all_information(self):
        j = np.array([[1.0], [0.0]])
        g = np.array([0.0, 3.0])
        result = conditional_candidate_information(j, g)
        self.assertAlmostEqual(result.conditional_information, 9.0, places=14)
        self.assertAlmostEqual(result.raw_candidate_energy, 9.0, places=14)
        self.assertAlmostEqual(result.information_fraction, 1.0, places=14)
        self.assertAlmostEqual(result.novelty_fraction, 1.0, places=14)

    def test_information_fraction_equals_novelty_squared(self):
        j = np.array([[1.0], [1.0], [0.0]])
        g = np.array([2.0, 0.0, 1.0])
        result = conditional_candidate_information(j, g)
        self.assertAlmostEqual(
            result.information_fraction,
            result.novelty_fraction**2,
            places=13,
        )

    def test_no_fitted_columns_leaves_candidate_untouched(self):
        j = np.empty((3, 0))
        g = np.array([1.0, -2.0, 2.0])
        result = conditional_candidate_information(j, g)
        self.assertAlmostEqual(result.conditional_information, 9.0, places=14)
        self.assertAlmostEqual(result.information_fraction, 1.0, places=14)
        self.assertEqual(result.jacobian_columns, 0)

    def test_nested_information_is_nondecreasing(self):
        # The first block can be explained exactly. Later blocks constrain the
        # same compensating coefficient and force a residual to appear.
        j_blocks = [
            np.array([[1.0]]),
            np.array([[1.0]]),
            np.array([[2.0]]),
        ]
        g_blocks = [
            np.array([1.0]),
            np.array([0.0]),
            np.array([3.0]),
        ]
        curve = nested_conditional_information_curve(j_blocks, g_blocks)
        values = np.array([x.conditional_information for x in curve])
        self.assertTrue(np.all(np.diff(values) >= -1e-13))
        self.assertAlmostEqual(values[0], 0.0, places=14)
        self.assertGreater(values[-1], values[1])

    def test_nested_blocks_must_share_parameter_columns(self):
        with self.assertRaises(ValueError):
            nested_conditional_information_curve(
                [np.ones((1, 1)), np.ones((1, 2))],
                [np.ones(1), np.ones(1)],
            )


if __name__ == "__main__":
    unittest.main()
