import unittest

import numpy as np

from transientwave.kick_drift import (
    inverse_kick_drift_step,
    kick_drift_step,
    kick_operator,
    kick_state_to_position_history,
    position_history_to_kick_state,
    second_order_step,
)


class KickDriftTests(unittest.TestCase):
    def test_state_coordinate_round_trip(self):
        rng = np.random.default_rng(1)
        z = rng.normal(size=8)
        zp = rng.normal(size=8)
        x, p = position_history_to_kick_state(z, zp)
        z2, zp2 = kick_state_to_position_history(x, p)
        np.testing.assert_array_equal(z2, z)
        np.testing.assert_allclose(zp2, zp, rtol=0.0, atol=2e-15)

    def test_one_step_matches_second_order(self):
        rng = np.random.default_rng(2)
        a = rng.normal(size=(8, 8))
        Q = (a + a.T) * 0.1
        z = rng.normal(size=8)
        zp = rng.normal(size=8)
        u = rng.normal(size=8) * 0.01
        K = kick_operator(Q)
        x, p = position_history_to_kick_state(z, zp)
        z_ref, _ = second_order_step(z, zp, Q, u)
        z_kd, p_kd = kick_drift_step(x, p, K, u)
        np.testing.assert_allclose(z_kd, z_ref, rtol=0.0, atol=2e-15)
        np.testing.assert_allclose(p_kd, z_ref - z, rtol=0.0, atol=2e-15)

    def test_many_ticks_match(self):
        rng = np.random.default_rng(3)
        a = rng.normal(size=(6, 6))
        Q = (a + a.T) * 0.08
        K = kick_operator(Q)
        z = rng.normal(size=6)
        zp = rng.normal(size=6)
        x, p = position_history_to_kick_state(z, zp)
        for _ in range(100):
            u = rng.normal(size=6) * 0.003
            z, zp = second_order_step(z, zp, Q, u)
            x, p = kick_drift_step(x, p, K, u)
            np.testing.assert_allclose(x, z, rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(p, z - zp, rtol=1e-12, atol=1e-12)

    def test_inverse_exactly_retraces_forward_map(self):
        rng = np.random.default_rng(4)
        a = rng.normal(size=(7, 7))
        Q = (a + a.T) * 0.06
        K = kick_operator(Q)
        z0 = rng.normal(size=7)
        p0 = rng.normal(size=7)
        u = rng.normal(size=7) * 0.02
        z1, p1 = kick_drift_step(z0, p0, K, u)
        zr, pr = inverse_kick_drift_step(z1, p1, K, u)
        np.testing.assert_allclose(zr, z0, rtol=0.0, atol=2e-15)
        np.testing.assert_allclose(pr, p0, rtol=0.0, atol=3e-15)

    def test_operator_parameter_derivative_is_unchanged(self):
        # Subtracting 2I does not alter any edge/rank-one derivative.
        n = 5
        b = np.zeros(n)
        b[1] = 1.0
        b[3] = -1.0
        edge_stamp = np.outer(b, b)
        Q = np.eye(n) * 1.9 + 0.07 * edge_stamp
        eps = 1e-7
        K0 = kick_operator(Q)
        K1 = kick_operator(Q + eps * edge_stamp)
        np.testing.assert_allclose((K1 - K0) / eps, edge_stamp, rtol=0.0, atol=2e-9)


if __name__ == "__main__":
    unittest.main()
