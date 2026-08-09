import unittest

import numpy as np

from transientwave.kick_drift import (
    common_diff_terminal_boundary_in_scaled_coordinates,
    inverse_scaled_kick_drift_step,
    kick_drift_step,
    kick_operator,
    kick_to_scaled_momentum,
    scaled_kick_drift_step,
    scaled_momentum_to_kick,
)


class ScaledKickDriftTests(unittest.TestCase):
    def test_scaled_step_matches_unscaled_for_multiple_scales(self):
        rng = np.random.default_rng(21)
        n = 9
        a = rng.normal(size=(n, n))
        Q = np.eye(n) * 1.9 + (a + a.T) * 0.01
        K = kick_operator(Q)
        z = rng.normal(size=n) * 0.1
        p = rng.normal(size=n) * 0.02
        u = rng.normal(size=n) * 0.003
        z_ref, p_ref = kick_drift_step(z, p, K, u)
        for lam in (0.5, 1.0, 2.0, 4.0, 16.0):
            zs, r = kick_to_scaled_momentum(z, p, lam)
            z1, r1 = scaled_kick_drift_step(zs, r, K, u, lam)
            _, p1 = scaled_momentum_to_kick(z1, r1, lam)
            np.testing.assert_allclose(z1, z_ref, rtol=0.0, atol=3e-15)
            np.testing.assert_allclose(p1, p_ref, rtol=0.0, atol=3e-15)

    def test_scaled_inverse_retraces(self):
        rng = np.random.default_rng(22)
        n = 7
        a = rng.normal(size=(n, n))
        K = (a + a.T) * 0.02
        z = rng.normal(size=n)
        r = rng.normal(size=n)
        u = rng.normal(size=n) * 0.01
        for lam in (1.0, 2.0, 5.0):
            z1, r1 = scaled_kick_drift_step(z, r, K, u, lam)
            z0, r0 = inverse_scaled_kick_drift_step(z1, r1, K, u, lam)
            np.testing.assert_allclose(z0, z, rtol=0.0, atol=3e-15)
            np.testing.assert_allclose(r0, r, rtol=0.0, atol=5e-15)

    def test_scaled_common_diff_boundary_matches_unscaled_meaning(self):
        rng = np.random.default_rng(23)
        z = rng.normal(size=8) * 0.1
        p = rng.normal(size=8) * 0.02
        e = rng.normal(size=8) * 0.01
        for lam in (1.0, 2.0, 4.0, 10.0):
            _, r = kick_to_scaled_momentum(z, p, lam)
            cz, cr, dz, dr = common_diff_terminal_boundary_in_scaled_coordinates(
                z, r, e, lam
            )
            _, cp = scaled_momentum_to_kick(cz, cr, lam)
            _, dp = scaled_momentum_to_kick(dz, dr, lam)
            np.testing.assert_allclose(cz, z - p, rtol=0.0, atol=3e-15)
            np.testing.assert_allclose(cp, -p, rtol=0.0, atol=3e-15)
            np.testing.assert_array_equal(dz, e)
            np.testing.assert_allclose(dp, e, rtol=0.0, atol=3e-15)

    def test_invalid_scale_rejected(self):
        z = np.zeros(2)
        r = np.zeros(2)
        K = np.zeros((2, 2))
        u = np.zeros(2)
        for lam in (0.0, -1.0):
            with self.assertRaises(ValueError):
                scaled_kick_drift_step(z, r, K, u, lam)


if __name__ == "__main__":
    unittest.main()
