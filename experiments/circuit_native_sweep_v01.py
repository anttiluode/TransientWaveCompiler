"""Run the preregistered TW-1A v0.2 circuit-native one-axis sweeps.

The grids and qualification predicate are frozen in
``docs/CIRCUIT_NATIVE_SWEEP_PREREG_V01.md``.  This script records failures; a
failed hardware qualification is data, not a process exit failure.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator import (
    TW1ACircuitEmulatorConfig,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1110, 1115))
ITERATIONS = 25
STEP_SIZE = 0.20

GRIDS = {
    "edge_gain_cv": [0, .001, .003, .01, .03, .10, .30],
    "self_gain_cv": [0, .001, .003, .01, .03, .10, .30],
    "terminal_clone_gain_std": [0, .001, .003, .01, .03, .10, .30],
    "edge_settling_error": [0, .0001, .0003, .001, .003, .01, .03, .10, .30],
    "ab_edge_memory": [0, .0001, .0003, .001, .003, .01, .03, .10, .30],
    "edge_charge_injection_std": [
        0, 1e-9, 3e-9, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6,
        3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3,
    ],
    "prev_ratio_error_std": [0, .0001, .0003, .001, .003, .01, .03, .10, .30],
    "error_dac_sign_asymmetry": [0, .0001, .0003, .001, .003, .01, .03, .10, .30],
    "lcc_curvature": [0, .001, .003, .01, .03, .10, .30, 1.0, 3.0],
    "credit_accumulator_leakage": [0, 1e-5, 3e-5, 1e-4, 3e-4, .001, .003, .01, .03],
}


def base_config(seed: int) -> TW1ACircuitEmulatorConfig:
    return TW1ACircuitEmulatorConfig(
        weight_bits=8,
        self_bits=12,
        dac_bits=8,
        error_dac_bits=10,
        adc_bits=8,
        state_noise_std=0.0,
        state_full_scale=20.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        adc_full_scale=2.0,
        seed=50_000 + seed,
    )


def summarize_runs(runs):
    improvements = [float(r["improvement"]) for r in runs]
    gaps = [float(r["placement_gap"]) for r in runs]
    final_wins = sum(bool(r["final_win"]) for r in runs)
    qualify = (
        sum(v >= 0.10 for v in improvements) >= 4
        and statistics.median(improvements) >= 0.20
        and final_wins >= 4
        and statistics.median(gaps) > 0.0
    )
    return {
        "qualified": bool(qualify),
        "improve_ge_0p10": int(sum(v >= 0.10 for v in improvements)),
        "final_wins": int(final_wins),
        "median_improvement": float(statistics.median(improvements)),
        "median_placement_gap": float(statistics.median(gaps)),
        "min_improvement": float(min(improvements)),
        "min_placement_gap": float(min(gaps)),
    }


def classify_axis(points):
    flags = [bool(p["summary"]["qualified"]) for p in points]
    if not flags or not flags[0]:
        return {
            "status": "baseline_failed",
            "measured_boundary": None,
            "recommendation": None,
        }

    first_fail = next((i for i, ok in enumerate(flags) if not ok), None)
    if first_fail is None:
        vals = [p["value"] for p in points]
        recommendation = vals[-2] if len(vals) >= 2 else vals[-1]
        return {
            "status": "no_failure_in_grid",
            "measured_boundary": {"lower_bound": vals[-1]},
            "recommendation": recommendation,
        }

    if any(flags[first_fail + 1:]):
        return {
            "status": "nonmonotone",
            "measured_boundary": None,
            "recommendation": None,
        }

    last_pass = points[first_fail - 1]["value"] if first_fail > 0 else None
    recommendation = points[first_fail - 2]["value"] if first_fail >= 2 else last_pass
    return {
        "status": "monotone_failure",
        "measured_boundary": {
            "largest_qualified": last_pass,
            "first_failed": points[first_fail]["value"],
        },
        "recommendation": recommendation,
    }


def main() -> None:
    tasks = {seed: compile_temporal_order_task(seed) for seed in SEEDS}
    report = {
        "experiment": "tw1a-circuit-native-sweep-v01",
        "preregistration": "docs/CIRCUIT_NATIVE_SWEEP_PREREG_V01.md",
        "seeds": SEEDS,
        "iterations": ITERATIONS,
        "step_size": STEP_SIZE,
        "reference_config": asdict(base_config(SEEDS[0])),
        "axes": {},
    }

    for axis, grid in GRIDS.items():
        print(f"\n=== {axis} ===", flush=True)
        points = []
        for value in grid:
            runs = []
            for seed in SEEDS:
                cfg = replace(base_config(seed), **{axis: value})
                result, gain = run_order_contrast_training(
                    tasks[seed],
                    cfg,
                    iterations=ITERATIONS,
                    step_size=STEP_SIZE,
                )
                runs.append(
                    {
                        "seed": seed,
                        "sense_gain": gain,
                        "improvement": result.exact_improvement,
                        "placement_gap": result.placement_gap,
                        "final_exact": result.exact_contrast[-1],
                        "final_shuffled": result.shuffled_contrast[-1],
                        "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
                    }
                )
            summary = summarize_runs(runs)
            point = {"value": value, "summary": summary, "runs": runs}
            points.append(point)
            print(
                f"{axis}={value:g} qualified={summary['qualified']} "
                f"n10={summary['improve_ge_0p10']}/5 wins={summary['final_wins']}/5 "
                f"median_dC={summary['median_improvement']:+.6f} "
                f"median_gap={summary['median_placement_gap']:+.6f} "
                f"min_dC={summary['min_improvement']:+.6f}",
                flush=True,
            )
        report["axes"][axis] = {
            "grid": grid,
            "points": points,
            "classification": classify_axis(points),
        }
        print("boundary", report["axes"][axis]["classification"], flush=True)

    out = Path("circuit-native-sweep-v01.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {out}", flush=True)


if __name__ == "__main__":
    main()
