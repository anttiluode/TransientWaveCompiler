"""Coordinate transform for fixed positive node-integrator packet gains.

Suppose the active node summing amplifiers apply one fixed measured positive
row gain D=diag(d_i) to every newly accumulated current/source packet while the
history term remains structural:

    z[n+1] = D Q_phys z[n] - z[n-1] + D u_phys[n].

With z=D^(1/2)x, choosing

    Q_phys = D^(-1/2) Q_logical D^(-1/2)
    u_phys = D^(-1/2) u_logical

recovers exactly

    x[n+1] = Q_logical x[n] - x[n-1] + u_logical[n].

Q_phys stays symmetric when Q_logical is symmetric.  Therefore static positive
node gain error is primarily a compiler calibration/range problem, not by
itself a reciprocity error.  Drift, lane dependence and signal/code dependence
are separate nonidealities and are not covered by this transform.
"""
from __future__ import annotations

import numpy as np


Array = np.ndarray


def _gain_vectors(gains: Array) -> tuple[Array, Array]:
    d = np.asarray(gains, dtype=float)
    if d.ndim != 1 or not len(d):
        raise ValueError("integrator gains must be a nonempty vector")
    if not np.all(np.isfinite(d)) or np.any(d <= 0.0):
        raise ValueError("integrator gains must be finite and strictly positive")
    root = np.sqrt(d)
    invroot = 1.0 / root
    return root, invroot


def compile_operator_for_integrator_gains(Q_logical: Array, gains: Array) -> Array:
    Q = np.asarray(Q_logical, dtype=float)
    root, invroot = _gain_vectors(gains)
    if Q.shape != (len(root), len(root)):
        raise ValueError("Q shape must match integrator gain vector")
    return invroot[:, None] * Q * invroot[None, :]


def compile_source_for_integrator_gains(source_logical: Array, gains: Array) -> Array:
    src = np.asarray(source_logical, dtype=float)
    _, invroot = _gain_vectors(gains)
    if src.shape[-1] != len(invroot):
        raise ValueError("source final dimension must match integrator gain vector")
    return src * invroot


def compile_readout_for_integrator_gains(readout_logical: Array, gains: Array) -> Array:
    c = np.asarray(readout_logical, dtype=float)
    _, invroot = _gain_vectors(gains)
    if c.shape != invroot.shape:
        raise ValueError("readout shape must match integrator gain vector")
    return c * invroot


def logical_to_physical_state(state_logical: Array, gains: Array) -> Array:
    x = np.asarray(state_logical, dtype=float)
    root, _ = _gain_vectors(gains)
    if x.shape[-1] != len(root):
        raise ValueError("state final dimension must match integrator gain vector")
    return x * root


def physical_to_logical_state(state_physical: Array, gains: Array) -> Array:
    z = np.asarray(state_physical, dtype=float)
    _, invroot = _gain_vectors(gains)
    if z.shape[-1] != len(invroot):
        raise ValueError("state final dimension must match integrator gain vector")
    return z * invroot


def physical_tick_with_integrator_gains(
    z: Array,
    zm1: Array,
    Q_phys: Array,
    source_phys: Array,
    gains: Array,
) -> Array:
    current = np.asarray(z, dtype=float)
    previous = np.asarray(zm1, dtype=float)
    Q = np.asarray(Q_phys, dtype=float)
    u = np.asarray(source_phys, dtype=float)
    d = np.asarray(gains, dtype=float)
    return d * (Q @ current + u) - previous
