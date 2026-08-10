"""First-order identifiability diagnostics for reciprocal filter models.

The topology benchmarks exposed a distinction between *sensitivity* and
*identifiability*.  A missing reciprocal edge can have a large response
sensitivity while still being locally invisible because the fitted model's
existing physical and nuisance columns span almost the same response direction.

For a realified complex-response Jacobian ``J`` and candidate response
derivative ``g`` this module reports

    eta = ||(I - P_J) g|| / ||g||,

where ``P_J`` is the orthogonal projector onto the numerical column space of
``J``.  ``eta ~= 0`` means the candidate is locally aliased by the current
model; ``eta ~= 1`` means its first-order response is almost wholly novel.

The metric is deliberately diagnostic rather than a proof of global
identifiability.  Bounds, nonlinear compensation, finite noise, and remote
alternative minima can still matter.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from .multistate_filter import FilterMeasurementState


@dataclass(frozen=True)
class IdentifiabilityScore:
    i: int
    j: int
    name: str
    novelty_fraction: float
    projected_fraction: float
    projected_energy_fraction: float
    candidate_norm: float
    residual_norm: float
    jacobian_rank: int
    jacobian_columns: int
    jacobian_condition: float | None
    state_shape_max_line_angle_deg: float | None
    state_shape_median_line_angle_deg: float | None
    channels: tuple[str, ...]
    nuisance_per_state: int

    def as_dict(self) -> dict[str, object]:
        return {
            "i": int(self.i),
            "j": int(self.j),
            "name": self.name,
            "novelty_fraction": float(self.novelty_fraction),
            "projected_fraction": float(self.projected_fraction),
            "projected_energy_fraction": float(self.projected_energy_fraction),
            "candidate_norm": float(self.candidate_norm),
            "residual_norm": float(self.residual_norm),
            "jacobian_rank": int(self.jacobian_rank),
            "jacobian_columns": int(self.jacobian_columns),
            "jacobian_condition": None if self.jacobian_condition is None else float(self.jacobian_condition),
            "state_shape_max_line_angle_deg": (
                None if self.state_shape_max_line_angle_deg is None
                else float(self.state_shape_max_line_angle_deg)
            ),
            "state_shape_median_line_angle_deg": (
                None if self.state_shape_median_line_angle_deg is None
                else float(self.state_shape_median_line_angle_deg)
            ),
            "channels": list(self.channels),
            "nuisance_per_state": int(self.nuisance_per_state),
        }


def _validate_channels(channels: Sequence[str]) -> tuple[str, ...]:
    out = tuple(str(ch).lower() for ch in channels)
    if not out:
        raise ValueError("at least one response channel is required")
    allowed = {"s11", "s21", "s22"}
    if len(set(out)) != len(out) or any(ch not in allowed for ch in out):
        raise ValueError("channels must be a unique subset of s11, s21, s22")
    return out


def _explicit_port_lossy_channels_with_derivatives(
    m: np.ndarray,
    omega: np.ndarray,
    parameters: Sequence[MatrixParameter],
    resonator_loss: float,
    channels: Sequence[str],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return physical S channels, matrix derivatives, and loss derivatives.

    This is the same explicit-port model used by ``measurement_aware_filter``
    but includes S22 for identifiability experiments without changing the
    production fitter's public return signature.
    """
    channels = _validate_channels(channels)
    m = np.asarray(m, dtype=float)
    if m.ndim != 2 or m.shape[0] != m.shape[1] or m.shape[0] < 3:
        raise ValueError("coupling matrix must be square with >=3 nodes")
    if not np.allclose(m, m.T, rtol=0.0, atol=1e-12):
        raise ValueError("coupling matrix must be reciprocal/symmetric")
    if not np.isfinite(resonator_loss) or resonator_loss < 0.0:
        raise ValueError("resonator_loss must be finite and nonnegative")

    n = m.shape[0]
    w = np.asarray(omega, dtype=float).reshape(-1)
    if len(w) == 0 or not np.all(np.isfinite(w)):
        raise ValueError("omega must contain finite samples")

    u = np.eye(n, dtype=complex)
    u[0, 0] = 0.0
    u[-1, -1] = 0.0
    q = np.zeros((n, n), dtype=complex)
    q[0, 0] = 1.0
    q[-1, -1] = 1.0
    stamps = [parameter.stamp(n).astype(complex) for parameter in parameters]
    d_a_loss = -1j * u

    response = {ch: np.empty(len(w), dtype=complex) for ch in channels}
    deriv = {ch: np.empty((len(w), len(parameters)), dtype=complex) for ch in channels}
    dloss = {ch: np.empty(len(w), dtype=complex) for ch in channels}

    for k, wi in enumerate(w):
        a = m.astype(complex) + complex(float(wi)) * u - 1j * (q + float(resonator_loss) * u)
        ainv = np.linalg.inv(a)

        if "s11" in response:
            response["s11"][k] = 1.0 + 2j * ainv[0, 0]
        if "s21" in response:
            response["s21"][k] = -2j * ainv[-1, 0]
        if "s22" in response:
            response["s22"][k] = 1.0 + 2j * ainv[-1, -1]

        for pidx, stamp in enumerate(stamps):
            dinv = -(ainv @ stamp @ ainv)
            if "s11" in deriv:
                deriv["s11"][k, pidx] = 2j * dinv[0, 0]
            if "s21" in deriv:
                deriv["s21"][k, pidx] = -2j * dinv[-1, 0]
            if "s22" in deriv:
                deriv["s22"][k, pidx] = 2j * dinv[-1, -1]

        dinv_loss = -(ainv @ d_a_loss @ ainv)
        if "s11" in dloss:
            dloss["s11"][k] = 2j * dinv_loss[0, 0]
        if "s21" in dloss:
            dloss["s21"][k] = -2j * dinv_loss[-1, 0]
        if "s22" in dloss:
            dloss["s22"][k] = 2j * dinv_loss[-1, -1]

    return response, deriv, dloss


