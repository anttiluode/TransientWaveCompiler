"""Measurement-aware explicit-port coupling-matrix response and gradients.

Adds a uniform resonator loss term and independent linear reference-plane phase
nuisance for S11/S21.  The purpose is computer-side filter tuning from
calibrated-but-imperfect complex measurements, not the TW-1A hardware model.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters


def lossy_scattering_with_derivatives(
    m: np.ndarray,
    omega: np.ndarray,
    parameters: Sequence[MatrixParameter],
    resonator_loss: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return S11/S21 and derivatives wrt matrix knobs and uniform loss.

    Uses

        A = M + Omega U - j(q + lambda U)

    where U selects resonator nodes and q selects source/load ports.
    """
    m = np.asarray(m, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("coupling matrix must be square")
    if not np.allclose(m, m.T, rtol=0.0, atol=1e-12):
        raise ValueError("coupling matrix must be reciprocal/symmetric")
    if resonator_loss < 0:
        raise ValueError("resonator_loss must be nonnegative")

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
    dloss11 = np.empty(len(w), dtype=complex)
    dloss21 = np.empty(len(w), dtype=complex)

    # dA/dlambda = -j U
    d_a_loss = -1j * u
    for k, wi in enumerate(w):
        a = m.astype(complex) + complex(float(wi)) * u - 1j * (q + float(resonator_loss) * u)
        ainv = np.linalg.inv(a)
        s11[k] = 1.0 + 2j * ainv[0, 0]
        s21[k] = -2j * ainv[-1, 0]
        for pidx, stamp in enumerate(stamps):
            dinv = -(ainv @ stamp @ ainv)
            ds11[k, pidx] = 2j * dinv[0, 0]
            ds21[k, pidx] = -2j * dinv[-1, 0]
        dinv_loss = -(ainv @ d_a_loss @ ainv)
        dloss11[k] = 2j * dinv_loss[0, 0]
        dloss21[k] = -2j * dinv_loss[-1, 0]
    return s11, s21, ds11, ds21, dloss11, dloss21


def measurement_aware_response(
    matrix_values: Sequence[float],
    *,
    n: int,
    parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    resonator_loss: float,
    phi11: float,
    tau11: float,
    phi21: float,
    tau21: float,
) -> tuple[np.ndarray, np.ndarray]:
    m = matrix_from_parameters(n, parameters, matrix_values)
    s11, s21, *_ = lossy_scattering_with_derivatives(m, omega, parameters, resonator_loss)
    w = np.asarray(omega, dtype=float).reshape(-1)
    return (
        s11 * np.exp(1j * (float(phi11) + float(tau11) * w)),
        s21 * np.exp(1j * (float(phi21) + float(tau21) * w)),
    )


def measurement_aware_loss_and_gradient(
    x: Sequence[float],
    *,
    n: int,
    parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    measured_s11: np.ndarray,
    measured_s21: np.ndarray,
) -> tuple[float, np.ndarray]:
    """Complex response loss and exact gradient for matrix + nuisance vector.

    Parameter order is

        [matrix values..., lambda, phi11, tau11, phi21, tau21].
    """
    x = np.asarray(x, dtype=float)
    p = len(parameters)
    if x.shape != (p + 5,):
        raise ValueError(f"expected {p + 5} values, got shape {x.shape}")
    matrix_values = x[:p]
    resonator_loss, phi11, tau11, phi21, tau21 = map(float, x[p:])
    m = matrix_from_parameters(n, parameters, matrix_values)
    w = np.asarray(omega, dtype=float).reshape(-1)
    t11 = np.asarray(measured_s11, dtype=complex).reshape(-1)
    t21 = np.asarray(measured_s21, dtype=complex).reshape(-1)
    if t11.shape != w.shape or t21.shape != w.shape:
        raise ValueError("measured S-parameter shape mismatch")

    s11, s21, ds11, ds21, dloss11, dloss21 = lossy_scattering_with_derivatives(
        m, w, parameters, resonator_loss
    )
    phase11 = np.exp(1j * (phi11 + tau11 * w))
    phase21 = np.exp(1j * (phi21 + tau21 * w))
    y11 = s11 * phase11
    y21 = s21 * phase21
    e11 = y11 - t11
    e21 = y21 - t21
    loss = float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2))

    # Derivatives of phase-corrected response wrt physical matrix parameters.
    dy11_matrix = ds11 * phase11[:, None]
    dy21_matrix = ds21 * phase21[:, None]
    grad_matrix = 2.0 * np.mean(
        np.real(np.conj(e11)[:, None] * dy11_matrix + np.conj(e21)[:, None] * dy21_matrix),
        axis=0,
    )

    dy11_loss = dloss11 * phase11
    dy21_loss = dloss21 * phase21
    grad_loss = 2.0 * np.mean(np.real(np.conj(e11) * dy11_loss + np.conj(e21) * dy21_loss))

    dy11_phi = 1j * y11
    dy11_tau = 1j * w * y11
    dy21_phi = 1j * y21
    dy21_tau = 1j * w * y21
    grad_phi11 = 2.0 * np.mean(np.real(np.conj(e11) * dy11_phi))
    grad_tau11 = 2.0 * np.mean(np.real(np.conj(e11) * dy11_tau))
    grad_phi21 = 2.0 * np.mean(np.real(np.conj(e21) * dy21_phi))
    grad_tau21 = 2.0 * np.mean(np.real(np.conj(e21) * dy21_tau))

    grad = np.concatenate(
        [
            np.asarray(grad_matrix, dtype=float),
            np.asarray([grad_loss, grad_phi11, grad_tau11, grad_phi21, grad_tau21], dtype=float),
        ]
    )
    return loss, grad


def wrap_phase_error(value: float, target: float) -> float:
    """Signed wrapped phase error in radians, in [-pi, pi)."""
    return float((float(value) - float(target) + np.pi) % (2.0 * np.pi) - np.pi)
