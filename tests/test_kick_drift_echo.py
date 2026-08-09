import unittest

import numpy as np

from transientwave.kick_drift import (
    common_diff_terminal_boundary_in_kick_coordinates,
    kick_drift_step,
    kick_operator,
    kick_state_to_position_history,
    pointer_swap_mirror_in_kick_coordinates,
    position_history_to_kick_state,
    second_order_step,
)


class KickDriftEchoTests(unittest.TestCase):
    def test_pointer_swap_mirror_matches_position_history(self):
        rng = np.random.default_rng(10)
        current = rng.normal(size=12)
        previous = rng.normal(size=12)
        z, p = position_history_to_kick_state(current, previous)
        zm, pm = pointer_swap_mirror_in_kick_coordinates(z, p)
        cur2, prev2 = kick_state_to_position_history(zm, pm)
        np.testing.assert_allclose(cur2, previous, rtol=0.0, atol=2e-15)
        np.testing.assert_allclose(prev2, current, rtol=0.0, atol=2e-15)

    def test_common_diff_terminal_boundary_matches_v08(self):
        rng = np.random.default_rng(11)
        current = rng.normal(size=9)
        previous = rng.normal(size=9)
        err = rng.normal(size=9) * 0.01
        z, p = position_history_to_kick_state(current, previous)
        cz, cp, dz, dp = common_diff_terminal_boundary_in_kick_coordinates(z, p, err)
        ccur, cprev = kick_state_to_position_history(cz, cp)
        dcur, dprev = kick_state_to_position_history(dz, dp)
        np.testing.assert_allclose(ccur, previous, rtol=0.0, atol=2e-15)
        np.testing.assert_allclose(cprev, current, rtol=0.0, atol=2e-15)
        np.testing.assert_array_equal(dcur, err)
        np.testing.assert_allclose(dprev, np.zeros_like(err), rtol=0.0, atol=2e-15)

    def test_many_reverse_ticks_match_v08_state_coordinates(self):
        rng = np.random.default_rng(12)
        n = 10
        a = rng.normal(size=(n, n))
        Q = np.eye(n) * 1.8 + (a + a.T) * 0.015
        K = kick_operator(Q)

        # Arbitrary forward terminal current/previous and one terminal D error.
        ccur = rng.normal(size=n) * 0.1
        cprev = rng.normal(size=n) * 0.1
        terminal_error = rng.normal(size=n) * 0.01

        z, p = position_history_to_kick_state(ccur, cprev)
        cz, cp, dz, dp = common_diff_terminal_boundary_in_kick_coordinates(
            z, p, terminal_error
        )

        # Position-history image of exactly the same v0.8 boundary.
        ccur_ref, cprev_ref = cprev.copy(), ccur.copy()
        dcur_ref, dprev_ref = terminal_error.copy(), np.zeros(n)

        for _ in range(80):
            csrc = rng.normal(size=n) * 0.002
            dsrc = rng.normal(size=n) * 0.002

            cnext, cprev_next = second_order_step(ccur_ref, cprev_ref, Q, csrc)
            dnext, dprev_next = second_order_step(dcur_ref, dprev_ref, Q, dsrc)
            cz, cp = kick_drift_step(cz, cp, K, csrc)
            dz, dp = kick_drift_step(dz, dp, K, dsrc)

            np.testing.assert_allclose(cz, cnext, rtol=1e-11, atol=1e-11)
            np.testing.assert_allclose(dz, dnext, rtol=1e-11, atol=1e-11)

            # Local edge differences / credit sensor sees the current z field,
            # so exact current-state equality is sufficient to preserve the
            # v0.8 square-difference identity.
            ccur_ref, cprev_ref = cnext, cprev_next
            dcur_ref, dprev_ref = dnext, dprev_next

    def test_same_two_vectors_per_lane(self):
        # This is deliberately a semantic resource assertion: (z,p) replaces
        # (CUR,PREV); it does not add a third state vector.
        rng = np.random.default_rng(13)
        current = rng.normal(size=5)
        previous = rng.normal(size=5)
        z, p = position_history_to_kick_state(current, previous)
        self.assertEqual(z.shape, current.shape)
        self.assertEqual(p.shape, previous.shape)


if __name__ == "__main__":
    unittest.main()
