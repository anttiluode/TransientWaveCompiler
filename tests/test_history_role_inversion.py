import unittest

import numpy as np

from transientwave.history_role_inversion import (
    TwoBankRoleState,
    ordinary_tick,
    run_role_inversion,
)


class HistoryRoleInversionTests(unittest.TestCase):
    def test_one_tick_matches_ordinary_recurrence(self):
        Q = np.asarray([[1.1, -0.2], [-0.2, 1.3]], dtype=float)
        x = np.asarray([0.4, -0.7])
        xm1 = np.asarray([-0.1, 0.25])
        u = np.asarray([0.03, -0.04])
        state = TwoBankRoleState.from_logical(x, xm1)
        expected = ordinary_tick(x, xm1, Q, u)
        actual = state.tick(Q, u)
        self.assertTrue(np.array_equal(actual, expected))
        self.assertTrue(np.array_equal(state.current, expected))
        self.assertTrue(np.array_equal(state.previous, x))

    def test_many_ticks_match_ordinary_recurrence_for_dense_random_system(self):
        rng = np.random.default_rng(901)
        n = 7
        a = rng.normal(size=(n, n))
        Q = 0.15 * (a + a.T)
        x = rng.normal(size=n)
        xm1 = rng.normal(size=n)
        sources = rng.normal(scale=0.1, size=(50, n))

        physical = run_role_inversion(x, xm1, Q, sources)
        expected = []
        cur = x.copy()
        prev = xm1.copy()
        for u in sources:
            nxt = ordinary_tick(cur, prev, Q, u)
            expected.append(nxt)
            prev, cur = cur, nxt
        expected = np.asarray(expected)
        self.assertTrue(np.array_equal(physical, expected))

    def test_each_destination_flip_is_charge_preserving_before_accumulation(self):
        x = np.asarray([0.75, -0.25])
        xm1 = np.asarray([0.20, 0.60])
        state = TwoBankRoleState.from_logical(x, xm1)
        destination = state.prev_bank
        physical_before = state.bank_voltage[destination].copy()
        logical_before = state.previous.copy()

        state.polarity[destination] *= -1.0
        self.assertTrue(np.array_equal(state.bank_voltage[destination], physical_before))
        self.assertTrue(np.array_equal(state.logical_bank(destination), -logical_before))

    def test_two_banks_alternate_roles_without_copying_old_cur(self):
        Q = np.asarray([[0.4]], dtype=float)
        sources = np.zeros((8, 1), dtype=float)
        state = TwoBankRoleState.from_logical(np.asarray([1.0]), np.asarray([0.2]))
        roles = []
        for u in sources:
            roles.append((state.cur_bank, state.prev_bank))
            state.tick(Q, u)
        self.assertEqual(
            roles,
            [(0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0)],
        )

    def test_zero_Q_exposes_exact_topological_minus_prev(self):
        Q = np.zeros((3, 3), dtype=float)
        x = np.asarray([1.0, 2.0, 3.0])
        xm1 = np.asarray([0.1, -0.2, 0.3])
        state = TwoBankRoleState.from_logical(x, xm1)
        nxt = state.tick(Q, np.zeros(3))
        self.assertTrue(np.array_equal(nxt, -xm1))


if __name__ == "__main__":
    unittest.main()
