"""Leave-one-group-out diagnosis of the failed v0.3 simultaneous corner.

Seeds 1300-1309 are already spent. Results are diagnostic only.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator_v03 import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task
from circuit_v03_corner import SEEDS, config_for


CASES = {
    "full_failed_v03_corner": {},
    "no_old_background": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
    },
    "no_edge_gain_mismatch": {"edge_gain_cv": 0.0},
    "perfect_self_calibration": {"self_calibration_error_std": 0.0},
    "no_prev_ratio_error": {"prev_ratio_error_std": 0.0},
    "no_terminal_clone_error": {"terminal_clone_gain_std": 0.0},
    "no_ab_subphase_errors": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "no_charge_injection": {
        "edge_charge_injection_common_std": 0.0,
        "edge_charge_injection_differential_std": 0.0,
    },
    "no_common_charge": {"edge_charge_injection_common_std": 0.0},
    "no_differential_charge": {"edge_charge_injection_differential_std": 0.0},
    "no_credit_path_errors": {
        "lcc_curvature": 0.0,
        "credit_accumulator_leakage": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
    },
    "no_state_storage_errors": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "prev_ratio_error_std": 0.0,
    },
}


def summarize(rows):
    imp = [r["improvement"] for r in rows]
    gaps = [r["gap"] for r in rows]
    return {
        "n_improve_ge_0p10": sum(x >= .10 for x in imp),
        "final_wins": sum(r["win"] for r in rows),
        "median_improvement": statistics.median(imp),
        "median_gap": statistics.median(gaps),
        "min_improvement": min(imp),
        "max_improvement": max(imp),
    }


def main():
    tasks = {s: compile_temporal_order_task(s) for s in SEEDS}
    report = {"experiment": "tw1a-v03-corner-diagnose", "seeds": SEEDS, "cases": {}}
    for name, overrides in CASES.items():
        rows = []
        print(f"\n=== {name} ===", flush=True)
        for seed in SEEDS:
            result, gain = run_order_contrast_training(
                tasks[seed], replace(config_for(seed), **overrides), iterations=30, step_size=.20
            )
            rows.append({
                "seed": seed,
                "sense_gain": gain,
                "improvement": result.exact_improvement,
                "gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            })
        s = summarize(rows)
        print(name, s, flush=True)
        report["cases"][name] = {"overrides": overrides, "summary": s, "runs": rows}
    Path("circuit-v03-corner-diagnose.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
