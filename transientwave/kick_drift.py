"""Exact kick-drift coordinates for the TW reversible second-order recurrence.

The compiled wave recurrence

    z[n+1] = Q z[n] - z[n-1] + u[n]

contains a universal ~2*I inertial term for the continuous-wave source class.
Define the first difference

    p[n] = z[n] - z[n-1].

Then the same map is exactly the pair of shears

    p[n+1] = p[n] + (Q - 2 I) z[n] + u[n]
    z[n+1] = z[n] + p[n+1].

This module is algebra only.  It does not claim that the fixed unity drift shear
is noiseless in silicon.  The circuit question is whether that fixed primitive
can be implemented more cheaply/quietly than resampling a programmable self
coefficient near +2 on every node and tick.
"""
from __future__ import annotations

import numpy as np


Array = np.ndarray


def kick_operator(Q: Array) -> Array:
    q = np.asarray(Q, dtype=float)
    if q.ndim != 2 or q.shape[0] != q.shape[1]:
        raise ValueError("Q must be square")
    return q - 2.0 * np.eye(q.shape[0], dtype=float)


def position_history_to_kick_state(z: Array, z_previous: Array) -> tuple[Array, Array]:
    x = np.asarray(z, dtype=float)
    xp = np.asarray(z_previous, dtype=float)
    if x.shape != xp.shape:
        raise ValueError("z and z_previous must have the same shape")
    return x.copy(), x - xp


def kick_state_to_position_history(z: Array, p: Array) -> tuple[Array, Array]:
    x = np.asarray(z, dtype=float)
    v = np.asarray(p, dtype=float)
    if x.shape != v.shape:
        raise ValueError("z and p must have the same shape")
    return x.copy(), x - v


def second_order_step(z: Array, z_previous: Array, Q: Array, u: Array) -> tuple[Array, Array]:
    x = np.asarray(z, dtype=float)
    xp = np.asarray(z_previous, dtype=float)
    q = np.asarray(Q, dtype=float)
    src = np.asarray(u, dtype=float)
    nxt = q @ x - xp + src
    return nxt, x.copy()


def kick_drift_step(z: Array, p: Array, K: Array, u: Array) -> tuple[Array, Array]:
    x = np.asarray(z, dtype=float)
    mom = np.asarray(p, dtype=float)
    k = np.asarray(K, dtype=float)
    src = np.asarray(u, dtype=float)
    p_next = mom + k @ x + src
    z_next = x + p_next
    return z_next, p_next


def inverse_kick_drift_step(z_next: Array, p_next: Array, K: Array, u: Array) -> tuple[Array, Array]:
    """Exact inverse of one kick-drift step for the same source sample."""
    xn = np.asarray(z_next, dtype=float)
    pn = np.asarray(p_next, dtype=float)
    k = np.asarray(K, dtype=float)
    src = np.asarray(u, dtype=float)
    z = xn - pn
    p = pn - k @ z - src
    return z, p


def decompose_kick_self_from_q_self(q_self: Array) -> Array:
    """The edge rank-one coefficients are unchanged; only local self shifts by -2."""
    return np.asarray(q_self, dtype=float) - 2.0
