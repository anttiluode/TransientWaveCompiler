"""Diagnostic leave-one-group-out analysis of the failed v0.1 circuit corner.

Bodies 1200-1209 are already spent by the preregistered corner.  These results
are diagnostic only and cannot establish a revised safe corner.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task
from circuit_native_corner_v01 import SEEDS, config_for


CASES = {
    "full_failed_corner": {},
    "no_old_background": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
    },
    "no_edge_gain_mismatch": {"edge_gain_cv": 0.0},
    "no_self_gain_mismatch": {"self_gain_cv": 0.0},
    "no_prev_ratio_error": {"prev_ratio_error_std": 0.0},
    "no_terminal_clone_error": {"terminal_clone_gain_std": 0.0},
    "no_ab_subphase_errors": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "no_charge_injection": {"edge_charge_injection_std": 0.0},
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
    "older_background_only": {
        "edge_gain_cv": 0.0,
        "self_gain_cv": 0.0,
        "terminal_clone_gain_std": 0.0,
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "edge_charge_injection_std": 0.0,
        "prev_ratio_error_std": 0.0,
        "error_dac_sign_asymmetry": 0.0,
        "lcc_curvature": 0.0,
        "credit_accumulator_leakage": 0.0,
    },
}


def summarize(runs):
    imp = [r["improvement"] for r in runs]
    gaps = [r["placement_gap"] for r in runs]
    return {
        "n_improve_ge_0p10": sum(v >= 0.10 for v in imp),
        "final_wins": sum(r["final_win"] for r in runs),
        "median_improvement": statistics.median(imp),
        "median_gap": statistics.median(gaps),
        "min_improvement": min(imp),
        "max_improvement": max(imp),
    }


def main():
    tasks = {s: compile_temporal_order_task(s) for s in SEEDS}
    report = {"experiment": "tw1a-circuit-native-corner-diagnose-v01", "seeds": SEEDS, "cases": {}}

    for name, overrides in CASES.items():
        runs = []
        print(f"\n=== {name} ===", flush=True)
        for seed in SEEDS:
            cfg = replace(config_for(seed), **overrides)
            result, gain = run_order_contrast_training(
                tasks[seed], cfg, iterations=30, step_size=0.20
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
            runs.append(row)
        summary = summarize(runs)
        print(name, summary, flush=True)
        report["cases"][name] = {"overrides": overrides, "summary": summary, "runs": runs}

    Path("circuit-native-corner-diagnose-v01.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
