"""Joint fitting and missing-edge diagnostics across known filter perturbation states.

A single static S-parameter response can admit compensated wrong coupling
matrices. This module adds a controlled source of information without changing
the hidden base topology: measure the same reciprocal device in several states
whose additional matrix stamps are known.

The shared physical matrix is common to every state. Each state may add known
fixed matrix entries (for example one deliberately detuned resonator) and has
its own five measurement/model nuisance variables.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from .measurement_aware_filter import (
    lossy_scattering_with_derivatives,
    measurement_aware_loss_and_gradient,
    measurement_aware_response,
)
from .topology_discovery import MissingEdgeScore, absent_reciprocal_edges


@dataclass(frozen=True)
class FilterMeasurementState:
    name: str
    fixed_parameters: tuple[MatrixParameter, ...]
    fixed_values: np.ndarray
    measured_s11: np.ndarray
    measured_s21: np.ndarray

    def validate(self, omega: np.ndarray) -> None:
        values = np.asarray(self.fixed_values, dtype=float)
        if values.shape != (len(self.fixed_parameters),):
            raise ValueError(f"state {self.name}: fixed_values shape mismatch")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"state {self.name}: fixed values must be finite")
        expected = np.asarray(omega).reshape(-1).shape
        if np.asarray(self.measured_s11).reshape(-1).shape != expected:
            raise ValueError(f"state {self.name}: measured_s11 shape mismatch")
        if np.asarray(self.measured_s21).reshape(-1).shape != expected:
            raise ValueError(f"state {self.name}: measured_s21 shape mismatch")


def _split_global_values(
    values: Sequence[float],
    *,
    shared_parameter_count: int,
    state_count: int,
) -> tuple[np.ndarray, list[np.ndarray]]:
    x = np.asarray(values, dtype=float)
    expected = int(shared_parameter_count) + 5 * int(state_count)
    if x.shape != (expected,):
        raise ValueError(f"expected {expected} global values, got shape {x.shape}")
    shared = x[:shared_parameter_count]
    nuisance = [
        x[shared_parameter_count + 5 * s : shared_parameter_count + 5 * (s + 1)]
        for s in range(state_count)
    ]
    return shared, nuisance


def multistate_loss_and_gradient(
    values: Sequence[float],
    *,
    n: int,
    shared_parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    states: Sequence[FilterMeasurementState],
) -> tuple[float, np.ndarray]:
    """Mean complex-response loss over states with exact global gradient.

    Global order is

    ``[shared matrix values..., state0 nuisance5..., state1 nuisance5..., ...]``.

    Known per-state matrix stamps are inserted into each local model and are
    not optimized. The returned gradient therefore contains only shared
    physical parameters and each state's nuisance variables.
    """
    if not states:
        raise ValueError("at least one measurement state is required")
    w = np.asarray(omega, dtype=float).reshape(-1)
    for state in states:
        state.validate(w)

    shared, nuisance_blocks = _split_global_values(
        values,
        shared_parameter_count=len(shared_parameters),
        state_count=len(states),
    )
    grad = np.zeros(len(shared_parameters) + 5 * len(states), dtype=float)
    total_loss = 0.0

    for s, (state, nuisance) in enumerate(zip(states, nuisance_blocks)):
        local_parameters = [*shared_parameters, *state.fixed_parameters]
        local_matrix_values = np.concatenate([shared, np.asarray(state.fixed_values, dtype=float)])
        local_values = np.concatenate([local_matrix_values, nuisance])
        loss, local_grad = measurement_aware_loss_and_gradient(
            local_values,
            n=n,
            parameters=local_parameters,
            omega=w,
            measured_s11=np.asarray(state.measured_s11, dtype=complex),
            measured_s21=np.asarray(state.measured_s21, dtype=complex),
        )
        total_loss += float(loss)
        grad[: len(shared_parameters)] += local_grad[: len(shared_parameters)]
        local_nuisance_start = len(local_parameters)
        global_nuisance_start = len(shared_parameters) + 5 * s
        grad[global_nuisance_start : global_nuisance_start + 5] = local_grad[
            local_nuisance_start : local_nuisance_start + 5
        ]

    scale = 1.0 / float(len(states))
    grad[: len(shared_parameters)] *= scale
    for s in range(len(states)):
        start = len(shared_parameters) + 5 * s
        grad[start : start + 5] *= scale
    return float(total_loss * scale), grad


def multistate_responses(
    shared_values: Sequence[float],
    *,
    n: int,
    shared_parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    states: Sequence[FilterMeasurementState],
    nuisance_blocks: Sequence[Sequence[float]],
) -> list[tuple[np.ndarray, np.ndarray]]:
    if len(states) != len(nuisance_blocks):
        raise ValueError("one nuisance block is required per state")
    shared = np.asarray(shared_values, dtype=float)
    if shared.shape != (len(shared_parameters),):
        raise ValueError("shared_values shape mismatch")
    out = []
    for state, nuisance in zip(states, nuisance_blocks):
        state.validate(np.asarray(omega).reshape(-1))
        nuisance = np.asarray(nuisance, dtype=float)
        if nuisance.shape != (5,):
            raise ValueError("each nuisance block must contain five values")
        local_parameters = [*shared_parameters, *state.fixed_parameters]
        local_values = np.concatenate([shared, np.asarray(state.fixed_values, dtype=float)])
        out.append(
            measurement_aware_response(
                local_values,
                n=n,
                parameters=local_parameters,
                omega=omega,
                resonator_loss=float(nuisance[0]),
                phi11=float(nuisance[1]),
                tau11=float(nuisance[2]),
                phi21=float(nuisance[3]),
                tau21=float(nuisance[4]),
            )
        )
    return out


def _complex_loss(pred11, pred21, measured11, measured21) -> float:
    e11 = np.asarray(pred11, dtype=complex) - np.asarray(measured11, dtype=complex)
    e21 = np.asarray(pred21, dtype=complex) - np.asarray(measured21, dtype=complex)
    return float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2))


def score_missing_reciprocal_edges_multistate(
    shared_values: Sequence[float],
    *,
    n: int,
    shared_parameters: Sequence[MatrixParameter],
    omega: np.ndarray,
    states: Sequence[FilterMeasurementState],
    nuisance_blocks: Sequence[Sequence[float]],
    max_abs_probe: float = 0.15,
    candidates: Iterable[MatrixParameter] | None = None,
) -> list[MissingEdgeScore]:
    """Rank absent edges from the joint residual of several known states.

    The shared wrong-topology solution and each state's fitted nuisance are
    held fixed. One candidate edge is shared across every state. Its gradient
    and Gauss-Newton curvature are accumulated over all states, a single
    bounded probe value is proposed, and ranking uses the actual mean probe
    loss across the complete state ensemble.
    """
    if not states:
        raise ValueError("at least one state is required")
    if len(states) != len(nuisance_blocks):
        raise ValueError("one nuisance block is required per state")
    if not np.isfinite(max_abs_probe) or max_abs_probe <= 0.0:
        raise ValueError("max_abs_probe must be finite and positive")

    w = np.asarray(omega, dtype=float).reshape(-1)
    shared = np.asarray(shared_values, dtype=float)
    if shared.shape != (len(shared_parameters),):
        raise ValueError("shared_values shape mismatch")
    for state in states:
        state.validate(w)

    candidate_list = (
        list(candidates)
        if candidates is not None
        else absent_reciprocal_edges(n, shared_parameters)
    )
    occupied = {
        tuple(sorted((int(parameter.i), int(parameter.j))))
        for parameter in shared_parameters
    }

    base_responses = multistate_responses(
        shared,
        n=n,
        shared_parameters=shared_parameters,
        omega=w,
        states=states,
        nuisance_blocks=nuisance_blocks,
    )
    baseline_losses = [
        _complex_loss(p11, p21, state.measured_s11, state.measured_s21)
        for (p11, p21), state in zip(base_responses, states)
    ]
    baseline_loss = float(np.mean(baseline_losses))
    scores: list[MissingEdgeScore] = []

    for candidate in candidate_list:
        i, j = int(candidate.i), int(candidate.j)
        if i == j:
            raise ValueError("missing-edge scoring supports off-diagonal edges only")
        key = tuple(sorted((i, j)))
        if key in occupied:
            raise ValueError(f"candidate edge {key} is already declared")

        gradients = []
        curvatures = []
        for state, nuisance, (base11, base21) in zip(states, nuisance_blocks, base_responses):
            nuisance = np.asarray(nuisance, dtype=float)
            if nuisance.shape != (5,):
                raise ValueError("each nuisance block must contain five values")
            local_parameters = [*shared_parameters, *state.fixed_parameters]
            local_values = np.concatenate([shared, np.asarray(state.fixed_values, dtype=float)])
            base_matrix = matrix_from_parameters(n, local_parameters, local_values)
            _s11, _s21, ds11, ds21, _dl11, _dl21 = lossy_scattering_with_derivatives(
                base_matrix,
                w,
                [candidate],
                float(nuisance[0]),
            )
            phase11 = np.exp(1j * (float(nuisance[1]) + float(nuisance[2]) * w))
            phase21 = np.exp(1j * (float(nuisance[3]) + float(nuisance[4]) * w))
            dy11 = ds11[:, 0] * phase11
            dy21 = ds21[:, 0] * phase21
            e11 = base11 - np.asarray(state.measured_s11, dtype=complex)
            e21 = base21 - np.asarray(state.measured_s21, dtype=complex)
            gradients.append(
                2.0 * float(np.mean(np.real(np.conj(e11) * dy11 + np.conj(e21) * dy21)))
            )
            curvatures.append(
                2.0 * float(np.mean(np.abs(dy11) ** 2 + np.abs(dy21) ** 2))
            )

        gradient = float(np.mean(gradients))
        curvature = float(np.mean(curvatures))
        proposed = 0.0 if curvature <= 1e-18 else float(
            np.clip(-gradient / curvature, -max_abs_probe, max_abs_probe)
        )

        probe_losses = []
        augmented = [*shared_parameters, candidate]
        augmented_values = np.concatenate([shared, np.asarray([proposed], dtype=float)])
        for state, nuisance in zip(states, nuisance_blocks):
            local_parameters = [*augmented, *state.fixed_parameters]
            local_values = np.concatenate([augmented_values, np.asarray(state.fixed_values, dtype=float)])
            nuisance = np.asarray(nuisance, dtype=float)
            p11, p21 = measurement_aware_response(
                local_values,
                n=n,
                parameters=local_parameters,
                omega=w,
                resonator_loss=float(nuisance[0]),
                phi11=float(nuisance[1]),
                tau11=float(nuisance[2]),
                phi21=float(nuisance[3]),
                tau21=float(nuisance[4]),
            )
            probe_losses.append(_complex_loss(p11, p21, state.measured_s11, state.measured_s21))
        probe_loss = float(np.mean(probe_losses))
        reduction = float(baseline_loss - probe_loss)
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
                relative_loss_reduction=float(reduction / max(baseline_loss, 1e-300)),
            )
        )

    scores.sort(key=lambda item: (item.probe_loss, -abs(item.proposed_value), item.i, item.j))
    return scores
