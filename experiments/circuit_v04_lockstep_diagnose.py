"""Fine diagnostic of the v0.4 lockstep dynamic error group.

Bodies 1400-1409 are already spent. Results are diagnostic only.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v04_corner import SEEDS, config_for
from transientwave.circuit_emulator_v04 import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


CASES = {
    "full_failed_corner": {},
    "no_b_settling_loss": {"edge_settling_error": 0.0},
    "no_ab_edge_memory": {"ab_edge_memory": 0.0},
    "no_error_dac_sign_asymmetry": {"error_dac_sign_asymmetry": 0.0},
    "no_settling_and_memory": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
    },
    "no_settling_and_error_asym": {
        "edge_settling_error": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "no_memory_and_error_asym": {
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "all_three_ideal": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
}


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gap = [float(r["placement_gap"]) for r in rows]
    return {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(bool(r["final_win"]) for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "median_placement_gap": float(statistics.median(gap)),
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gap)),
    }


def main() -> None:
    output = {
        "experiment": "tw1a-v04-lockstep-diagnostic",
        "status": "diagnostic-only-spent-bodies",
        "seeds": SEEDS,
        "cases": {},
    }
    for name, changes in CASES.items():
        rows = []
        print(f"CASE {name}", flush=True)
        for seed in SEEDS:
            result, gain = run_order_contrast_training(
                compile_temporal_order_task(seed),
                replace(config_for(seed), **changes),
                iterations=30,
                step_size=0.20,
            )
            row = {
                "seed": seed,
                "sense_gain": gain,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            }
            rows.append(row)
        output["cases"][name] = {"changes": changes, "summary": summarize(rows), "runs": rows}
        print(name, output["cases"][name]["summary"], flush=True)

    Path("circuit-v04-lockstep-diagnose.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
