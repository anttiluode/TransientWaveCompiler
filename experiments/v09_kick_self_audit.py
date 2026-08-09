"""Audit how much programmable self remains after exact Q -> Q-2I kick-drift split."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from transientwave.circuit_architecture import decompose_local_symmetric_q, grid_edges
from transientwave.kick_drift import kick_operator
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2300, 2310))


def stats(x):
    a = np.asarray(x, dtype=float)
    return {
        "min": float(np.min(a)),
        "max": float(np.max(a)),
        "max_abs": float(np.max(np.abs(a))),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "rms": float(np.sqrt(np.mean(a * a))),
    }


def main() -> None:
    edges = grid_edges()
    rows = []
    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        manifest = task["target"]
        Q = np.asarray(manifest["Q"], dtype=float)
        K = kick_operator(Q)
        q_self, q_edges = decompose_local_symmetric_q(Q, edges=edges)
        k_self, k_edges = decompose_local_symmetric_q(K, edges=edges)

        # Off-diagonal/rank-one parameterization must be exactly unchanged.
        edge_delta = max(abs(float(q_edges[e]) - float(k_edges[e])) for e in q_edges)

        r = float(manifest["gauge"]["r"])
        q0 = r + 1.0 / r
        force_self = q_self - q0
        active = np.asarray(task["metadata"]["active_cells"], dtype=int)
        inactive = np.asarray(sorted(set(range(Q.shape[0])) - set(active.tolist())), dtype=int)

        row = {
            "seed": seed,
            "r": r,
            "inertial_q0": q0,
            "edge_coefficient_max_delta_after_minus_2I": edge_delta,
            "q_self_all": stats(q_self),
            "kick_self_all": stats(k_self),
            "force_self_all": stats(force_self),
            "q_self_active": stats(q_self[active]),
            "kick_self_active": stats(k_self[active]),
            "force_self_active": stats(force_self[active]),
            "q_self_inactive": stats(q_self[inactive]) if inactive.size else None,
            "kick_self_inactive": stats(k_self[inactive]) if inactive.size else None,
            "active_nodes": int(active.size),
            "inactive_nodes": int(inactive.size),
        }
        rows.append(row)
        print(
            f"{seed}: q0={q0:.9f} "
            f"active |selfQ|max={row['q_self_active']['max_abs']:.9f} "
            f"|selfK|max={row['kick_self_active']['max_abs']:.9f} "
            f"|force|max={row['force_self_active']['max_abs']:.9f} "
            f"edge_delta={edge_delta:.3e}",
            flush=True,
        )

    qmax = [r["q_self_active"]["max_abs"] for r in rows]
    kmax = [r["kick_self_active"]["max_abs"] for r in rows]
    fmax = [r["force_self_active"]["max_abs"] for r in rows]
    reduction = [q / k for q, k in zip(qmax, kmax) if k > 0]
    thermal_reduction = [np.sqrt(q / k) for q, k in zip(qmax, kmax) if k > 0]
    summary = {
        "max_active_q_self": float(max(qmax)),
        "max_active_kick_self": float(max(kmax)),
        "max_active_force_self_after_q0": float(max(fmax)),
        "median_self_magnitude_reduction_q_over_k": float(statistics.median(reduction)),
        "median_sampling_noise_reduction_sqrt_q_over_k": float(statistics.median(thermal_reduction)),
        "all_edge_coefficients_unchanged": bool(
            max(r["edge_coefficient_max_delta_after_minus_2I"] for r in rows) == 0.0
        ),
    }
    print("summary", summary, flush=True)
    Path("v09-kick-self-audit.json").write_text(
        json.dumps({"experiment": "v09-kick-drift-self-audit", "seeds": SEEDS, "summary": summary, "runs": rows}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
