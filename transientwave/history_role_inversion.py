"""Exact two-bank implementation of the fixed ``-PREV`` recurrence term.

The second-order TW recurrence is

    z[n+1] = Q z[n] - z[n-1] + u[n].

A conventional circuit reading suggests a matched unity inverting transfer from
PREV into a separate NEXT summing state.  But TW nodes already require two state
banks and treat CUR/PREV as logical roles.  The old PREV bank can itself become
the NEXT destination:

1. keep its stored physical differential charge unchanged;
2. toggle only the logical differential polarity used for that bank;
3. the bank's logical initial value is now exactly ``-z[n-1]``;
4. accumulate ``Q z[n] + u[n]`` onto that same bank in its new orientation;
5. swap CUR/PREV role pointers.

This module is an algebraic reference model for that schedule.  It contains no
analog gain parameter for ``-PREV`` because the coefficient is implemented by
role/polarity control rather than a sampled ratio.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


Array = np.ndarray


@dataclass
class TwoBankRoleState:
    """Two physical differential banks plus logical role and orientation tags.

    ``bank_voltage[k]`` is the physical differential voltage/charge coordinate
    of bank k in its fixed physical terminal orientation.  ``polarity[k]`` is
    +1 or -1 and maps physical voltage to logical state when that bank is read:

        logical = polarity[k] * bank_voltage[k].
    """

    bank_voltage: Array
    polarity: Array
    cur_bank: int
    prev_bank: int

    @classmethod
    def from_logical(cls, current: Array, previous: Array) -> "TwoBankRoleState":
        cur = np.asarray(current, dtype=float)
        prev = np.asarray(previous, dtype=float)
        if cur.shape != prev.shape:
            raise ValueError("current/previous shape mismatch")
        bank_voltage = np.stack([cur.copy(), prev.copy()], axis=0)
        polarity = np.ones_like(bank_voltage)
        return cls(bank_voltage=bank_voltage, polarity=polarity, cur_bank=0, prev_bank=1)

    def logical_bank(self, bank: int) -> Array:
        return self.polarity[bank] * self.bank_voltage[bank]

    @property
    def current(self) -> Array:
        return self.logical_bank(self.cur_bank)

    @property
    def previous(self) -> Array:
        return self.logical_bank(self.prev_bank)

    def tick(self, Q: Array, source: Array) -> Array:
        """Advance one recurrence using PREV-as-NEXT polarity inversion."""
        q = np.asarray(Q, dtype=float)
        u = np.asarray(source, dtype=float)
        x = self.current.copy()
        xm1 = self.previous.copy()
        if q.shape != (len(x), len(x)):
            raise ValueError("Q shape mismatch")
        if u.shape != x.shape:
            raise ValueError("source shape mismatch")

        destination = self.prev_bank

        # Toggle only interpretation/wiring polarity.  Physical stored charge is
        # untouched, so the logical destination immediately becomes -x[n-1].
        self.polarity[destination] *= -1.0
        assert np.array_equal(self.logical_bank(destination), -xm1)

        # Add the positive recurrence contribution in the destination's *new*
        # logical orientation.  To change logical state by delta, physical bank
        # voltage changes by polarity*delta.
        delta = q @ x + u
        self.bank_voltage[destination] += self.polarity[destination] * delta

        next_state = self.logical_bank(destination).copy()

        # Old CUR is still physically untouched and therefore becomes PREV.
        old_cur = self.cur_bank
        self.cur_bank = destination
        self.prev_bank = old_cur
        return next_state


def ordinary_tick(current: Array, previous: Array, Q: Array, source: Array) -> Array:
    return np.asarray(Q, dtype=float) @ np.asarray(current, dtype=float) - np.asarray(
        previous, dtype=float
    ) + np.asarray(source, dtype=float)


def run_role_inversion(
    current: Array,
    previous: Array,
    Q: Array,
    sources: Array,
) -> Array:
    """Return logical trajectory from the two-bank role-inversion schedule."""
    state = TwoBankRoleState.from_logical(current, previous)
    src = np.asarray(sources, dtype=float)
    trace = []
    for u in src:
        trace.append(state.tick(Q, u))
    return np.asarray(trace)
