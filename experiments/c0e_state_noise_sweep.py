"""Diagnostic C0e state-noise sweep on spent C0d bodies 1700-1709."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v05_segmented_mismatch_corner import SEEDS, config_for
from transientwave.circuit_emulator_v05_segmented_mismatch import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


VALUES = [0.0, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "all_body_clean": n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gaps)),
    }


def main() -> None:
    out = {
        "experiment": "tw1a-c0e-state-noise-budget-diagnostic",
        "status": "diagnostic-only-spent-bodies",
        "preregistration": "docs/CIRCUIT_C0E_STATE_NOISE_PREREG.md",
        "seeds": SEEDS,
        "values": [],
    }

    for value in VALUES:
        rows = []
        print(f"state_noise_std={value:g}", flush=True)
        for seed in SEEDS:
            cfg = replace(config_for(seed), state_noise_std=float(value))
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
        summary = summarize(rows)
        print("  ", summary, flush=True)
        out["values"].append({
            "state_noise_std": value,
            "summary": summary,
            "runs": rows,
        })

    Path("c0e-state-noise-sweep.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
