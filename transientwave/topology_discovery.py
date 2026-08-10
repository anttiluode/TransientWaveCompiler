"""Residual-driven discovery of missing reciprocal coupling-matrix edges.

This module does not try to infer an arbitrary graph from scratch. It starts
from an already fitted declared topology and asks a narrower diagnostic
question:

    which currently absent symmetric matrix stamp best explains the remaining
    complex S-parameter residual?

For each absent off-diagonal edge it uses the exact response derivative at
zero edge strength, takes a Gauss-Newton one-dimensional probe step, evaluates
that probe exactly, and ranks candidates by achieved loss reduction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from .measurement_aware_filter import (
    lossy_scattering_with_derivatives,
    measurement_aware_response,
)


@dataclass(frozen=True)
class MissingEdgeScore:
    i: int
    j: int
    name: str
    gradient_at_zero: float
    gauss_newton_curvature: float
    proposed_value: float
    baseline_loss: float
    probe_loss: float
    loss_reduction: float
    relative_loss_reduction: float

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "i": int(self.i),
            "j": int(self.j),
            "name": self.name,
            "gradient_at_zero": float(self.gradient_at_zero),
            "gauss_newton_curvature": float(self.gauss_newton_curvature),
            "proposed_value": float(self.proposed_value),
            "baseline_loss": float(self.baseline_loss),
            "probe_loss": float(self.probe_loss),
            "loss_reduction": float(self.loss_reduction),
            "relative_loss_reduction": float(self.relative_loss_reduction),
        }


def absent_reciprocal_edges(
    n: int,
    parameters: Sequence[MatrixParameter],
) -> list[MatrixParameter]:
    """Enumerate absent off-diagonal reciprocal matrix entries."""
    if n < 2:
        raise ValueError("n must be at least 2")
    occupied = {
        tuple(sorted((int(parameter.i), int(parameter.j))))
        for parameter in parameters
        if int(parameter.i) != int(parameter.j)
    }
    return [
        MatrixParameter(i, j, f"m{i}{j}")
        for i in range(n)
        for j in range(i + 1, n)
        if (i, j) not in occupied
    ]


def _complex_loss(
    predicted_s11: np.ndarray,
    predicted_s21: np.ndarray,
    measured_s11: np.ndarray,
    measured_s21: np.ndarray,
) -> float:
    e11 = np.asarray(predicted_s11, dtype=complex) - np.asarray(measured_s11, dtype=complex)
    e21 = np.asarray(predicted_s21, dtype=complex) - np.asarray(measured_s21, dtype=complex)
    return float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2))


def score_missing_reciprocal_edges(
    matrix_values: Sequence[float],
    *,
    n: int,
    parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    measured_s11: np.ndarray,
    measured_s21: np.ndarray,
    resonator_loss: float = 0.0,
    phi11: float = 0.0,
    tau11: float = 0.0,
    phi21: float = 0.0,
    tau21: float = 0.0,
    max_abs_probe: float = 0.15,
    candidates: Iterable[MatrixParameter] | None = None,
) -> list[MissingEdgeScore]:
    """Rank absent reciprocal edges by exact one-step residual reduction.

    The base physical and nuisance values are held fixed during scoring. For
    each candidate edge ``c`` at value zero, the exact complex response
    derivative ``dy/dc`` gives a scalar residual gradient. A Gauss-Newton
    curvature approximation proposes

        c_probe = clip(-g / h, -max_abs_probe, +max_abs_probe).

    The response at ``c_probe`` is then evaluated exactly. Ranking therefore
    uses actual probe loss rather than only derivative magnitude.
    """
    values = np.asarray(matrix_values, dtype=float)
    if values.shape != (len(parameters),):
        raise ValueError("matrix_values must contain one value per declared parameter")
    if not np.isfinite(max_abs_probe) or max_abs_probe <= 0:
        raise ValueError("max_abs_probe must be finite and positive")

    w = np.asarray(omega, dtype=float).reshape(-1)
    t11 = np.asarray(measured_s11, dtype=complex).reshape(-1)
    t21 = np.asarray(measured_s21, dtype=complex).reshape(-1)
    if t11.shape != w.shape or t21.shape != w.shape:
        raise ValueError("measured S-parameter shape mismatch")

    base11, base21 = measurement_aware_response(
        values,
        n=n,
        parameters=parameters,
        omega=w,
        resonator_loss=float(resonator_loss),
        phi11=float(phi11),
        tau11=float(tau11),
        phi21=float(phi21),
        tau21=float(tau21),
    )
    e11 = base11 - t11
    e21 = base21 - t21
    baseline_loss = _complex_loss(base11, base21, t11, t21)
    phase11 = np.exp(1j * (float(phi11) + float(tau11) * w))
    phase21 = np.exp(1j * (float(phi21) + float(tau21) * w))
    base_matrix = matrix_from_parameters(n, parameters, values)

    candidate_list = list(candidates) if candidates is not None else absent_reciprocal_edges(n, parameters)
    occupied = {
        tuple(sorted((int(parameter.i), int(parameter.j))))
        for parameter in parameters
    }
    scores: list[MissingEdgeScore] = []

    for candidate in candidate_list:
        i, j = int(candidate.i), int(candidate.j)
        if i == j:
            raise ValueError("missing-edge discovery currently scores off-diagonal reciprocal edges only")
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError("candidate edge endpoint out of range")
        key = tuple(sorted((i, j)))
        if key in occupied:
            raise ValueError(f"candidate edge {key} is already declared")

        _s11, _s21, ds11, ds21, _dloss11, _dloss21 = lossy_scattering_with_derivatives(
            base_matrix,
            w,
            [candidate],
            float(resonator_loss),
        )
        dy11 = ds11[:, 0] * phase11
        dy21 = ds21[:, 0] * phase21
        gradient = 2.0 * float(
            np.mean(np.real(np.conj(e11) * dy11 + np.conj(e21) * dy21))
        )
        curvature = 2.0 * float(np.mean(np.abs(dy11) ** 2 + np.abs(dy21) ** 2))
        if not np.isfinite(curvature) or curvature <= 1e-18:
            proposed = 0.0
        else:
            proposed = float(np.clip(-gradient / curvature, -max_abs_probe, max_abs_probe))

        augmented_parameters = [*parameters, candidate]
        augmented_values = np.concatenate([values, np.asarray([proposed], dtype=float)])
        probe11, probe21 = measurement_aware_response(
            augmented_values,
            n=n,
            parameters=augmented_parameters,
            omega=w,
            resonator_loss=float(resonator_loss),
            phi11=float(phi11),
            tau11=float(tau11),
            phi21=float(phi21),
            tau21=float(tau21),
        )
        probe_loss = _complex_loss(probe11, probe21, t11, t21)
        reduction = float(baseline_loss - probe_loss)
        relative = float(reduction / max(baseline_loss, 1e-300))
        scores.append(
            MissingEdgeScore(
                i=key[0],
                j=key[1],
                name=candidate.name or f"m{key[0]}{key[1]}",
                gradient_at_zero=gradient,
                gauss_newton_curvature=curvature,
                proposed_value=proposed,
                baseline_loss=baseline_loss,
                probe_loss=probe_loss,
                loss_reduction=reduction,
                relative_loss_reduction=relative,
            )
        )

    scores.sort(key=lambda item: (item.probe_loss, -abs(item.proposed_value), item.i, item.j))
    return scores
