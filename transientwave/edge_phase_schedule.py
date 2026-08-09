"""Deterministic four-color edge schedule for the rectangular TW-1A mesh.

The four-neighbor rectangular grid has maximum degree four.  A simple parity
coloring partitions every physical bond into four matchings:

* H-even, H-odd
* V-even, V-odd

Within one phase no physical node participates in more than one edge transfer.
For active charge summing this makes the edge-transfer feedback factor depend on
one selected edge capacitor rather than the sum of all incident edge capacitors.
"""
from __future__ import annotations

from collections import Counter

from .backend import TW1AGridBackend


PHASE_NAMES = ("H0", "H1", "V0", "V1")


def edge_phase(edge: tuple[int, int], backend: TW1AGridBackend | None = None) -> int:
    b = TW1AGridBackend() if backend is None else backend
    i, j = tuple(sorted(edge))
    ri, ci = divmod(i, b.cols)
    rj, cj = divmod(j, b.cols)
    if ri == rj and cj == ci + 1:
        return ci & 1
    if ci == cj and rj == ri + 1:
        return 2 + (ri & 1)
    raise ValueError(f"edge {edge} is not one nearest-neighbor bond of the grid")


def four_phase_edge_schedule(
    backend: TW1AGridBackend | None = None,
) -> list[list[tuple[int, int]]]:
    b = TW1AGridBackend() if backend is None else backend
    phases: list[list[tuple[int, int]]] = [[] for _ in range(4)]
    for edge in b.physical_edges():
        phases[edge_phase(edge, b)].append(edge)
    return phases


def schedule_audit(backend: TW1AGridBackend | None = None) -> dict:
    b = TW1AGridBackend() if backend is None else backend
    phases = four_phase_edge_schedule(b)
    max_node_use = []
    duplicate_nodes = []
    for phase in phases:
        counts = Counter(node for edge in phase for node in edge)
        max_node_use.append(max(counts.values(), default=0))
        duplicate_nodes.append(sorted(node for node, n in counts.items() if n > 1))
    flat = [tuple(sorted(e)) for phase in phases for e in phase]
    physical = [tuple(sorted(e)) for e in b.physical_edges()]
    return {
        "phase_names": list(PHASE_NAMES),
        "phase_edge_counts": [len(p) for p in phases],
        "max_node_use_per_phase": max_node_use,
        "duplicate_nodes_per_phase": duplicate_nodes,
        "covers_all_edges_once": len(flat) == len(set(flat)) == len(physical) and set(flat) == set(physical),
    }
