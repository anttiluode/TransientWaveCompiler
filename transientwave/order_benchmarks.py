"""Temporal-order discrimination benchmarks for TW-1A.

Each task is a pair of ordinary compiled quadratic-energy programs.  Target AB
and distractor BA contain the same two leaf events at the same two times; only
which leaf receives the early event is exchanged.
"""
from __future__ import annotations

from collections import deque
from itertools import combinations
from typing import Any

import numpy as np

from .benchmarks import NODES, _grow_tree, _distances
from .ir import program_from_dict
from .physical import compile_tw1a


def _adjacency(active: list[int], edges: list[tuple[int, int]]) -> dict[int, list[int]]:
    adj = {i: [] for i in active}
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    return adj


def _tree_distance(a: int, b: int, adj: dict[int, list[int]]) -> int:
    q: deque[tuple[int, int]] = deque([(a, 0)])
    seen = {a}
    while q:
        i, d = q.popleft()
        if i == b:
            return d
        for j in adj[i]:
            if j not in seen:
                seen.add(j)
                q.append((j, d + 1))
    raise RuntimeError("tree is disconnected")


def _choose_leaf_pair(
    active: list[int], edges: list[tuple[int, int]], root: int = 0
) -> tuple[int, int, dict[str, int]]:
    """Choose two distal, well-separated non-root leaves deterministically."""
    adj = _adjacency(active, edges)
    root_dist = _distances(root, edges, active)
    leaves = sorted(i for i in active if i != root and len(adj[i]) == 1)
    if len(leaves) < 2:
        raise RuntimeError("temporal-order benchmark needs at least two non-root leaves")

    scored: list[tuple[tuple[int, int, int, int, int], int, int, int]] = []
    for a, b in combinations(leaves, 2):
        pair_d = _tree_distance(a, b, adj)
        score = (
            min(root_dist[a], root_dist[b]),
            pair_d,
            root_dist[a] + root_dist[b],
            max(a, b),
            min(a, b),
        )
        scored.append((score, a, b, pair_d))
    _, a, b, pair_d = max(scored, key=lambda x: x[0])
    return a, b, {
        "leaf_a_root_distance": int(root_dist[a]),
        "leaf_b_root_distance": int(root_dist[b]),
        "leaf_pair_distance": int(pair_d),
        "leaf_count": int(len(leaves)),
    }


def _event_waveform(steps: int, tick: int, amplitude: float) -> list[float]:
    if not 0 <= tick < steps:
        raise ValueError("event tick outside horizon")
    w = np.zeros(steps, dtype=float)
    w[tick] = float(amplitude)
    return w.tolist()


def temporal_order_program_dicts(
    seed: int,
    *,
    active_nodes: int = 40,
    steps: int = 96,
    dt: float = 0.08,
    gamma: float = 0.40,
    onsite: float = 1.0,
    edge_stiffness: float = 10.0,
    parked_onsite: float = 10.0,
    event_amplitude: float = 6.0,
    early_tick: int = 4,
    late_tick: int = 20,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return target AB, distractor BA source programs and shared metadata."""
    if early_tick >= late_tick:
        raise ValueError("early_tick must be earlier than late_tick")

    active, edges = _grow_tree(seed, active_nodes)
    active_set = set(active)
    leaf_a, leaf_b, leaf_meta = _choose_leaf_pair(active, edges, root=0)

    H = np.eye(NODES, dtype=float) * float(parked_onsite)
    for i in active:
        H[i, i] = float(onsite)
    for i, j in edges:
        k = float(edge_stiffness)
        H[i, i] += k
        H[j, j] += k
        H[i, j] -= k
        H[j, i] -= k

    for i in range(NODES):
        if i not in active_set:
            H[i, :i] = 0.0
            H[i, i + 1 :] = 0.0
            H[:i, i] = 0.0
            H[i + 1 :, i] = 0.0

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

    common: dict[str, Any] = {
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
        "objective": {
            "kind": "quadratic_energy",
            "port": "soma",
            "weight": 1.0,
        },
        "trainable_edges": trainable,
        "constraints": {
            "stability_margin": 0.001,
            "max_boundary_gain": 8.0,
            "require_reciprocal": True,
            "allow_partition": False,
        },
    }

    early = _event_waveform(steps, early_tick, event_amplitude)
    late = _event_waveform(steps, late_tick, event_amplitude)

    def make(order: str) -> dict[str, Any]:
        d = dict(common)
        d["name"] = f"temporal_order_{order}_{seed}"
        if order == "AB":
            wa, wb = early, late
        elif order == "BA":
            wa, wb = late, early
        else:
            raise ValueError(order)
        d["ports"] = [
            {"name": "leaf_a", "node": int(leaf_a), "kind": "drive", "waveform": wa},
            {"name": "leaf_b", "node": int(leaf_b), "kind": "drive", "waveform": wb},
            {"name": "soma", "node": 0, "kind": "sense"},
        ]
        d["metadata"] = {
            "benchmark": "tw1a_temporal_order_contrast_v01",
            "seed": int(seed),
            "order": order,
            "active_nodes": int(active_nodes),
            "active_cells": active,
            "tree_edges": [list(e) for e in edges],
            "leaf_a": int(leaf_a),
            "leaf_b": int(leaf_b),
            **leaf_meta,
            "root": 0,
            "early_tick": int(early_tick),
            "late_tick": int(late_tick),
            "event_amplitude": float(event_amplitude),
            "active_onsite": float(onsite),
            "parked_onsite": float(parked_onsite),
        }
        return d

    meta = {
        "seed": int(seed),
        "leaf_a": int(leaf_a),
        "leaf_b": int(leaf_b),
        **leaf_meta,
        "active_cells": active,
        "tree_edges": [list(e) for e in edges],
    }
    return make("AB"), make("BA"), meta


def compile_temporal_order_task(seed: int, **kwargs: Any) -> dict[str, Any]:
    """Compile a matched AB/BA task pair through the strict TW-1A backend."""
    ab, ba, meta = temporal_order_program_dicts(seed, **kwargs)
    target = compile_tw1a(program_from_dict(ab))
    distractor = compile_tw1a(program_from_dict(ba))

    qa = np.asarray(target["Q"], dtype=float)
    qb = np.asarray(distractor["Q"], dtype=float)
    if not np.array_equal(qa, qb):
        raise RuntimeError("AB and BA compiled to different Q matrices")
    if target["trainable_edges"] != distractor["trainable_edges"]:
        raise RuntimeError("AB and BA trainable-edge maps differ")

    return {
        "format": "tw1a-order-contrast-v0.1",
        "seed": int(seed),
        "target": target,
        "distractor": distractor,
        "metadata": meta,
    }
