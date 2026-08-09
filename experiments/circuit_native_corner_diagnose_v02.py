"""Second diagnostic on spent v0.1 corner bodies.

Every case removes the dominant lane-select charge-injection term, then removes
one additional error group.  This is diagnosis only; it cannot qualify a new
simultaneous corner.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task
from circuit_native_corner_v01 import SEEDS, config_for


BASE = {"edge_charge_injection_std": 0.0}
CASES = {
    "no_charge_only": {},
    "plus_no_old_background": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
    },
    "plus_no_edge_gain": {"edge_gain_cv": 0.0},
    "plus_no_self_gain": {"self_gain_cv": 0.0},
    "plus_no_prev_ratio": {"prev_ratio_error_std": 0.0},
    "plus_no_terminal_clone": {"terminal_clone_gain_std": 0.0},
    "plus_no_ab_subphase": {
        "edge_settling_error": 0.0,
        "ab_edge_memory": 0.0,
        "error_dac_sign_asymmetry": 0.0,
    },
    "plus_no_credit_path": {
        "lcc_curvature": 0.0,
        "credit_accumulator_leakage": 0.0,
        "credit_noise_fraction": 0.0,
        "credit_offset_fraction": 0.0,
    },
    "plus_no_state_storage": {
        "leakage_rate": 0.0,
        "leakage_cv": 0.0,
        "state_noise_std": 0.0,
        "prev_ratio_error_std": 0.0,
    },
    "plus_ideal_self_and_prev": {
        "self_gain_cv": 0.0,
        "prev_ratio_error_std": 0.0,
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
    report = {"experiment": "tw1a-circuit-native-corner-diagnose-v02", "seeds": SEEDS, "cases": {}}
    for name, extra in CASES.items():
        overrides = dict(BASE)
        overrides.update(extra)
        runs = []
        print(f"\n=== {name} ===", flush=True)
        for seed in SEEDS:
            cfg = replace(config_for(seed), **overrides)
            result, gain = run_order_contrast_training(tasks[seed], cfg, iterations=30, step_size=0.20)
            runs.append({
                "seed": seed,
                "sense_gain": gain,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            })
        s = summarize(runs)
        print(name, s, flush=True)
        report["cases"][name] = {"overrides": overrides, "summary": s, "runs": runs}
    Path("circuit-native-corner-diagnose-v02.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
