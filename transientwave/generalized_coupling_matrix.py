"""Generalized source/resonator/load coupling-matrix response and gradients.

This implements the standard explicit-port formulation used for cross-coupled
microwave filters:

    A(Omega) = M + Omega U - j q
    S11      = 1 + 2j [A^-1]_{S,S}
    S21      = -2j [A^-1]_{L,S}

where the first and last matrix nodes are source/load ports, ``U`` is one on
resonator diagonal entries and zero at the ports, and ``q`` is one only at the
source/load diagonal entries.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters


def _validate_explicit_port_matrix(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1] or m.shape[0] < 3:
        raise ValueError("explicit-port coupling matrix must be square with >=3 nodes")
    if not np.allclose(m, m.T, rtol=0.0, atol=1e-12):
        raise ValueError("coupling matrix must be reciprocal/symmetric")
    return m


def generalized_scattering(
    m: np.ndarray,
    omega: np.ndarray | Sequence[float] | float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return S11 and S21 for an explicit source/resonator/load matrix."""
    m = _validate_explicit_port_matrix(m)
    n = m.shape[0]
    w = np.atleast_1d(np.asarray(omega, dtype=float))
    u = np.eye(n, dtype=complex)
    u[0, 0] = 0.0
    u[-1, -1] = 0.0
    q = np.zeros((n, n), dtype=complex)
    q[0, 0] = 1.0
    q[-1, -1] = 1.0

    s11 = np.empty(w.shape, dtype=complex)
    s21 = np.empty(w.shape, dtype=complex)
    for idx, wi in np.ndenumerate(w):
        a = m.astype(complex) + complex(float(wi)) * u - 1j * q
        ainv = np.linalg.inv(a)
        s11[idx] = 1.0 + 2j * ainv[0, 0]
        s21[idx] = -2j * ainv[-1, 0]

    if np.ndim(omega) == 0:
        return s11.reshape(()), s21.reshape(())
    return s11, s21


def generalized_scattering_with_parameter_derivatives(
    m: np.ndarray,
    omega: np.ndarray | Sequence[float],
    parameters: Sequence[MatrixParameter],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return explicit-port S parameters and exact derivatives wrt M knobs."""
    m = _validate_explicit_port_matrix(m)
    n = m.shape[0]
    w = np.asarray(omega, dtype=float).reshape(-1)
    u = np.eye(n, dtype=complex)
    u[0, 0] = 0.0
    u[-1, -1] = 0.0
    q = np.zeros((n, n), dtype=complex)
    q[0, 0] = 1.0
    q[-1, -1] = 1.0
    stamps = [p.stamp(n).astype(complex) for p in parameters]

    s11 = np.empty(len(w), dtype=complex)
    s21 = np.empty(len(w), dtype=complex)
    ds11 = np.empty((len(w), len(parameters)), dtype=complex)
    ds21 = np.empty((len(w), len(parameters)), dtype=complex)

    for k, wi in enumerate(w):
        a = m.astype(complex) + complex(float(wi)) * u - 1j * q
        ainv = np.linalg.inv(a)
        s11[k] = 1.0 + 2j * ainv[0, 0]
        s21[k] = -2j * ainv[-1, 0]
        for pidx, stamp in enumerate(stamps):
            dinv = -(ainv @ stamp @ ainv)
            ds11[k, pidx] = 2j * dinv[0, 0]
            ds21[k, pidx] = -2j * dinv[-1, 0]
    return s11, s21, ds11, ds21


def complex_response_loss_and_gradient(
    values: Sequence[float],
    *,
    n: int,
    parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    target_s11: np.ndarray,
    target_s21: np.ndarray,
) -> tuple[float, np.ndarray]:
    """Mean complex S-parameter error and exact gradient.

    Complex S parameters are intentionally used here because a calibrated VNA
    supplies phase as well as magnitude, and phase removes response ambiguities
    that are irrelevant to the matrix-algebra benchmark but important for knob
    recovery.
    """
    x = np.asarray(values, dtype=float)
    m = matrix_from_parameters(n, parameters, x)
    s11, s21, ds11, ds21 = generalized_scattering_with_parameter_derivatives(
        m, omega, parameters
    )
    t11 = np.asarray(target_s11, dtype=complex).reshape(-1)
    t21 = np.asarray(target_s21, dtype=complex).reshape(-1)
    if s11.shape != t11.shape or s21.shape != t21.shape:
        raise ValueError("target response shape mismatch")

    e11 = s11 - t11
    e21 = s21 - t21
    loss = float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2))
    grad = 2.0 * np.mean(
        np.real(np.conj(e11)[:, None] * ds11 + np.conj(e21)[:, None] * ds21),
        axis=0,
    )
    return loss, np.asarray(grad, dtype=float)


def generalized_response_error_metrics(
    m: np.ndarray,
    target_m: np.ndarray,
    omega: np.ndarray,
) -> dict[str, float]:
    s11, s21 = generalized_scattering(m, omega)
    t11, t21 = generalized_scattering(target_m, omega)
    e11 = s11 - t11
    e21 = s21 - t21
    d11 = np.abs(s11) - np.abs(t11)
    d21 = np.abs(s21) - np.abs(t21)
    return {
        "mse_complex_response": float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2)),
        "rms_complex_s11_error": float(np.sqrt(np.mean(np.abs(e11) ** 2))),
        "rms_complex_s21_error": float(np.sqrt(np.mean(np.abs(e21) ** 2))),
        "max_complex_s11_error": float(np.max(np.abs(e11))),
        "max_complex_s21_error": float(np.max(np.abs(e21))),
        "max_s11_magnitude_error": float(np.max(np.abs(d11))),
        "max_s21_magnitude_error": float(np.max(np.abs(d21))),
    }
