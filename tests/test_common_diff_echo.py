import unittest

import numpy as np

from transientwave.common_diff_echo import (
    CommonDiffState,
    common_diff_reverse_tick,
    common_diff_to_pair,
    edge_credit_direct_product,
    edge_credit_from_common_diff,
    edge_credit_from_pair,
    pair_reverse_tick,
    pair_to_common_diff,
)


class CommonDifferenceEchoTests(unittest.TestCase):
    def test_identical_terminal_pair_maps_to_forward_common_and_exact_zero_diff(self):
        rng = np.random.default_rng(801)
        cur = rng.normal(size=11)
        prev = rng.normal(size=11)
        cc, cp, dc, dp = pair_to_common_diff(cur, prev, cur, prev)
        self.assertTrue(np.array_equal(cc, cur))
        self.assertTrue(np.array_equal(cp, prev))
        self.assertTrue(np.array_equal(dc, np.zeros_like(cur)))
        self.assertTrue(np.array_equal(dp, np.zeros_like(prev)))

    def test_one_tick_pair_and_common_diff_are_equivalent(self):
        rng = np.random.default_rng(802)
        n = 9
        a = rng.normal(size=(n, n))
        q = 0.08 * (a + a.T)
        cc = rng.normal(size=n)
        cp = rng.normal(size=n)
        dc = rng.normal(size=n)
        dp = rng.normal(size=n)
        src = rng.normal(scale=0.1, size=n)
        err = rng.normal(scale=0.03, size=n)

        pc, pp, mc, mp = common_diff_to_pair(cc, cp, dc, dp)
        pn, pc_old, mn, mc_old = pair_reverse_tick(pc, pp, mc, mp, q, src, err)
        ccn, ccp, dcn, dcp = common_diff_reverse_tick(cc, cp, dc, dp, q, src, err)
        epn, epp, emn, emp = common_diff_to_pair(ccn, ccp, dcn, dcp)

        self.assertTrue(np.allclose(pn, epn, rtol=2e-13, atol=2e-13))
        self.assertTrue(np.allclose(pc_old, epp, rtol=0, atol=0))
        self.assertTrue(np.allclose(mn, emn, rtol=2e-13, atol=2e-13))
        self.assertTrue(np.allclose(mc_old, emp, rtol=0, atol=0))

    def test_many_reverse_ticks_match_pair_trajectories(self):
        rng = np.random.default_rng(803)
        n = 7
        a = rng.normal(size=(n, n))
        q = 0.06 * (a + a.T)
        terminal_cur = rng.normal(size=n)
        terminal_prev = rng.normal(size=n)
        common_sources = rng.normal(scale=0.07, size=(80, n))
        errors = rng.normal(scale=0.02, size=(80, n))

        plus_cur = terminal_cur.copy()
        plus_prev = terminal_prev.copy()
        minus_cur = terminal_cur.copy()
        minus_prev = terminal_prev.copy()
        cd = CommonDiffState.from_forward_terminal(terminal_cur, terminal_prev)

        for src, err in zip(common_sources, errors):
            plus_cur, plus_prev, minus_cur, minus_prev = pair_reverse_tick(
                plus_cur, plus_prev, minus_cur, minus_prev, q, src, err
            )
            cd.tick(q, src, err)
            epc, epp, emc, emp = common_diff_to_pair(
                cd.common_current,
                cd.common_previous,
                cd.diff_current,
                cd.diff_previous,
            )
            self.assertTrue(np.allclose(plus_cur, epc, rtol=2e-11, atol=2e-11))
            self.assertTrue(np.allclose(plus_prev, epp, rtol=2e-11, atol=2e-11))
            self.assertTrue(np.allclose(minus_cur, emc, rtol=2e-11, atol=2e-11))
            self.assertTrue(np.allclose(minus_prev, emp, rtol=2e-11, atol=2e-11))

    def test_credit_square_identity_is_exact_common_diff_product(self):
        rng = np.random.default_rng(804)
        c = rng.normal(size=112)
        d = rng.normal(size=112)
        pair = edge_credit_from_pair(c + d, c - d)
        rebuilt = edge_credit_from_common_diff(c, d)
        direct = edge_credit_direct_product(c, d)
        self.assertTrue(np.allclose(pair, rebuilt, rtol=2e-14, atol=2e-14))
        self.assertTrue(np.allclose(rebuilt, direct, rtol=2e-14, atol=2e-14))

    def test_error_is_single_signed_source_on_difference_lane(self):
        q = np.zeros((2, 2), dtype=float)
        zeros = np.zeros(2)
        err = np.asarray([0.2, -0.3])
        state = CommonDiffState.from_forward_terminal(zeros, zeros)
        state.tick(q, zeros, err)
        self.assertTrue(np.array_equal(state.common_current, zeros))
        self.assertTrue(np.array_equal(state.diff_current, err))
        plus, _, minus, _ = common_diff_to_pair(
            state.common_current,
            state.common_previous,
            state.diff_current,
            state.diff_previous,
        )
        self.assertTrue(np.array_equal(plus, err))
        self.assertTrue(np.array_equal(minus, -err))


if __name__ == "__main__":
    unittest.main()
