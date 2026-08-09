"""Classical reciprocal coupled-resonator filter response and tuning utilities.

The model is the standard narrowband coupling-matrix representation

    A(gamma) = gamma I - j R + M

with reciprocal real-symmetric resonator coupling matrix M and endpoint
loading matrix R.  Scattering parameters are read from A^{-1}.

This module deliberately lives beside, rather than inside, the transient TW-1A
emulator.  It is a compiler/application bridge: both objects expose a sparse
symmetric graph operator, but the microwave coupling matrix uses the standard
frequency-domain narrowband normalization instead of the TW conformal
second-order time recurrence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class CouplingEdge:
    i: int
    j: int

    def stamp(self, n: int) -> np.ndarray:
        if self.i == self.j:
            raise ValueError("inter-resonator coupling edges must be off-diagonal")
        e = np.zeros((n, n), dtype=float)
        e[self.i, self.j] = 1.0
        e[self.j, self.i] = 1.0
        return e


def _validate_matrix(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("coupling matrix must be square")
    if not np.allclose(m, m.T, rtol=0.0, atol=1e-12):
        raise ValueError("coupling matrix must be reciprocal/symmetric")
    return m


def scattering(
    m: np.ndarray,
    gamma: np.ndarray | Sequence[float] | float,
    *,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (S11, S21) for normalized frequency gamma.

    Uses

        A = gamma I - j R + M
        S11 = 1 + 2j R1 [A^-1]_{11}
        S21 = -2j sqrt(R1 R2) [A^-1]_{N1}.
    """
    m = _validate_matrix(m)
    if r_in <= 0 or r_out <= 0:
        raise ValueError("endpoint loading parameters must be positive")
    n = m.shape[0]
    g = np.atleast_1d(np.asarray(gamma, dtype=float))
    r = np.zeros((n, n), dtype=float)
    r[0, 0] = float(r_in)
    r[-1, -1] = float(r_out)
    eye = np.eye(n, dtype=complex)

    s11 = np.empty(g.shape, dtype=complex)
    s21 = np.empty(g.shape, dtype=complex)
    scale21 = -2j * np.sqrt(float(r_in) * float(r_out))
    for idx, gi in np.ndenumerate(g):
        a = complex(float(gi)) * eye - 1j * r + m
        ainv = np.linalg.inv(a)
        s11[idx] = 1.0 + 2j * float(r_in) * ainv[0, 0]
        s21[idx] = scale21 * ainv[-1, 0]

    if np.ndim(gamma) == 0:
        return s11.reshape(()), s21.reshape(())
    return s11, s21