def _realify_matrix(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=complex)
    if value.ndim != 2:
        raise ValueError("complex Jacobian must be two-dimensional")
    return np.concatenate([np.real(value), np.imag(value)], axis=0)


def _realify_vector(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=complex).reshape(-1)
    return np.concatenate([np.real(value), np.imag(value)])


def orthogonal_novelty_fraction(
    jacobian: np.ndarray,
    candidate: np.ndarray,
    *,
    rcond: float = 1e-10,
) -> dict[str, float | int | None]:
    """Project ``candidate`` away from the numerical column space of ``J``."""
    j = np.asarray(jacobian, dtype=float)
    g = np.asarray(candidate, dtype=float).reshape(-1)
    if j.ndim != 2 or j.shape[0] != g.shape[0]:
        raise ValueError("jacobian rows must match candidate length")
    if not np.all(np.isfinite(j)) or not np.all(np.isfinite(g)):
        raise ValueError("jacobian/candidate must be finite")
    if not np.isfinite(rcond) or rcond <= 0.0:
        raise ValueError("rcond must be finite and positive")

    gnorm = float(np.linalg.norm(g))
    if gnorm <= 1e-300:
        return {
            "novelty_fraction": 0.0,
            "projected_fraction": 0.0,
            "projected_energy_fraction": 0.0,
            "candidate_norm": gnorm,
            "residual_norm": 0.0,
            "jacobian_rank": 0,
            "jacobian_columns": int(j.shape[1]),
            "jacobian_condition": None,
        }

    if j.shape[1] == 0:
        residual_norm = gnorm
        return {
            "novelty_fraction": 1.0,
            "projected_fraction": 0.0,
            "projected_energy_fraction": 0.0,
            "candidate_norm": gnorm,
            "residual_norm": residual_norm,
            "jacobian_rank": 0,
            "jacobian_columns": 0,
            "jacobian_condition": None,
        }

    u, singular, _vh = np.linalg.svd(j, full_matrices=False)
    if len(singular) == 0 or singular[0] <= 0.0:
        rank = 0
    else:
        rank = int(np.sum(singular > float(rcond) * singular[0]))
    if rank:
        basis = u[:, :rank]
        projected = basis @ (basis.T @ g)
        condition = float(singular[0] / singular[rank - 1])
    else:
        projected = np.zeros_like(g)
        condition = None
    residual = g - projected
    residual_norm = float(np.linalg.norm(residual))
    projected_norm = float(np.linalg.norm(projected))
    novelty = float(np.clip(residual_norm / gnorm, 0.0, 1.0))
    projected_fraction = float(np.clip(projected_norm / gnorm, 0.0, 1.0))
    return {
        "novelty_fraction": novelty,
        "projected_fraction": projected_fraction,
        "projected_energy_fraction": float(np.clip(projected_fraction**2, 0.0, 1.0)),
        "candidate_norm": gnorm,
        "residual_norm": residual_norm,
        "jacobian_rank": rank,
        "jacobian_columns": int(j.shape[1]),
        "jacobian_condition": condition,
    }


