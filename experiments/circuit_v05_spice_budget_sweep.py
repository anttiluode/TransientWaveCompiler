"""Diagnostic SPICE-handoff sweeps for the qualified v0.5 architecture.

Uses already-spent bodies 1500-1509. Results are diagnostic only.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v05_corner import SEEDS, config_for
from transientwave.circuit_emulator_v05 import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


AXES = {
    "edge_lane_match_std": [0.001, 0.003, 0.010, 0.030, 0.100],
    "edge_common_settling_loss": [0.10, 0.20, 0.30, 0.40, 0.50],
}


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    clean = n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25
    return {
        "all_body_clean": clean,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gaps)),
    }


def run_point(axis: str, value: float):
    rows = []
    for seed in SEEDS:
        cfg = replace(config_for(seed), **{axis: value})
        result, gain = run_order_contrast_training(
            compile_temporal_order_task(seed),
            cfg,
            iterations=30,
            step_size=0.20,
        )
        rows.append({
            "seed": seed,
            "sense_gain": gain,
            "improvement": result.exact_improvement,
            "placement_gap": result.placement_gap,
            "final_exact": result.exact_contrast[-1],
            "final_shuffled": result.shuffled_contrast[-1],
            "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
        })
    return rows


def main() -> None:
    out = {
        "experiment": "tw1a-v05-spice-handoff-diagnostic-sweep",
        "status": "diagnostic-only-spent-bodies",
        "preregistration": "docs/CIRCUIT_V05_SPICE_SWEEP_PREREG.md",
        "seeds": SEEDS,
        "axes": {},
    }
    for axis, values in AXES.items():
        points = []
        print("AXIS", axis, flush=True)
        for value in values:
            rows = run_point(axis, float(value))
            summary = summarize(rows)
            points.append({"value": value, "summary": summary, "runs": rows})
            print(f"  {value:g} {summary}", flush=True)
        out["axes"][axis] = points

    Path("circuit-v05-spice-budget-sweep.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