def scattering_with_edge_derivatives(
    m: np.ndarray,
    gamma: np.ndarray | Sequence[float],
    edges: Sequence[CouplingEdge],
    *,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return scattering and exact derivatives wrt reciprocal edge values.

    d A^-1 / dm_e = -A^-1 (dA/dm_e) A^-1.
    Returned derivative arrays have shape (n_frequency, n_edges).
    """
    m = _validate_matrix(m)
    n = m.shape[0]
    g = np.asarray(gamma, dtype=float).reshape(-1)
    r = np.zeros((n, n), dtype=float)
    r[0, 0] = float(r_in)
    r[-1, -1] = float(r_out)
    eye = np.eye(n, dtype=complex)
    stamps = [edge.stamp(n).astype(complex) for edge in edges]

    s11 = np.empty(len(g), dtype=complex)
    s21 = np.empty(len(g), dtype=complex)
    ds11 = np.empty((len(g), len(edges)), dtype=complex)
    ds21 = np.empty((len(g), len(edges)), dtype=complex)
    scale21 = -2j * np.sqrt(float(r_in) * float(r_out))

    for k, gi in enumerate(g):
        a = complex(float(gi)) * eye - 1j * r + m
        ainv = np.linalg.inv(a)
        s11[k] = 1.0 + 2j * float(r_in) * ainv[0, 0]
        s21[k] = scale21 * ainv[-1, 0]
        for q, stamp in enumerate(stamps):
            dinv = -(ainv @ stamp @ ainv)
            ds11[k, q] = 2j * float(r_in) * dinv[0, 0]
            ds21[k, q] = scale21 * dinv[-1, 0]
    return s11, s21, ds11, ds21


def matrix_from_edges(
    n: int,
    edges: Sequence[CouplingEdge],
    values: Sequence[float],
    *,
    diagonal: Sequence[float] | None = None,
) -> np.ndarray:
    if len(edges) != len(values):
        raise ValueError("one value is required per edge")
    m = np.zeros((n, n), dtype=float)
    if diagonal is not None:
        d = np.asarray(diagonal, dtype=float)
        if d.shape != (n,):
            raise ValueError("diagonal must have one value per resonator")
        np.fill_diagonal(m, d)
    for edge, value in zip(edges, values):
        if not (0 <= edge.i < n and 0 <= edge.j < n):
            raise ValueError("edge endpoint out of range")
        m[edge.i, edge.j] = float(value)
        m[edge.j, edge.i] = float(value)
    return m


def magnitude_response_loss_and_gradient(
    values: Sequence[float],
    *,
    n: int,
    edges: Sequence[CouplingEdge],
    gamma: np.ndarray,
    target_s11: np.ndarray,
    target_s21: np.ndarray,
    r_in: float = 1.0,
    r_out: float = 1.0,
    diagonal: Sequence[float] | None = None,
) -> tuple[float, np.ndarray]:
    """Mean squared |S11|+|S21| response error and exact edge gradient."""
    values = np.asarray(values, dtype=float)
    m = matrix_from_edges(n, edges, values, diagonal=diagonal)
    s11, s21, ds11, ds21 = scattering_with_edge_derivatives(
        m, gamma, edges, r_in=r_in, r_out=r_out
    )
    t11 = np.asarray(target_s11, dtype=complex).reshape(-1)
    t21 = np.asarray(target_s21, dtype=complex).reshape(-1)
    if s11.shape != t11.shape or s21.shape != t21.shape:
        raise ValueError("target response shape mismatch")

    mag11 = np.abs(s11)
    mag21 = np.abs(s21)
    target11 = np.abs(t11)
    target21 = np.abs(t21)
    e11 = mag11 - target11
    e21 = mag21 - target21
    loss = float(np.mean(e11 * e11 + e21 * e21))

    eps = 1e-15
    # d|s| = Re(conj(s)/|s| * ds), with zero-safe denominator.
    dmag11 = np.real((np.conj(s11) / np.maximum(mag11, eps))[:, None] * ds11)
    dmag21 = np.real((np.conj(s21) / np.maximum(mag21, eps))[:, None] * ds21)
    grad = 2.0 * np.mean(e11[:, None] * dmag11 + e21[:, None] * dmag21, axis=0)
    return loss, np.asarray(grad, dtype=float)


def response_error_metrics(
    m: np.ndarray,
    target_m: np.ndarray,
    gamma: np.ndarray,
    *,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> dict[str, float]:
    s11, s21 = scattering(m, gamma, r_in=r_in, r_out=r_out)
    t11, t21 = scattering(target_m, gamma, r_in=r_in, r_out=r_out)
    d11 = np.abs(s11) - np.abs(t11)
    d21 = np.abs(s21) - np.abs(t21)
    return {
        "mse_magnitude_response": float(np.mean(d11 * d11 + d21 * d21)),
        "rms_s11_magnitude_error": float(np.sqrt(np.mean(d11 * d11))),
        "rms_s21_magnitude_error": float(np.sqrt(np.mean(d21 * d21))),
        "max_s11_magnitude_error": float(np.max(np.abs(d11))),
        "max_s21_magnitude_error": float(np.max(np.abs(d21))),
    }