def _state_line_angles(vectors: Sequence[np.ndarray]) -> tuple[float | None, float | None]:
    if len(vectors) < 2:
        return None, None
    normalized: list[np.ndarray] = []
    for vector in vectors:
        v = _realify_vector(vector)
        norm = float(np.linalg.norm(v))
        if norm > 1e-300:
            normalized.append(v / norm)
    if len(normalized) < 2:
        return None, None
    angles = []
    for a, b in combinations(normalized, 2):
        # A line rather than an oriented vector: pure +/- rescaling is zero
        # shape change and therefore receives zero principal angle.
        cosine = float(np.clip(abs(np.dot(a, b)), 0.0, 1.0))
        angles.append(float(np.degrees(np.arccos(cosine))))
    return float(max(angles)), float(np.median(angles))


def multistate_candidate_identifiability(
    shared_values: Sequence[float],
    *,
    n: int,
    shared_parameters: Sequence[MatrixParameter],
    candidate: MatrixParameter,
    omega: np.ndarray,
    states: Sequence[FilterMeasurementState],
    nuisance_blocks: Sequence[Sequence[float]],
    channels: Sequence[str] = ("s11", "s21"),
    include_s22_phase_nuisance: bool = True,
    rcond: float = 1e-10,
) -> IdentifiabilityScore:
    """Measure first-order novelty of one absent edge across known states.

    The global Jacobian contains shared physical columns plus block-diagonal
    state-specific nuisance columns.  With S11/S21 the nuisance block is the
    existing five variables ``[loss, phi11, tau11, phi21, tau21]``.  If S22 is
    included, two additional *state-specific* phase columns are included by
    default so S22 is not given an unfair perfectly calibrated reference plane.

    ``nuisance_blocks`` always supplies the existing five fitted values per
    state.  S22 phase offset/slope are evaluated at zero; for this isotropic
    first-order projection their unknown base phase is only a rotation of the
    S22 channel, while their two tangent columns are explicitly included.
    """
    channels = _validate_channels(channels)
    if not states:
        raise ValueError("at least one measurement state is required")
    if len(states) != len(nuisance_blocks):
        raise ValueError("one nuisance block is required per state")
    if int(candidate.i) == int(candidate.j):
        raise ValueError("candidate must be an off-diagonal reciprocal edge")

    shared = np.asarray(shared_values, dtype=float)
    if shared.shape != (len(shared_parameters),):
        raise ValueError("shared_values shape mismatch")
    w = np.asarray(omega, dtype=float).reshape(-1)
    for state in states:
        state.validate(w)

    key = tuple(sorted((int(candidate.i), int(candidate.j))))
    occupied = {
        tuple(sorted((int(parameter.i), int(parameter.j))))
        for parameter in shared_parameters
    }
    if key in occupied:
        raise ValueError(f"candidate edge {key} is already declared")

    s22_extra = 2 if ("s22" in channels and include_s22_phase_nuisance) else 0
    nuisance_per_state = 5 + s22_extra
    complex_rows_per_state = len(w) * len(channels)
    total_complex_rows = complex_rows_per_state * len(states)
    total_columns = len(shared_parameters) + nuisance_per_state * len(states)
    global_j = np.zeros((total_complex_rows, total_columns), dtype=complex)
    global_g = np.zeros(total_complex_rows, dtype=complex)
    state_candidate_vectors: list[np.ndarray] = []

    all_derivative_parameters = [*shared_parameters, candidate]
    for state_index, (state, nuisance_raw) in enumerate(zip(states, nuisance_blocks)):
        nuisance = np.asarray(nuisance_raw, dtype=float)
        if nuisance.shape != (5,):
            raise ValueError("each nuisance block must contain five values")
        local_parameters = [*shared_parameters, *state.fixed_parameters]
        local_values = np.concatenate([shared, np.asarray(state.fixed_values, dtype=float)])
        local_matrix = matrix_from_parameters(n, local_parameters, local_values)
        response, deriv, dloss = _explicit_port_lossy_channels_with_derivatives(
            local_matrix,
            w,
            all_derivative_parameters,
            float(nuisance[0]),
            channels,
        )

        phase = {
            "s11": np.exp(1j * (float(nuisance[1]) + float(nuisance[2]) * w)),
            "s21": np.exp(1j * (float(nuisance[3]) + float(nuisance[4]) * w)),
            "s22": np.ones(len(w), dtype=complex),
        }
        shared_parts = []
        candidate_parts = []
        loss_parts = []
        y: dict[str, np.ndarray] = {}
        for ch in channels:
            y[ch] = response[ch] * phase[ch]
            shared_parts.append(deriv[ch][:, : len(shared_parameters)] * phase[ch][:, None])
            candidate_parts.append(deriv[ch][:, -1] * phase[ch])
            loss_parts.append(dloss[ch] * phase[ch])

        state_shared = np.concatenate(shared_parts, axis=0)
        state_candidate = np.concatenate(candidate_parts)
        state_loss = np.concatenate(loss_parts)
        state_candidate_vectors.append(state_candidate)
        row0 = state_index * complex_rows_per_state
        row1 = row0 + complex_rows_per_state
        global_j[row0:row1, : len(shared_parameters)] = state_shared
        global_g[row0:row1] = state_candidate

        local = np.zeros((complex_rows_per_state, nuisance_per_state), dtype=complex)
        local[:, 0] = state_loss
        channel_offset = 0
        for ch in channels:
            sl = slice(channel_offset, channel_offset + len(w))
            if ch == "s11":
                local[sl, 1] = 1j * y[ch]
                local[sl, 2] = 1j * w * y[ch]
            elif ch == "s21":
                local[sl, 3] = 1j * y[ch]
                local[sl, 4] = 1j * w * y[ch]
            elif ch == "s22" and include_s22_phase_nuisance:
                local[sl, 5] = 1j * y[ch]
                local[sl, 6] = 1j * w * y[ch]
            channel_offset += len(w)

        col0 = len(shared_parameters) + nuisance_per_state * state_index
        col1 = col0 + nuisance_per_state
        global_j[row0:row1, col0:col1] = local

    metric = orthogonal_novelty_fraction(
        _realify_matrix(global_j),
        _realify_vector(global_g),
        rcond=rcond,
    )
    max_angle, median_angle = _state_line_angles(state_candidate_vectors)
    return IdentifiabilityScore(
        i=key[0],
        j=key[1],
        name=candidate.name or f"m{key[0]}{key[1]}",
        novelty_fraction=float(metric["novelty_fraction"]),
        projected_fraction=float(metric["projected_fraction"]),
        projected_energy_fraction=float(metric["projected_energy_fraction"]),
        candidate_norm=float(metric["candidate_norm"]),
        residual_norm=float(metric["residual_norm"]),
        jacobian_rank=int(metric["jacobian_rank"]),
        jacobian_columns=int(metric["jacobian_columns"]),
        jacobian_condition=(
            None if metric["jacobian_condition"] is None
            else float(metric["jacobian_condition"])
        ),
        state_shape_max_line_angle_deg=max_angle,
        state_shape_median_line_angle_deg=median_angle,
        channels=channels,
        nuisance_per_state=nuisance_per_state,
    )
