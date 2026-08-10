import unittest

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.topology_gauge import (
    analyze_absent_edges_gauge,
    analyze_candidate_gauge,
    single_detuning_anchors_that_break_alias,
)


PARAMETERS = [
    MatrixParameter(0, 1, "mS1"),
    MatrixParameter(1, 2, "m12"),
    MatrixParameter(2, 3, "m23"),
    MatrixParameter(3, 4, "m34"),
    MatrixParameter(4, 5, "m4L"),
    MatrixParameter(1, 4, "m14"),
    MatrixParameter(0, 5, "mSL"),
]
VALUES = np.array([1.02, -0.86, 0.77, -0.86, 1.02, -0.19, 0.0005], dtype=float)
MATRIX = matrix_from_parameters(6, PARAMETERS, VALUES)


class TopologyGaugeTests(unittest.TestCase):
    def test_published_folded_topology_has_exactly_two_static_gauge_aliases(self):
        rows = analyze_absent_edges_gauge(MATRIX, PARAMETERS)
        aliased = {row.candidate for row in rows if row.aliased}
        self.assertEqual(aliased, {(0, 3), (2, 5)})
        self.assertTrue(all(row.baseline_gauge_dimension == 0 for row in rows))

    def test_releasing_each_alias_opens_one_rotation_generator(self):
        source_side = analyze_candidate_gauge(MATRIX, PARAMETERS, (0, 3))
        load_side = analyze_candidate_gauge(MATRIX, PARAMETERS, (2, 5))
        self.assertEqual(source_side.released_gauge_dimension, 1)
        self.assertEqual(load_side.released_gauge_dimension, 1)
        self.assertEqual(source_side.nullity_gain, 1)
        self.assertEqual(load_side.nullity_gain, 1)

        source_coeffs = dict(zip(source_side.generator_labels, source_side.unit_candidate_generator_coefficients))
        load_coeffs = dict(zip(load_side.generator_labels, load_side.unit_candidate_generator_coefficients))
        self.assertAlmostEqual(abs(source_coeffs[(1, 3)]), 1.0 / 1.02, places=12)
        self.assertAlmostEqual(abs(load_coeffs[(2, 4)]), 1.0 / 1.02, places=12)
        for label, value in source_coeffs.items():
            if label != (1, 3):
                self.assertAlmostEqual(value, 0.0, places=12)
        for label, value in load_coeffs.items():
            if label != (2, 4):
                self.assertAlmostEqual(value, 0.0, places=12)

    def test_single_resonator_detuning_anchor_table_matches_rotation_support(self):
        self.assertEqual(
            single_detuning_anchors_that_break_alias(MATRIX, PARAMETERS, (0, 3)),
            [1, 3],
        )
        self.assertEqual(
            single_detuning_anchors_that_break_alias(MATRIX, PARAMETERS, (2, 5)),
            [2, 4],
        )

    def test_commuting_detunings_do_not_break_alias(self):
        self.assertTrue(analyze_candidate_gauge(MATRIX, PARAMETERS, (0, 3), anchors=(2,)).aliased)
        self.assertTrue(analyze_candidate_gauge(MATRIX, PARAMETERS, (0, 3), anchors=(4,)).aliased)
        self.assertTrue(analyze_candidate_gauge(MATRIX, PARAMETERS, (2, 5), anchors=(1,)).aliased)
        self.assertTrue(analyze_candidate_gauge(MATRIX, PARAMETERS, (2, 5), anchors=(3,)).aliased)


if __name__ == "__main__":
    unittest.main()
