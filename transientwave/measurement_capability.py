"""Measurement-budget capability diagnostics for candidate physical directions.

This module deliberately contains only small, model-agnostic linearized tools.
Given a fitted/nuisance response tangent ``J`` and one candidate response
derivative ``g`` on a declared set of *real-valued measurement rows*, it
computes the part of ``g`` that cannot be reproduced by re-adjusting the
columns of ``J``.

For equal independent Gaussian measurement noise, the squared residual is the
candidate's conditional Fisher information up to the noise variance.  With
non-identity noise covariance, callers should whiten ``J`` and ``g`` first.

The construction is established linear algebra / Fisher information; TWC does
not claim novelty for it.  Its role here is operational: support capability
reports such as acquire-more / change-channel / perturb / cannot-resolve.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .identifiability import orthogonal_novelty_fraction


@dataclass(frozen=True)
class ConditionalInformation:
    """Conditional information for one candidate direction on one row set."""

    conditional_information: float
    raw_candidate_energy: float
    information_fraction: float
    novelty_fraction: float
    residual_norm: float
    candidate_norm: float
    jacobian_rank: int
    jacobian_columns: int
    jacobian_condition: float | None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "conditional_information": float(self.conditional_information),
            "raw_candidate_energy": float(self.raw_candidate_energy),
            "information_fraction": float(self.information_fraction),
            "novelty_fraction": float(self.novelty_fraction),
            "residual_norm": float(self.residual_norm),
            "candidate_norm": float(self.candidate_norm),
            "jacobian_rank": int(self.jacobian_rank),
            "jacobian_columns": int(self.jacobian_columns),
            "jacobian_condition": (
                None
                if self.jacobian_condition is None
                else float(self.jacobian_condition)
            ),
        }


def conditional_candidate_information(
    jacobian: np.ndarray,
    candidate: np.ndarray,
    *,
    rcond: float = 1e-10,
) -> ConditionalInformation:
    """Return candidate information left after fitted/nuisance compensation.

    Parameters
    ----------
    jacobian:
        Real-valued measurement Jacobian with shape ``(n_rows, n_parameters)``.
        Complex response models should realify/whiten their measurement rows
        before calling this function.
    candidate:
        Real-valued derivative of the proposed candidate parameter, one value
        per measurement row.
    rcond:
        Numerical rank cutoff passed to ``orthogonal_novelty_fraction``.

    Notes
    -----
    The primary quantity is

    ``I_c = min_beta ||candidate - jacobian @ beta||^2``.

    For nested row sets with the same parameterization, ``I_c`` is
    nondecreasing as rows are appended.  The normalized novelty fraction need
    not be monotone because the raw candidate norm changes too.
    """
    metric = orthogonal_novelty_fraction(
        np.asarray(jacobian, dtype=float),
        np.asarray(candidate, dtype=float),
        rcond=float(rcond),
    )
    candidate_norm = float(metric["candidate_norm"])
    residual_norm = float(metric["residual_norm"])
    raw = candidate_norm * candidate_norm
    info = residual_norm * residual_norm
    fraction = 0.0 if raw <= 1e-300 else float(info / raw)
    return ConditionalInformation(
        conditional_information=info,
        raw_candidate_energy=raw,
        information_fraction=fraction,
        novelty_fraction=float(metric["novelty_fraction"]),
        residual_norm=residual_norm,
        candidate_norm=candidate_norm,
        jacobian_rank=int(metric["jacobian_rank"]),
        jacobian_columns=int(metric["jacobian_columns"]),
        jacobian_condition=(
            None
            if metric["jacobian_condition"] is None
            else float(metric["jacobian_condition"])
        ),
    )


def nested_conditional_information_curve(
    jacobian_blocks: Sequence[np.ndarray],
    candidate_blocks: Sequence[np.ndarray],
    *,
    rcond: float = 1e-10,
) -> tuple[ConditionalInformation, ...]:
    """Evaluate cumulative candidate information while measurement rows grow.

    ``jacobian_blocks[k]`` and ``candidate_blocks[k]`` are appended together.
    The fitted parameter columns must be identical across all Jacobian blocks.
    This helper does not invent a stopping threshold; it only returns the
    cumulative information curve.
    """
    if len(jacobian_blocks) != len(candidate_blocks):
        raise ValueError("jacobian_blocks and candidate_blocks must have equal length")
    if not jacobian_blocks:
        raise ValueError("at least one measurement block is required")

    j_parts: list[np.ndarray] = []
    g_parts: list[np.ndarray] = []
    ncols: int | None = None
    out: list[ConditionalInformation] = []
    for j_block, g_block in zip(jacobian_blocks, candidate_blocks):
        j = np.asarray(j_block, dtype=float)
        g = np.asarray(g_block, dtype=float).reshape(-1)
        if j.ndim != 2 or j.shape[0] != g.shape[0]:
            raise ValueError("each Jacobian block must match its candidate rows")
        if ncols is None:
            ncols = int(j.shape[1])
        elif j.shape[1] != ncols:
            raise ValueError("all Jacobian blocks must have the same columns")
        j_parts.append(j)
        g_parts.append(g)
        out.append(
            conditional_candidate_information(
                np.concatenate(j_parts, axis=0),
                np.concatenate(g_parts, axis=0),
                rcond=rcond,
            )
        )
    return tuple(out)
