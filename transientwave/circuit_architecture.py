"""Process-independent TW-1A v0.2 circuit architecture contract.

This module translates the logical symmetric recurrence

    z[n+1] = Q z[n] - z[n-1] + u[n]

into circuit resources that preserve the compiler's rank-one reciprocal edge
semantics. It intentionally stops above transistor sizing: the goal is to make
cell topology, coefficient sharing, state storage, timing and coherence rules
machine-readable before SPICE/layout work begins.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

import numpy as np


Array = np.ndarray


def grid_edges(rows: int = 8, cols: int = 8) -> list[tuple[int, int]]:
    """Return four-neighbor physical edges for a row-major rectangular tile."""
    out: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if c + 1 < cols:
                out.append((i, i + 1))
            if r + 1 < rows:
                out.append((i, i + cols))
    return out


def signed_midtread_positive_codes(bits: int) -> int:
    """Positive code count K for exact-zero signed codes -K..K."""
    bits = int(bits)
    if bits < 2:
        raise ValueError("bits must be >=2")
    return (1 << (bits - 1)) - 1


def bits_for_absolute_lsb(full_scale: float, target_lsb: float) -> int:
    """Minimum signed mid-tread bits whose positive-side LSB <= target_lsb."""
    fs = float(abs(full_scale))
    lsb = float(abs(target_lsb))
    if not math.isfinite(fs) or fs <= 0:
        raise ValueError("full_scale must be finite and positive")
    if not math.isfinite(lsb) or lsb <= 0:
        raise ValueError("target_lsb must be finite and positive")
    required_k = int(math.ceil(fs / lsb))
    return 1 + int(math.ceil(math.log2(required_k + 1)))


def max_grid_degree(rows: int = 8, cols: int = 8) -> int:
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")
    if rows == 1 and cols == 1:
        return 0
    if rows == 1 or cols == 1:
        return 2 if max(rows, cols) > 2 else 1
    return 4


def required_self_path_full_scale(
    *,
    q_diag_full_scale: float = 1.95,
    q_edge_full_scale: float = 0.25,
    degree: int = 4,
) -> float:
    """Worst-case self coefficient after rank-one edge decomposition.

    With Q = diag(d) + sum_e a_e b_e b_e^T, b_e=e_i-e_j and
    a_e=-Q_ij, the residual self term is d_i=Q_ii-sum(a_e). Thus a
    degree-k backend allowing |Q_ii|<=D and |Q_ij|<=E needs |d_i|<=D+kE.
    """
    d = float(abs(q_diag_full_scale))
    e = float(abs(q_edge_full_scale))
    degree = int(degree)
    if degree < 0:
        raise ValueError("degree must be nonnegative")
    return d + degree * e


def self_bits_matching_edge_lsb(
    *,
    edge_bits: int = 8,
    edge_full_scale: float = 0.25,
    self_full_scale: float = 2.95,
) -> int:
    """Bits required so the self-MDAC LSB is no coarser than the edge LSB."""
    edge_k = signed_midtread_positive_codes(edge_bits)
    edge_lsb = float(abs(edge_full_scale)) / edge_k
    return bits_for_absolute_lsb(self_full_scale, edge_lsb)


def decompose_local_symmetric_q(
    Q: Array,
    *,
    edges: Iterable[tuple[int, int]],
    tol: float = 1e-12,
) -> tuple[Array, dict[tuple[int, int], float]]:
    """Decompose local symmetric Q into node self terms and rank-one edges."""
    q = np.asarray(Q, dtype=float)
    if q.ndim != 2 or q.shape[0] != q.shape[1]:
        raise ValueError("Q must be square")
    if not np.allclose(q, q.T, atol=tol, rtol=0.0):
        raise ValueError("Q must be symmetric")

    n = q.shape[0]
    edge_set = {tuple(sorted((int(i), int(j)))) for i, j in edges}
    for i in range(n):
        for j in range(i + 1, n):
            if abs(float(q[i, j])) > tol and (i, j) not in edge_set:
                raise ValueError(f"nonlocal coupling ({i},{j}) cannot map to physical edge cell")

    self_terms = np.diag(q).copy()
    coeffs: dict[tuple[int, int], float] = {}
    for i, j in sorted(edge_set):
        if i >= n or j >= n:
            continue
        a = -float(q[i, j])
        if abs(a) <= tol:
            a = 0.0
        coeffs[(i, j)] = a
        self_terms[i] -= a
        self_terms[j] -= a
    return self_terms, coeffs


def recompose_local_symmetric_q(
    self_terms: Array,
    edge_coeffs: dict[tuple[int, int], float],
) -> Array:
    """Recompose Q from d_i and a_e rank-one physical cell coefficients."""
    d = np.asarray(self_terms, dtype=float).ravel()
    q = np.diag(d.copy())
    for (i, j), a in edge_coeffs.items():
        i = int(i)
        j = int(j)
        a = float(a)
        q[i, i] += a
        q[j, j] += a
        q[i, j] -= a
        q[j, i] -= a
    return q


def gradient_traversal_ticks(steps: int, *, objective_terms: int = 1) -> int:
    """Wave ticks for one forward plus one simultaneous +/- reverse per term."""
    steps = int(steps)
    objective_terms = int(objective_terms)
    if steps <= 0 or objective_terms <= 0:
        raise ValueError("steps and objective_terms must be positive")
    return 2 * steps * objective_terms


def gradient_hold_seconds(
    steps: int,
    clock_hz: float,
    *,
    objective_terms: int = 1,
    control_ticks_per_term: int = 2,
) -> float:
    """Approximate PARAM_HOLD duration including clone/mirror control slots."""
    f = float(clock_hz)
    if not math.isfinite(f) or f <= 0:
        raise ValueError("clock_hz must be finite and positive")
    ticks = gradient_traversal_ticks(steps, objective_terms=objective_terms)
    ticks += int(control_ticks_per_term) * int(objective_terms)
    return ticks / f


def retention_time_constant_seconds(clock_hz: float, leakage_per_tick: float) -> float:
    """RC-like time constant that gives the requested per-tick amplitude loss."""
    f = float(clock_hz)
    ell = float(leakage_per_tick)
    if not math.isfinite(f) or f <= 0:
        raise ValueError("clock_hz must be finite and positive")
    if not (0.0 < ell < 1.0):
        raise ValueError("leakage_per_tick must lie in (0,1)")
    return -(1.0 / f) / math.log1p(-ell)


@dataclass(frozen=True)
class TW1ACircuitProfile:
    """Reference TW-1A v0.2 topology, before transistor sizing."""

    rows: int = 8
    cols: int = 8
    ports: int = 8
    wave_lanes: int = 2
    temporal_state_banks_per_lane: int = 2

    edge_bits: int = 8
    edge_full_scale: float = 0.25
    self_bits: int = 12
    self_full_scale: float = 3.0

    drive_dac_bits: int = 8
    error_dac_bits: int = 10
    sense_adc_bits: int = 8
    credit_adc_bits: int = 10

    recommended_leakage_per_tick: float = 0.001
    recommended_clock_hz_for_bringup: float = 1_000_000.0

    shared_edge_multiply_across_lanes: bool = True
    shared_error_dac_with_sign_flip: bool = True
    single_signed_credit_accumulator: bool = True
    parameter_write_lock_during_gradient: bool = True
    exact_zero_edge_code: bool = True
    mirror_is_pointer_swap: bool = True

    @property
    def nodes(self) -> int:
        return self.rows * self.cols

    @property
    def edges(self) -> int:
        return len(grid_edges(self.rows, self.cols))

    @property
    def differential_state_registers(self) -> int:
        return self.nodes * self.wave_lanes * self.temporal_state_banks_per_lane

    @property
    def scalar_sample_capacitors_minimum(self) -> int:
        return 2 * self.differential_state_registers

    def validate(self) -> None:
        if self.nodes != 64 or self.edges != 112:
            raise ValueError("TW-1A v0.2 reference profile is the 8x8 / 112-edge tile")
        derived_fs = required_self_path_full_scale(
            q_diag_full_scale=1.95,
            q_edge_full_scale=self.edge_full_scale,
            degree=max_grid_degree(self.rows, self.cols),
        )
        if self.self_full_scale + 1e-12 < derived_fs:
            raise ValueError(
                f"self path full scale {self.self_full_scale} is below derived {derived_fs}"
            )
        needed_bits = self_bits_matching_edge_lsb(
            edge_bits=self.edge_bits,
            edge_full_scale=self.edge_full_scale,
            self_full_scale=self.self_full_scale,
        )
        if self.self_bits < needed_bits:
            raise ValueError(
                f"self path needs >= {needed_bits} bits to match {self.edge_bits}-bit edge LSB"
            )
        if not all(
            (
                self.shared_edge_multiply_across_lanes,
                self.shared_error_dac_with_sign_flip,
                self.single_signed_credit_accumulator,
                self.parameter_write_lock_during_gradient,
                self.exact_zero_edge_code,
                self.mirror_is_pointer_swap,
            )
        ):
            raise ValueError("reference profile requires all structural coherence invariants")

    def resource_summary(self, *, trainable_edges: int | None = None) -> dict[str, Any]:
        self.validate()
        et = self.edges if trainable_edges is None else int(trainable_edges)
        if not 0 <= et <= self.edges:
            raise ValueError("trainable_edges outside physical capacity")
        return {
            "wave_nodes": self.nodes,
            "reciprocal_edge_cells": self.edges,
            "trainable_local_credit_cells": et,
            "wave_lanes": self.wave_lanes,
            "differential_state_registers": self.differential_state_registers,
            "minimum_scalar_state_sample_caps": self.scalar_sample_capacitors_minimum,
            "node_self_mdacs": self.nodes,
            "edge_mdacs": self.edges,
            "ports": self.ports,
            "sense_adc_bits": self.sense_adc_bits,
            "credit_adc_bits": self.credit_adc_bits,
            "note": "architecture resources, not transistor/area estimates",
        }

    def coherence_contract(self) -> dict[str, Any]:
        self.validate()
        return {
            "gradient_scope": "PARAM_HOLD from first objective forward through final objective reverse pair",
            "edge_code_storage": "digital signed code; writes inhibited during PARAM_HOLD",
            "edge_realization": (
                "one switched-capacitor/charge-domain rank-one MDAC reused for lanes A and B inside each wave tick"
            ),
            "reverse_pair": "lane A evolves F+A and lane B evolves F-A in lockstep under the same held operator",
            "error_injection": "one magnitude DAC sample routed + to lane A and - to lane B",
            "credit_acquisition": (
                "one edge squarer/integrator adds (Delta z_plus)^2 and subtracts (Delta z_minus)^2"
            ),
            "mirror": "swap current/previous bank roles; no analog momentum-gain multiply",
            "terminal_clone": "copy lane-A terminal current/previous into lane B once, then pointer-swap both",
            "expected_effect": (
                "PLUS/MINUS coefficient drift, DAC gain drift and LCC DC offset become primarily common-mode or adjacent-subphase errors"
            ),
            "qualification_status": "architecture hypothesis; re-test in circuit emulator then SPICE/board hardware",
        }

    def tick_microphases(self) -> list[str]:
        return [
            "PHI0_PRECHARGE_AND_AUTOZERO",
            "PHI1_LANE_A_SAMPLE_EDGE_DIFFERENCES",
            "PHI2_LANE_A_TRANSFER_EDGE_AND_SELF_CHARGE",
            "PHI3_LCC_ADD_PLUS_SQUARE",
            "PHI4_LANE_B_SAMPLE_EDGE_DIFFERENCES",
            "PHI5_LANE_B_TRANSFER_EDGE_AND_SELF_CHARGE",
            "PHI6_LCC_SUBTRACT_MINUS_SQUARE",
            "PHI7_COMMIT_BOTH_LANES",
        ]

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        d = asdict(self)
        d.update(
            {
                "architecture": "tw1a-sc-lockstep-v0.2",
                "nodes": self.nodes,
                "physical_edges": self.edges,
                "derived_self_full_scale_min": required_self_path_full_scale(),
                "derived_self_bits_to_match_edge_lsb": self_bits_matching_edge_lsb(
                    edge_bits=self.edge_bits,
                    edge_full_scale=self.edge_full_scale,
                    self_full_scale=self.self_full_scale,
                ),
                "resource_summary": self.resource_summary(),
                "coherence_contract": self.coherence_contract(),
                "reverse_tick_microphases": self.tick_microphases(),
                "recommended_retention_tau_at_bringup_seconds": retention_time_constant_seconds(
                    self.recommended_clock_hz_for_bringup,
                    self.recommended_leakage_per_tick,
                ),
            }
        )
        return d
