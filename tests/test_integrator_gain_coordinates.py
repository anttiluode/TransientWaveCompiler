import unittest

import numpy as np

from transientwave.integrator_gain_coordinates import (
    compile_operator_for_integrator_gains,
    compile_readout_for_integrator_gains,
    compile_source_for_integrator_gains,
    logical_to_physical_state,
    physical_tick_with_integrator_gains,
    physical_to_logical_state,
)


class IntegratorGainCoordinateTests(unittest.TestCase):
    def test_compiled_operator_stays_symmetric(self):
        rng = np.random.default_rng(12)
        a = rng.normal(size=(8, 8))
        q = 0.1 * (a + a.T)
        d = np.exp(rng.normal(scale=0.3, size=8))
        qp = compile_operator_for_integrator_gains(q, d)
        self.assertTrue(np.allclose(qp, qp.T, rtol=0, atol=1e-14))

    def test_one_tick_recovers_logical_recurrence(self):
        rng = np.random.default_rng(13)
        n = 9
        a = rng.normal(size=(n, n))
        q = 0.08 * (a + a.T)
        d = np.exp(rng.normal(scale=0.4, size=n))
        x = rng.normal(size=n)
        xm1 = rng.normal(size=n)
        u = rng.normal(scale=0.1, size=n)

        qp = compile_operator_for_integrator_gains(q, d)
        up = compile_source_for_integrator_gains(u, d)
        z = logical_to_physical_state(x, d)
        zm1 = logical_to_physical_state(xm1, d)
        znext = physical_tick_with_integrator_gains(z, zm1, qp, up, d)
        actual = physical_to_logical_state(znext, d)
        expected = q @ x - xm1 + u
        self.assertTrue(np.allclose(actual, expected, rtol=2e-13, atol=2e-13))

    def test_many_ticks_recover_logical_trajectory(self):
        rng = np.random.default_rng(14)
        n = 6
        a = rng.normal(size=(n, n))
        q = 0.06 * (a + a.T)
        d = np.exp(rng.normal(scale=0.5, size=n))
        x = rng.normal(size=n)
        xm1 = rng.normal(size=n)
        source = rng.normal(scale=0.08, size=(60, n))

        qp = compile_operator_for_integrator_gains(q, d)
        source_p = compile_source_for_integrator_gains(source, d)
        z = logical_to_physical_state(x, d)
        zm1 = logical_to_physical_state(xm1, d)
        logical_cur = x.copy()
        logical_prev = xm1.copy()
        for u, up in zip(source, source_p):
            znext = physical_tick_with_integrator_gains(z, zm1, qp, up, d)
            expected = q @ logical_cur - logical_prev + u
            actual = physical_to_logical_state(znext, d)
            self.assertTrue(np.allclose(actual, expected, rtol=2e-11, atol=2e-11))
            zm1, z = z, znext
            logical_prev, logical_cur = logical_cur, expected

    def test_readout_is_invariant_under_state_coordinates(self):
        rng = np.random.default_rng(15)
        x = rng.normal(size=7)
        c = rng.normal(size=7)
        d = np.exp(rng.normal(scale=0.25, size=7))
        z = logical_to_physical_state(x, d)
        cp = compile_readout_for_integrator_gains(c, d)
        self.assertAlmostEqual(float(cp @ z), float(c @ x), places=12)

    def test_nonpositive_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_operator_for_integrator_gains(np.eye(2), np.asarray([1.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
