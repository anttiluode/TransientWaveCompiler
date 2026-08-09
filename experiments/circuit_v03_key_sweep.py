"""Run preregistered TW-1A v0.3 calibrated/charge-balanced primitive sweeps."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator_v03 import (
    TW1ACircuitV03Config,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1250, 1255))
ITERATIONS = 25
STEP = 0.20

AXES = {
    "raw_self_gain_cv": {
        "field": "self_gain_cv",
        "grid": [0, .03, .10, .20, .30, .50],
        "fixed": {"self_calibration_error_std": 0.0},
    },
    "self_calibration_error_std": {
        "field": "self_calibration_error_std",
        "grid": [0, .0001, .0003, .001, .003, .01, .03],
        "fixed": {"self_gain_cv": .10},
    },
    "common_charge_injection": {
        "field": "edge_charge_injection_common_std",
        "grid": [0, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3],
        "fixed": {
            "self_gain_cv": .10,
            "self_calibration_error_std": 0.0,
            "edge_charge_injection_differential_std": 0.0,
        },
    },
    "differential_charge_injection": {
        "field": "edge_charge_injection_differential_std",
        "grid": [0, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4],
        "fixed": {
            "self_gain_cv": .10,
            "self_calibration_error_std": 0.0,
            "edge_charge_injection_common_std": 1e-4,
        },
    },
}


def base_config(seed):
    return TW1ACircuitV03Config(
        weight_bits=8,
        self_bits=12,
        dac_bits=8,
        error_dac_bits=10,
        adc_bits=8,
        state_full_scale=20.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        state_noise_std=0.0,
        credit_noise_fraction=0.0,
        credit_offset_fraction=0.0,
        edge_gain_cv=0.0,
        self_gain_cv=0.0,
        self_calibration=True,
        self_calibration_error_std=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        edge_settling_error=0.0,
        ab_edge_memory=0.0,
        edge_charge_injection_std=0.0,
        edge_charge_injection_common_std=0.0,
        edge_charge_injection_differential_std=0.0,
        prev_ratio_error_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        adc_full_scale=2.0,
        seed=80_000 + seed,
    )


def summary(rows):
    imp = [r["improvement"] for r in rows]
    gaps = [r["gap"] for r in rows]
    wins = sum(r["win"] for r in rows)
    ok = (
        sum(v >= .10 for v in imp) >= 4
        and statistics.median(imp) >= .20
        and wins >= 4
        and statistics.median(gaps) > 0
    )
    return {
        "qualified": ok,
        "n_improve_ge_0p10": sum(v >= .10 for v in imp),
        "final_wins": wins,
        "median_improvement": statistics.median(imp),
        "median_gap": statistics.median(gaps),
        "min_improvement": min(imp),
    }


def classify(points):
    flags = [p["summary"]["qualified"] for p in points]
    if not flags[0]:
        return {"status": "baseline_failed", "boundary": None, "recommendation": None}
    first_fail = next((i for i, x in enumerate(flags) if not x), None)
    if first_fail is None:
        vals = [p["value"] for p in points]
        return {
            "status": "no_failure_in_grid",
            "boundary": {"lower_bound": vals[-1]},
            "recommendation": vals[-2] if len(vals) > 1 else vals[-1],
        }
    if any(flags[first_fail + 1:]):
        return {"status": "nonmonotone", "boundary": None, "recommendation": None}
    vals = [p["value"] for p in points]
    return {
        "status": "monotone_failure",
        "boundary": {
            "largest_qualified": vals[first_fail - 1] if first_fail else None,
            "first_failed": vals[first_fail],
        },
        "recommendation": vals[first_fail - 2] if first_fail >= 2 else vals[first_fail - 1],
    }


def main():
    tasks = {s: compile_temporal_order_task(s) for s in SEEDS}
    report = {
        "experiment": "tw1a-v03-key-sweep",
        "preregistration": "docs/CIRCUIT_V03_KEY_SWEEP_PREREG.md",
        "seeds": SEEDS,
        "iterations": ITERATIONS,
        "step_size": STEP,
        "base_config": asdict(base_config(SEEDS[0])),
        "axes": {},
    }
    for axis_name, spec in AXES.items():
        print(f"\n=== {axis_name} ===", flush=True)
        points = []
        for value in spec["grid"]:
            rows = []
            for seed in SEEDS:
                cfg = replace(base_config(seed), **spec["fixed"], **{spec["field"]: value})
                result, gain = run_order_contrast_training(tasks[seed], cfg, iterations=ITERATIONS, step_size=STEP)
                rows.append({
                    "seed": seed,
                    "sense_gain": gain,
                    "improvement": result.exact_improvement,
                    "gap": result.placement_gap,
                    "final_exact": result.exact_contrast[-1],
                    "final_shuffled": result.shuffled_contrast[-1],
                    "win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
                })
            s = summary(rows)
            points.append({"value": value, "summary": s, "runs": rows})
            print(axis_name, value, s, flush=True)
        report["axes"][axis_name] = {
            "field": spec["field"],
            "fixed": spec["fixed"],
            "grid": spec["grid"],
            "points": points,
            "classification": classify(points),
        }
        print("classification", report["axes"][axis_name]["classification"], flush=True)
    Path("circuit-v03-key-sweep.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
