"""Deterministic TW-1A benchmark/task generators."""
from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from .ir import program_from_dict
from .physical import compile_tw1a


ROWS = 8
COLS = 8
NODES = ROWS * COLS


def _neighbors(i: int) -> list[int]:
    r, c = divmod(i, COLS)
    out: list[int] = []
    if c > 0:
        out.append(i - 1)
    if c + 1 < COLS:
        out.append(i + 1)
    if r > 0:
        out.append(i - COLS)
    if r + 1 < ROWS:
        out.append(i + COLS)
    return out


def _grow_tree(seed: int, active_nodes: int) -> tuple[list[int], list[tuple[int, int]]]:
    if not 2 <= active_nodes <= NODES:
        raise ValueError("active_nodes must be in [2,64]")
    rng = np.random.default_rng(seed)
    active = {0}
    edges: list[tuple[int, int]] = []

    while len(active) < active_nodes:
        frontier: list[tuple[int, int]] = []
        for i in sorted(active):
            for j in _neighbors(i):
                if j not in active:
                    frontier.append((i, j))
        if not frontier:
            raise RuntimeError("grid-growth frontier exhausted")

        # Favor recently distal/frontier growth without turning the tree into a
        # single deterministic snake.  The random choice is frozen by seed.
        parent, child = frontier[int(rng.integers(0, len(frontier)))]
        active.add(child)
        edges.append((min(parent, child), max(parent, child)))

    return sorted(active), edges


def _distances(root: int, edges: list[tuple[int, int]], active: list[int]) -> dict[int, int]:
    adj = {i: [] for i in active}
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    d = {root: 0}
    q: deque[int] = deque([root])
    while q:
        i = q.popleft()
        for j in adj[i]:
            if j not in d:
                d[j] = d[i] + 1
                q.append(j)
    return d


def irregular_arbor_program_dict(
    seed: int,
    *,
    active_nodes: int = 40,
    steps: int = 56,
    dt: float = 0.08,
    gamma: float = 0.40,
    onsite: float = 1.0,
    edge_stiffness: float = 10.0,
    drive_amplitude: float = 6.0,
) -> dict[str, Any]:
    """Create the preregistered 40-cell irregular arbor task family."""
    active, edges = _grow_tree(seed, active_nodes)
    dist = _distances(0, edges, active)
    output = max(active, key=lambda i: (dist[i], i))

    H = np.eye(NODES, dtype=float) * float(onsite)
    for i, j in edges:
        k = float(edge_stiffness)
        H[i, i] += k
        H[j, j] += k
        H[i, j] -= k
        H[j, i] -= k

    rng = np.random.default_rng(seed + 99173)
    half = steps // 2
    raw = rng.normal(size=half)
    raw = raw - float(np.mean(raw))
    scale = float(np.max(np.abs(raw))) + 1e-30
    wave = drive_amplitude * raw / scale
    waveform = wave.tolist() + [0.0] * (steps - half)

    trainable = [
        {
            "i": i,
            "j": j,
            "min": 2.0,
            "max": 18.0,
            "stiffness_scale": 1.0,
            "group": "arbor_material",
        }
        for i, j in edges
    ]

    return {
        "name": f"irregular_arbor_{seed}",
        "version": 1,
        "dt": float(dt),
        "steps": int(steps),
        "state": {
            "nodes": NODES,
            "initial": [0.0] * NODES,
            "initial_previous": [0.0] * NODES,
        },
        "dynamics": {
            "form": "continuous_damped_wave",
            "gamma": float(gamma),
            "integration": "semi_implicit_euler",
            "H": H.tolist(),
        },
        "ports": [
            {
                "name": "input",
                "node": 0,
                "kind": "drive",
                "waveform": waveform,
            },
            {
                "name": "output",
                "node": int(output),
                "kind": "sense",
            },
        ],
        "objective": {
            "kind": "quadratic_energy",
            "port": "output",
            "weight": 1.0,
        },
        "trainable_edges": trainable,
        "constraints": {
            "stability_margin": 0.001,
            "max_boundary_gain": 8.0,
            "require_reciprocal": True,
            "allow_partition": False,
        },
        "metadata": {
            "benchmark": "tw1a_irregular_arbor_v01",
            "seed": int(seed),
            "active_nodes": int(active_nodes),
            "active_cells": active,
            "tree_edges": [list(e) for e in edges],
            "output_graph_distance": int(dist[output]),
        },
    }


def compile_irregular_arbor(seed: int, **kwargs: Any) -> dict[str, Any]:
    return compile_tw1a(program_from_dict(irregular_arbor_program_dict(seed, **kwargs)))
