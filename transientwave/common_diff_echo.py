"""Common/difference coordinates for the TW echo reverse pair.

The existing lockstep circuit carries two reverse wave states

    plus  = F + A
    minus = F - A

and therefore needs a terminal analog clone plus a +/- error injection pair.
Because the body recurrence is linear, the same information can instead be
stored as

    common = (plus + minus)/2 = F
    diff   = (plus - minus)/2 = A.

At the end of the forward pass ``common`` is simply the mirrored forward state
and ``diff`` starts from exact zero.  No terminal analog copy is required.
During reverse, the common lane receives the ordinary retrace source and the
difference lane receives one error waveform with one polarity:

    common[n+1] = Q common[n] - common[n-1] + source[n]
    diff[n+1]   = Q diff[n]   - diff[n-1]   + error[n].

The old PLUS/MINUS edge fields are reconstructed only at the local credit
sensor:

    delta_plus  = delta_common + delta_diff
    delta_minus = delta_common - delta_diff.

Thus the same square-difference credit identity is retained without storing two
full F+/-A trajectories and without a +/- error-DAC gain match requirement.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


Array = np.ndarray


def second_order_tick(current: Array, previous: Array, Q: Array, source: Array) -> Array:
    return np.asarray(Q, dtype=float) @ np.asarray(current, dtype=float) - np.asarray(
        previous, dtype=float
    ) + np.asarray(source, dtype=float)


def pair_to_common_diff(
    plus_current: Array,
    plus_previous: Array,
    minus_current: Array,
    minus_previous: Array,
) -> tuple[Array, Array, Array, Array]:
    pc = np.asarray(plus_current, dtype=float)
    pp = np.asarray(plus_previous, dtype=float)
    mc = np.asarray(minus_current, dtype=float)
    mp = np.asarray(minus_previous, dtype=float)
    return (
        0.5 * (pc + mc),
        0.5 * (pp + mp),
        0.5 * (pc - mc),
        0.5 * (pp - mp),
    )


def common_diff_to_pair(
    common_current: Array,
    common_previous: Array,
    diff_current: Array,
    diff_previous: Array,
) -> tuple[Array, Array, Array, Array]:
    cc = np.asarray(common_current, dtype=float)
    cp = np.asarray(common_previous, dtype=float)
    dc = np.asarray(diff_current, dtype=float)
    dp = np.asarray(diff_previous, dtype=float)
    return cc + dc, cp + dp, cc - dc, cp - dp


def pair_reverse_tick(
    plus_current: Array,
    plus_previous: Array,
    minus_current: Array,
    minus_previous: Array,
    Q: Array,
    common_source: Array,
    error_source: Array,
) -> tuple[Array, Array, Array, Array]:
    plus_next = second_order_tick(
        plus_current, plus_previous, Q, np.asarray(common_source) + np.asarray(error_source)
    )
    minus_next = second_order_tick(
        minus_current,
        minus_previous,
        Q,
        np.asarray(common_source) - np.asarray(error_source),
    )
    return plus_next, np.asarray(plus_current).copy(), minus_next, np.asarray(minus_current).copy()


def common_diff_reverse_tick(
    common_current: Array,
    common_previous: Array,
    diff_current: Array,
    diff_previous: Array,
    Q: Array,
    common_source: Array,
    error_source: Array,
) -> tuple[Array, Array, Array, Array]:
    common_next = second_order_tick(common_current, common_previous, Q, common_source)
    diff_next = second_order_tick(diff_current, diff_previous, Q, error_source)
    return (
        common_next,
        np.asarray(common_current).copy(),
        diff_next,
        np.asarray(diff_current).copy(),
    )


def edge_credit_from_pair(delta_plus: Array, delta_minus: Array) -> Array:
    p = np.asarray(delta_plus, dtype=float)
    m = np.asarray(delta_minus, dtype=float)
    return 0.25 * (p * p - m * m)


def edge_credit_from_common_diff(delta_common: Array, delta_diff: Array) -> Array:
    c = np.asarray(delta_common, dtype=float)
    d = np.asarray(delta_diff, dtype=float)
    plus = c + d
    minus = c - d
    return 0.25 * (plus * plus - minus * minus)


def edge_credit_direct_product(delta_common: Array, delta_diff: Array) -> Array:
    return np.asarray(delta_common, dtype=float) * np.asarray(delta_diff, dtype=float)


@dataclass
class CommonDiffState:
    common_current: Array
    common_previous: Array
    diff_current: Array
    diff_previous: Array

    @classmethod
    def from_forward_terminal(cls, current: Array, previous: Array) -> "CommonDiffState":
        current = np.asarray(current, dtype=float)
        previous = np.asarray(previous, dtype=float)
        return cls(
            common_current=current.copy(),
            common_previous=previous.copy(),
            diff_current=np.zeros_like(current),
            diff_previous=np.zeros_like(previous),
        )

    def tick(self, Q: Array, common_source: Array, error_source: Array) -> None:
        (
            self.common_current,
            self.common_previous,
            self.diff_current,
            self.diff_previous,
        ) = common_diff_reverse_tick(
            self.common_current,
            self.common_previous,
            self.diff_current,
            self.diff_previous,
            Q,
            common_source,
            error_source,
        )
