"""Topology/gauge identifiability for classical reciprocal coupling matrices.

A two-port coupling matrix is not a unique physical realization.  Orthogonal
changes of basis inside the internal resonator subspace leave the port response
unchanged.  This module asks a narrower engineering question without using any
measured S-parameter data:

    If one presently-declared zero matrix entry is released as a candidate
    parasitic coupling, does that release an internal rotation generator that
    was previously pinned by the declared zero pattern?

If yes, the candidate edge is statically gauge-aliased: a response-equivalent
coupling-matrix realization can open that edge while compensating through the
already-declared entries.  Known physical perturbations (currently represented
as resonator diagonal detuning anchors) can be added as coordinate constraints;
only rotations commuting with every anchor survive.

The calculation is local in coupling-matrix realization space but uses only the
matrix/topology itself, not a frequency sweep, target response, optimizer, or
measurement noise model.  Special parameter values can create additional
accidental symmetries, so the result should be interpreted at the supplied
nominal matrix (or checked across generic nominal values when a purely
structural statement is desired).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter


Entry = tuple[int, int]


@dataclass(frozen=True)
class GaugeCandidateAnalysis:
    """Gauge-release result for one absent reciprocal matrix edge."""

    candidate: Entry
    aliased: bool
    baseline_gauge_dimension: int
    released_gauge_dimension: int
    nullity_gain: int
    candidate_opening_norm: float
    internal_nodes: tuple[int, ...]
    anchors: tuple[int, ...]
    generator_labels: tuple[Entry, ...]
    unit_candidate_generator_coefficients: tuple[float, ...] | None

    def as_dict(self) -> dict[str, object]:
        coeffs = None
        if self.unit_candidate_generator_coefficients is not None:
            coeffs = {
                f"K{a}{b}": float(value)
                for (a, b), value in zip(
                    self.generator_labels,
                    self.unit_candidate_generator_coefficients,
                )
                if abs(value) > 1e-12
            }
        return {
            "candidate": list(self.candidate),
            "aliased": bool(self.aliased),
            "baseline_gauge_dimension": int(self.baseline_gauge_dimension),
            "released_gauge_dimension": int(self.released_gauge_dimension),
            "nullity_gain": int(self.nullity_gain),
            "candidate_opening_norm": float(self.candidate_opening_norm),
            "internal_nodes": list(self.internal_nodes),
            "anchors": list(self.anchors),
            "unit_candidate_generator_coefficients": coeffs,
        }


def _entry(i: int, j: int) -> Entry:
    return (int(i), int(j)) if i <= j else (int(j), int(i))


def _validate_matrix(m: np.ndarray) -> np.ndarray:
    out = np.asarray(m, dtype=float)
    if out.ndim != 2 or out.shape[0] != out.shape[1]:
        raise ValueError("coupling matrix must be square")
    if out.shape[0] < 3:
        raise ValueError("coupling matrix must contain source, resonator(s), and load")
    if not np.all(np.isfinite(out)):
        raise ValueError("coupling matrix must be finite")
    if not np.allclose(out, out.T, rtol=0.0, atol=1e-12):
        raise ValueError("coupling matrix must be reciprocal/symmetric")
    return out


def _internal_nodes(n: int, internal_nodes: Sequence[int] | None) -> tuple[int, ...]:
    nodes = tuple(range(1, n - 1)) if internal_nodes is None else tuple(int(v) for v in internal_nodes)
    if len(nodes) < 2:
        raise ValueError("at least two internal resonators are required")
    if len(set(nodes)) != len(nodes):
        raise ValueError("internal_nodes must be unique")
    if any(node <= 0 or node >= n - 1 for node in nodes):
        raise ValueError("internal_nodes must exclude source/load endpoints")
    return nodes


def internal_rotation_basis(
    n: int,
    internal_nodes: Sequence[int] | None = None,
) -> tuple[tuple[Entry, ...], tuple[np.ndarray, ...]]:
    """Return the standard skew basis of so(N_internal), embedded in n nodes."""
    nodes = _internal_nodes(int(n), internal_nodes)
    labels: list[Entry] = []
    basis: list[np.ndarray] = []
    for a, b in combinations(nodes, 2):
        k = np.zeros((n, n), dtype=float)
        k[a, b] = 1.0
        k[b, a] = -1.0
        labels.append((a, b))
        basis.append(k)
    return tuple(labels), tuple(basis)


def realization_tangent(m: np.ndarray, generator: np.ndarray) -> np.ndarray:
    """Return d/dtheta [R M R^T] at theta=0 for skew generator K."""
    matrix = _validate_matrix(m)
    k = np.asarray(generator, dtype=float)
    if k.shape != matrix.shape:
        raise ValueError("generator shape mismatch")
    if not np.allclose(k, -k.T, rtol=0.0, atol=1e-12):
        raise ValueError("generator must be skew-symmetric")
    # R(theta)=exp(theta K): d(R M R^T)/dtheta = K M - M K.
    return k @ matrix - matrix @ k


def _declared_entries(parameters: Sequence[MatrixParameter]) -> set[Entry]:
    return {_entry(parameter.i, parameter.j) for parameter in parameters}


def _upper_entries(n: int) -> list[Entry]:
    return [(i, j) for i in range(n) for j in range(i, n)]


def _nullspace(matrix: np.ndarray, *, rcond: float) -> tuple[np.ndarray, int]:
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2:
        raise ValueError("constraint matrix must be two-dimensional")
    if a.shape[1] == 0:
        return np.zeros((0, 0), dtype=float), 0
    if a.shape[0] == 0:
        return np.eye(a.shape[1], dtype=float), 0
    _u, singular, vh = np.linalg.svd(a, full_matrices=True)
    if len(singular) == 0 or singular[0] <= 0.0:
        rank = 0
    else:
        rank = int(np.sum(singular > float(rcond) * singular[0]))
    return vh[rank:].T.copy(), rank


def _anchor_constraint_rows(
    basis: Sequence[np.ndarray],
    anchors: Iterable[int],
    n: int,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for node in anchors:
        node = int(node)
        if node <= 0 or node >= n - 1:
            raise ValueError("detuning anchors must be internal resonator nodes")
        d = np.zeros((n, n), dtype=float)
        d[node, node] = 1.0
        commutators = [k @ d - d @ k for k in basis]
        for i, j in _upper_entries(n):
            row = [float(c[i, j]) for c in commutators]
            if any(abs(value) > 0.0 for value in row):
                rows.append(row)
    return rows


def analyze_candidate_gauge(
    m: np.ndarray,
    declared_parameters: Sequence[MatrixParameter],
    candidate: MatrixParameter | Entry,
    *,
    internal_nodes: Sequence[int] | None = None,
    anchors: Sequence[int] = (),
    fixed_parameters: Sequence[MatrixParameter] = (),
    rcond: float = 1e-10,
) -> GaugeCandidateAnalysis:
    """Test whether releasing one declared zero opens a response-invariant gauge.

    ``declared_parameters`` and ``fixed_parameters`` define entries allowed to
    be nonzero in the base realization.  All other upper-triangular entries are
    treated as declared zeros.  The candidate must be one absent off-diagonal
    reciprocal edge.

    ``anchors`` are known physical resonator detunings shared across the
    measurement protocol.  A surviving gauge generator must commute with every
    corresponding diagonal stamp, because those perturbations label the
    physical resonator coordinates.
    """
    matrix = _validate_matrix(m)
    n = matrix.shape[0]
    nodes = _internal_nodes(n, internal_nodes)
    if not np.isfinite(rcond) or rcond <= 0.0:
        raise ValueError("rcond must be finite and positive")

    if isinstance(candidate, MatrixParameter):
        key = _entry(candidate.i, candidate.j)
    else:
        if len(candidate) != 2:
            raise ValueError("candidate must contain two node indices")
        key = _entry(candidate[0], candidate[1])
    if key[0] == key[1]:
        raise ValueError("candidate must be an off-diagonal reciprocal edge")
    if key[0] < 0 or key[1] >= n:
        raise ValueError("candidate endpoint out of range")

    allowed = _declared_entries([*declared_parameters, *fixed_parameters])
    if key in allowed:
        raise ValueError(f"candidate edge {key} is already declared")

    labels, basis = internal_rotation_basis(n, nodes)
    tangents = [realization_tangent(matrix, k) for k in basis]
    zeros = [entry for entry in _upper_entries(n) if entry not in allowed]
    anchor_rows = _anchor_constraint_rows(basis, anchors, n)

    def constraint_matrix(include_candidate_zero: bool) -> np.ndarray:
        entries = zeros if include_candidate_zero else [entry for entry in zeros if entry != key]
        rows = [
            [float(tangent[i, j]) for tangent in tangents]
            for i, j in entries
        ]
        rows.extend(anchor_rows)
        if not rows:
            return np.zeros((0, len(basis)), dtype=float)
        return np.asarray(rows, dtype=float)

    baseline_null, baseline_rank = _nullspace(
        constraint_matrix(True),
        rcond=rcond,
    )
    released_null, released_rank = _nullspace(
        constraint_matrix(False),
        rcond=rcond,
    )
    baseline_dim = len(basis) - baseline_rank
    released_dim = len(basis) - released_rank

    candidate_vector = np.asarray([tangent[key] for tangent in tangents], dtype=float)
    if released_null.size:
        candidate_in_null = released_null.T @ candidate_vector
        opening_norm = float(np.linalg.norm(candidate_in_null))
    else:
        candidate_in_null = np.zeros(0, dtype=float)
        opening_norm = 0.0

    scale = max(1.0, float(np.linalg.norm(candidate_vector)))
    aliased = bool(
        released_dim > baseline_dim
        and opening_norm > float(rcond) * scale
    )

    unit_coefficients: tuple[float, ...] | None = None
    if aliased:
        # Choose the surviving generator direction with the largest candidate
        # component, then scale it so delta M[candidate] = +1.
        alpha = released_null @ candidate_in_null
        amplitude = float(candidate_vector @ alpha)
        if abs(amplitude) > float(rcond) * scale:
            alpha = alpha / amplitude
            unit_coefficients = tuple(float(value) for value in alpha)

    return GaugeCandidateAnalysis(
        candidate=key,
        aliased=aliased,
        baseline_gauge_dimension=int(baseline_dim),
        released_gauge_dimension=int(released_dim),
        nullity_gain=int(released_dim - baseline_dim),
        candidate_opening_norm=opening_norm,
        internal_nodes=nodes,
        anchors=tuple(int(v) for v in anchors),
        generator_labels=labels,
        unit_candidate_generator_coefficients=unit_coefficients,
    )


def absent_reciprocal_edges(
    n: int,
    declared_parameters: Sequence[MatrixParameter],
    *,
    fixed_parameters: Sequence[MatrixParameter] = (),
) -> list[Entry]:
    allowed = _declared_entries([*declared_parameters, *fixed_parameters])
    return [
        (i, j)
        for i in range(int(n))
        for j in range(i + 1, int(n))
        if (i, j) not in allowed
    ]


def analyze_absent_edges_gauge(
    m: np.ndarray,
    declared_parameters: Sequence[MatrixParameter],
    *,
    internal_nodes: Sequence[int] | None = None,
    anchors: Sequence[int] = (),
    fixed_parameters: Sequence[MatrixParameter] = (),
    rcond: float = 1e-10,
) -> list[GaugeCandidateAnalysis]:
    matrix = _validate_matrix(m)
    return [
        analyze_candidate_gauge(
            matrix,
            declared_parameters,
            edge,
            internal_nodes=internal_nodes,
            anchors=anchors,
            fixed_parameters=fixed_parameters,
            rcond=rcond,
        )
        for edge in absent_reciprocal_edges(
            matrix.shape[0],
            declared_parameters,
            fixed_parameters=fixed_parameters,
        )
    ]


def single_detuning_anchors_that_break_alias(
    m: np.ndarray,
    declared_parameters: Sequence[MatrixParameter],
    candidate: MatrixParameter | Entry,
    *,
    internal_nodes: Sequence[int] | None = None,
    fixed_parameters: Sequence[MatrixParameter] = (),
    rcond: float = 1e-10,
) -> list[int]:
    """Return individual resonator detunings that eliminate candidate gauge alias."""
    matrix = _validate_matrix(m)
    nodes = _internal_nodes(matrix.shape[0], internal_nodes)
    base = analyze_candidate_gauge(
        matrix,
        declared_parameters,
        candidate,
        internal_nodes=nodes,
        fixed_parameters=fixed_parameters,
        rcond=rcond,
    )
    if not base.aliased:
        return []
    return [
        node
        for node in nodes
        if not analyze_candidate_gauge(
            matrix,
            declared_parameters,
            candidate,
            internal_nodes=nodes,
            anchors=(node,),
            fixed_parameters=fixed_parameters,
            rcond=rcond,
        ).aliased
    ]
