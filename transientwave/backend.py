"""Logical TW-1A backend resource and routing model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class TW1AGridBackend:
    rows: int = 8
    cols: int = 8
    q_edge_min: float = -0.25
    q_edge_max: float = 0.25
    q_diag_min: float = -1.95
    q_diag_max: float = 1.95
    ports: int = 8
    zero_tolerance: float = 1e-12

    @property
    def nodes(self) -> int:
        return self.rows * self.cols

    def physical_edges(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for r in range(self.rows):
            for c in range(self.cols):
                i = r * self.cols + c
                if c + 1 < self.cols:
                    out.append((i, i + 1))
                if r + 1 < self.rows:
                    out.append((i, i + self.cols))
        return out

    def allowed_edge_set(self) -> set[tuple[int, int]]:
        return {tuple(sorted(e)) for e in self.physical_edges()}


def extract_active_edges(Q: np.ndarray, tol: float = 1e-12) -> list[tuple[int, int, float]]:
    """Return i<j off-diagonal nonzero couplings from a symmetric Q."""
    n = Q.shape[0]
    out: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            q = float(Q[i, j])
            if abs(q) > tol:
                out.append((i, j, q))
    return out


def direct_grid_route(Q: np.ndarray, backend: TW1AGridBackend | None = None) -> dict:
    """Route logical node i directly to physical grid node i.

    This is intentionally strict. v0.1 does not pretend to contain a general graph
    placer. A later pass may permute nodes or insert relay/delay nodes.
    """
    b = TW1AGridBackend() if backend is None else backend
    n = Q.shape[0]
    if n > b.nodes:
        raise ValueError(f"program has {n} nodes; backend has {b.nodes}")

    allowed = b.allowed_edge_set()
    physical_ids = {edge: k for k, edge in enumerate(b.physical_edges())}
    active = extract_active_edges(Q, b.zero_tolerance)

    unroutable = [(i, j, q) for i, j, q in active if (i, j) not in allowed]
    if unroutable:
        preview = ", ".join(f"({i},{j})={q:.4g}" for i, j, q in unroutable[:6])
        if len(unroutable) > 6:
            preview += f", ... +{len(unroutable)-6} more"
        raise ValueError(
            "logical Q contains nonlocal edges not present in direct 8x8 four-neighbor fabric: " + preview
        )

    edge_map = []
    for i, j, q in active:
        if not (b.q_edge_min <= q <= b.q_edge_max):
            raise ValueError(
                f"edge ({i},{j}) coefficient {q:.6g} outside backend range "
                f"[{b.q_edge_min},{b.q_edge_max}]"
            )
        edge_map.append(
            {
                "logical_edge": [i, j],
                "physical_edge": physical_ids[(i, j)],
                "q": q,
            }
        )

    diag = np.diag(Q)
    bad_diag = [
        (i, float(q)) for i, q in enumerate(diag)
        if not (b.q_diag_min <= float(q) <= b.q_diag_max)
    ]
    if bad_diag:
        preview = ", ".join(f"{i}:{q:.4g}" for i, q in bad_diag[:6])
        raise ValueError(
            f"diagonal Q coefficients exceed backend range [{b.q_diag_min},{b.q_diag_max}]: {preview}"
        )

    node_map = [
        {
            "logical_node": i,
            "physical_node": i,
            "row": i // b.cols,
            "col": i % b.cols,
        }
        for i in range(n)
    ]

    return {
        "backend": "tw1a-8x8-v0",
        "node_map": node_map,
        "edge_map": edge_map,
        "active_edges": len(active),
        "physical_edge_capacity": len(b.physical_edges()),
        "unused_physical_edges": len(b.physical_edges()) - len(active),
    }
