"""Diagnostic leave-group-out analysis of the failed v0.4 corner.

Bodies 1400-1409 are spent.  These cases are diagnostic only and cannot qualify
a revised hardware corner.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from experiments.circuit_v04_corner import SEEDS, config_for
from transientwave.circuit_emulator_v04 import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


CASES = {
    "full_failed_corner": {},
    "no_charge_residual": {
        "edge_charge_cancellation_error_std": 0.0,
        "edge_charge_residual_common_floor_std": 0.0,
        "edge_charge_residual_differential_floor_std": 0.0,
    },
    "perfect_edge_cal": {
        "edge_calibration_error_std": 0.0,
    },
    "perfect_self_cal": {
        "self_calibration_error_std": 0.0,
    },
    "perfect_prev_cal": {
        "prev_ratio_calibration_error_std": 0.0,
    },
    "perfect_clone_cal": {
        "terminal_clone_calibration_error_std": 0.0,
    },
    "perfect_all_gain_cal": {
        "edge_calibration_error_std": 0.0,
        "self_calibration_error_std": 0.0,
        "prev_ratio_calibration_error_std": 0.0,
        "terminal_clone_calibration_error_std": 0.0,
    },
    "no_lockstep_dynamic_error": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "ideal_credit_path": {
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
        "lcc_curvature": 0.0,
        "credit_accumulator_leakage": 0.0,
    },
    "no_old_background": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
    },
    "no_charge_plus_perfect_all_gain_cal": {
        "edge_charge_cancellation_error_std": 0.0,
        "edge_charge_residual_common_floor_std": 0.0,
        "edge_charge_residual_differential_floor_std": 0.0,
        "edge_calibration_error_std": 0.0,
        "self_calibration_error_std": 0.0,
        "prev_ratio_calibration_error_std": 0.0,
        "terminal_clone_calibration_error_std": 0.0,
    },
    "clean_quantized": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
        "edge_gain_cv": 0.0,
        "edge_calibration_error_std": 0.0,
        "self_gain_cv": 0.0,
        "self_calibration_error_std": 0.0,
        "terminal_clone_gain_std": 0.0,
        "terminal_clone_calibration_error_std": 0.0,
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "edge_charge_raw_common_std": 0.0,
        "edge_charge_raw_differential_std": 0.0,
        "edge_charge_cancellation_error_std": 0.0,
        "edge_charge_residual_common_floor_std": 0.0,
        "edge_charge_residual_differential_floor_std": 0.0,
        "prev_ratio_error_std": 0.0,
        "prev_ratio_calibration_error_std": 0.0,
        "error_dac_sign_asymmetry": 0.0,
        "lcc_curvature": 0.0,
        "credit_accumulator_leakage": 0.0,
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
        "experiment": "tw1a-v04-failed-corner-diagnostic",
        "status": "diagnostic-only-spent-bodies",
        "seeds": SEEDS,
        "cases": {},
    }
    for name, changes in CASES.items():
        rows = []
        print(f"CASE {name}", flush=True)
        for seed in SEEDS:
            cfg = replace(config_for(seed), **changes)
            result, gain = run_order_contrast_training(
                compile_temporal_order_task(seed),
                cfg,
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
            print(
                f"  seed={seed} DeltaC={row['improvement']:+.5f} "
                f"gap={row['placement_gap']:+.5f}",
                flush=True,
            )
        summary = summarize(rows)
        print("  summary", summary, flush=True)
        output["cases"][name] = {
            "changes": changes,
            "summary": summary,
            "runs": rows,
        }

    Path("circuit-v04-corner-diagnose.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
