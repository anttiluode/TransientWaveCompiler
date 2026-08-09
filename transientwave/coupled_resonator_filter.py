"""Classical reciprocal coupled-resonator filter response and tuning utilities.

The model is the standard narrowband coupling-matrix representation

    A(gamma) = gamma I - j R + M

with reciprocal real-symmetric resonator coupling matrix M and endpoint
loading matrix R. Scattering parameters are read from A^{-1}.

This module deliberately lives beside, rather than inside, the transient TW-1A
emulator. It is a compiler/application bridge: both objects expose a sparse
symmetric graph operator, but the microwave coupling matrix uses the standard
frequency-domain narrowband normalization instead of the TW conformal
second-order time recurrence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class MatrixParameter:
    """One independently tunable reciprocal coupling-matrix coefficient.

    ``i == j`` is a resonator self-detuning / diagonal tuning knob.
    ``i != j`` is one reciprocal inter-resonator coupling and stamps both
    symmetric matrix entries with the same scalar coefficient.
    """

    i: int
    j: int
    name: str = ""

    def stamp(self, n: int) -> np.ndarray:
        if not (0 <= self.i < n and 0 <= self.j < n):
            raise ValueError("matrix-parameter endpoint out of range")
        e = np.zeros((n, n), dtype=float)
        e[self.i, self.j] = 1.0
        if self.i != self.j:
            e[self.j, self.i] = 1.0
        return e


@dataclass(frozen=True)
class CouplingEdge:
    """Backward-compatible off-diagonal reciprocal coupling parameter."""

    i: int
    j: int

    def stamp(self, n: int) -> np.ndarray:
        if self.i == self.j:
            raise ValueError("inter-resonator coupling edges must be off-diagonal")
        return MatrixParameter(self.i, self.j).stamp(n)


ParameterLike = MatrixParameter | CouplingEdge


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


def scattering_with_parameter_derivatives(
    m: np.ndarray,
    gamma: np.ndarray | Sequence[float],
    parameters: Sequence[ParameterLike],
    *,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return scattering and exact derivatives wrt reciprocal parameters.

    This handles both diagonal resonator self-detuning coefficients and
    reciprocal off-diagonal couplings through

        d A^-1 / dp = -A^-1 (dA/dp) A^-1.

    Returned derivative arrays have shape ``(n_frequency, n_parameters)``.
    """
    m = _validate_matrix(m)
    n = m.shape[0]
    g = np.asarray(gamma, dtype=float).reshape(-1)
    r = np.zeros((n, n), dtype=float)
    r[0, 0] = float(r_in)
    r[-1, -1] = float(r_out)
    eye = np.eye(n, dtype=complex)
    stamps = [parameter.stamp(n).astype(complex) for parameter in parameters]

    s11 = np.empty(len(g), dtype=complex)
    s21 = np.empty(len(g), dtype=complex)
    ds11 = np.empty((len(g), len(parameters)), dtype=complex)
    ds21 = np.empty((len(g), len(parameters)), dtype=complex)
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


def scattering_with_edge_derivatives(
    m: np.ndarray,
    gamma: np.ndarray | Sequence[float],
    edges: Sequence[CouplingEdge],
    *,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Backward-compatible edge-only derivative wrapper."""
    return scattering_with_parameter_derivatives(
        m, gamma, edges, r_in=r_in, r_out=r_out
    )


def matrix_from_parameters(
    n: int,
    parameters: Sequence[ParameterLike],
    values: Sequence[float],
) -> np.ndarray:
    """Assemble a real-symmetric coupling matrix from independent knobs."""
    if len(parameters) != len(values):
        raise ValueError("one value is required per matrix parameter")
    m = np.zeros((n, n), dtype=float)
    occupied: set[tuple[int, int]] = set()
    for parameter, value in zip(parameters, values):
        if not (0 <= parameter.i < n and 0 <= parameter.j < n):
            raise ValueError("matrix-parameter endpoint out of range")
        key = tuple(sorted((int(parameter.i), int(parameter.j))))
        if key in occupied:
            raise ValueError(f"duplicate matrix parameter for entries {key}")
        occupied.add(key)
        m += float(value) * parameter.stamp(n)
    return m


def matrix_from_edges(
    n: int,
    edges: Sequence[CouplingEdge],
    values: Sequence[float],
    *,
    diagonal: Sequence[float] | None = None,
) -> np.ndarray:
    """Backward-compatible edge matrix builder with optional fixed diagonal."""
    m = matrix_from_parameters(n, edges, values)
    if diagonal is not None:
        d = np.asarray(diagonal, dtype=float)
        if d.shape != (n,):
            raise ValueError("diagonal must have one value per resonator")
        np.fill_diagonal(m, d)
    return m


def magnitude_response_loss_and_parameter_gradient(
    values: Sequence[float],
    *,
    n: int,
    parameters: Sequence[ParameterLike],
    gamma: np.ndarray,
    target_s11: np.ndarray,
    target_s21: np.ndarray,
    r_in: float = 1.0,
    r_out: float = 1.0,
) -> tuple[float, np.ndarray]:
    """Mean squared |S11|+|S21| response error and exact knob gradient."""
    values = np.asarray(values, dtype=float)
    m = matrix_from_parameters(n, parameters, values)
    s11, s21, ds11, ds21 = scattering_with_parameter_derivatives(
        m, gamma, parameters, r_in=r_in, r_out=r_out
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
    """Backward-compatible edge-only response loss/gradient."""
    if diagonal is None:
        return magnitude_response_loss_and_parameter_gradient(
            values,
            n=n,
            parameters=edges,
            gamma=gamma,
            target_s11=target_s11,
            target_s21=target_s21,
            r_in=r_in,
            r_out=r_out,
        )

    # Preserve the original fixed-diagonal API. The derivative parameters are
    # still only the off-diagonal edge values.
    values = np.asarray(values, dtype=float)
    m = matrix_from_edges(n, edges, values, diagonal=diagonal)
    s11, s21, ds11, ds21 = scattering_with_parameter_derivatives(
        m, gamma, edges, r_in=r_in, r_out=r_out
    )
    t11 = np.asarray(target_s11, dtype=complex).reshape(-1)
    t21 = np.asarray(target_s21, dtype=complex).reshape(-1)
    mag11 = np.abs(s11)
    mag21 = np.abs(s21)
    e11 = mag11 - np.abs(t11)
    e21 = mag21 - np.abs(t21)
    loss = float(np.mean(e11 * e11 + e21 * e21))
    eps = 1e-15
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
