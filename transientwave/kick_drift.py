"""Exact kick-drift coordinates for the TW reversible second-order recurrence.

The compiled wave recurrence

    z[n+1] = Q z[n] - z[n-1] + u[n]

contains a universal ~2*I inertial term for the continuous-wave source class.
Define the first difference

    p[n] = z[n] - z[n-1].

Then the same map is exactly the pair of shears

    p[n+1] = p[n] + (Q - 2 I) z[n] + u[n]
    z[n+1] = z[n] + p[n+1].

The two vectors ``(z,p)`` carry exactly the same information as the existing
``(CUR,PREV)`` banks, so adopting these coordinates does not by itself add
state storage.

A further exact compiler coordinate is the scaled momentum

    r[n] = lambda * p[n], lambda > 0,

which gives

    r[n+1] = r[n] + lambda*(Q-2I)z[n] + lambda*u[n]
    z[n+1] = z[n] + r[n+1]/lambda.

This exposes an explicit circuit trade: larger lambda increases kick/edge/source
range while reducing the drift coefficient and its sampled-cap thermal packet.

This module is algebra only. It does not claim the unity kick/drift shears are
noiseless in silicon.
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


def kick_to_scaled_momentum(z: Array, p: Array, scale: float) -> tuple[Array, Array]:
    lam = float(scale)
    if not np.isfinite(lam) or lam <= 0.0:
        raise ValueError("scale must be finite and positive")
    x = np.asarray(z, dtype=float)
    mom = np.asarray(p, dtype=float)
    if x.shape != mom.shape:
        raise ValueError("z and p must have the same shape")
    return x.copy(), lam * mom


def scaled_momentum_to_kick(z: Array, r: Array, scale: float) -> tuple[Array, Array]:
    lam = float(scale)
    if not np.isfinite(lam) or lam <= 0.0:
        raise ValueError("scale must be finite and positive")
    x = np.asarray(z, dtype=float)
    scaled = np.asarray(r, dtype=float)
    if x.shape != scaled.shape:
        raise ValueError("z and r must have the same shape")
    return x.copy(), scaled / lam


def pointer_swap_mirror_in_kick_coordinates(z: Array, p: Array) -> tuple[Array, Array]:
    """Exact image of the existing CUR<->PREV terminal mirror."""
    x = np.asarray(z, dtype=float)
    mom = np.asarray(p, dtype=float)
    if x.shape != mom.shape:
        raise ValueError("z and p must have the same shape")
    return x - mom, -mom


def pointer_swap_mirror_in_scaled_coordinates(
    z: Array, r: Array, scale: float
) -> tuple[Array, Array]:
    """Exact terminal mirror for r=lambda*p: Z<-Z-R/lambda, R<- -R."""
    lam = float(scale)
    if not np.isfinite(lam) or lam <= 0.0:
        raise ValueError("scale must be finite and positive")
    x = np.asarray(z, dtype=float)
    scaled = np.asarray(r, dtype=float)
    if x.shape != scaled.shape:
        raise ValueError("z and r must have the same shape")
    return x - scaled / lam, -scaled


def common_diff_terminal_boundary_in_kick_coordinates(
    forward_z: Array,
    forward_p: Array,
    terminal_error: Array,
) -> tuple[Array, Array, Array, Array]:
    """Map the v0.8 common/difference terminal boundary into (z,p)."""
    cz, cp = pointer_swap_mirror_in_kick_coordinates(forward_z, forward_p)
    err = np.asarray(terminal_error, dtype=float)
    if err.shape != cz.shape:
        raise ValueError("terminal_error must match state shape")
    return cz, cp, err.copy(), err.copy()


def common_diff_terminal_boundary_in_scaled_coordinates(
    forward_z: Array,
    forward_r: Array,
    terminal_error: Array,
    scale: float,
) -> tuple[Array, Array, Array, Array]:
    """v0.8 common/difference terminal boundary for r=lambda*p.

    Since the old D boundary has current=e_T and previous=0, p_D=e_T and
    therefore r_D=lambda*e_T.
    """
    lam = float(scale)
    cz, cr = pointer_swap_mirror_in_scaled_coordinates(forward_z, forward_r, lam)
    err = np.asarray(terminal_error, dtype=float)
    if err.shape != cz.shape:
        raise ValueError("terminal_error must match state shape")
    return cz, cr, err.copy(), lam * err


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


def scaled_kick_drift_step(
    z: Array, r: Array, K: Array, u: Array, scale: float
) -> tuple[Array, Array]:
    """Exact scaled-momentum shear with r=lambda*p."""
    lam = float(scale)
    if not np.isfinite(lam) or lam <= 0.0:
        raise ValueError("scale must be finite and positive")
    x = np.asarray(z, dtype=float)
    scaled = np.asarray(r, dtype=float)
    k = np.asarray(K, dtype=float)
    src = np.asarray(u, dtype=float)
    r_next = scaled + lam * (k @ x + src)
    z_next = x + r_next / lam
    return z_next, r_next


def inverse_kick_drift_step(z_next: Array, p_next: Array, K: Array, u: Array) -> tuple[Array, Array]:
    """Exact inverse of one kick-drift step for the same source sample."""
    xn = np.asarray(z_next, dtype=float)
    pn = np.asarray(p_next, dtype=float)
    k = np.asarray(K, dtype=float)
    src = np.asarray(u, dtype=float)
    z = xn - pn
    p = pn - k @ z - src
    return z, p


def inverse_scaled_kick_drift_step(
    z_next: Array, r_next: Array, K: Array, u: Array, scale: float
) -> tuple[Array, Array]:
    lam = float(scale)
    if not np.isfinite(lam) or lam <= 0.0:
        raise ValueError("scale must be finite and positive")
    xn = np.asarray(z_next, dtype=float)
    rn = np.asarray(r_next, dtype=float)
    k = np.asarray(K, dtype=float)
    src = np.asarray(u, dtype=float)
    z = xn - rn / lam
    r = rn - lam * (k @ z + src)
    return z, r


def decompose_kick_self_from_q_self(q_self: Array) -> Array:
    """The edge rank-one coefficients are unchanged; only local self shifts by -2."""
    return np.asarray(q_self, dtype=float) - 2.0
