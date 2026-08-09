"""Fixed-task v0.9 factorial with independent fabrication and dynamic-noise seeds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

from v09_fresh_corner import config_for as formal_config
from transientwave.circuit_emulator_v09_partitioned_rng import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


TASK_SEED = 2400
IDEAL_IMPROVEMENT = 0.864382
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fabrication-seed", type=int, required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(a.fabrication_seed)
    rows = []
    print(
        f"task={TASK_SEED} fabrication={a.fabrication_seed} "
        f"ideal_DeltaC={IDEAL_IMPROVEMENT:+.6f}",
        flush=True,
    )
    for dseed in DYNAMIC_SEEDS:
        result, gain = run_order_contrast_training(
            task,
            cfg,
            iterations=30,
            step_size=0.20,
            dynamic_seed=dseed,
        )
        improvement = float(result.exact_improvement)
        row = {
            "task_seed": TASK_SEED,
            "fabrication_seed": a.fabrication_seed,
            "dynamic_seed": dseed,
            "sense_gain": gain,
            "improvement": improvement,
            "placement_gap": float(result.placement_gap),
            "final_exact": float(result.exact_contrast[-1]),
            "final_shuffled": float(result.shuffled_contrast[-1]),
            "final_win": bool(result.exact_contrast[-1] > result.shuffled_contrast[-1]),
            "hardware_over_ideal_improvement": float(improvement / IDEAL_IMPROVEMENT),
        }
        rows.append(row)
        print(
            f"  dyn={dseed}: DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"hw/ideal={row['hardware_over_ideal_improvement']:.3f}",
            flush=True,
        )

    imp = [r["improvement"] for r in rows]
    ratio = [r["hardware_over_ideal_improvement"] for r in rows]
    summary = {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(r["final_win"] for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "maximum_improvement": float(max(imp)),
        "median_hw_over_ideal": float(statistics.median(ratio)),
        "minimum_hw_over_ideal": float(min(ratio)),
        "maximum_hw_over_ideal": float(max(ratio)),
    }
    print("summary", summary, flush=True)
    out = {
        "experiment": "v09-separated-seed-axis-factorial",
        "preregistration": "docs/BENCHMARK_V09_SEED_AXIS_FACTORIAL_PREREG.md",
        "status": "diagnostic",
        "task_seed": TASK_SEED,
        "ideal_improvement": IDEAL_IMPROVEMENT,
        "fabrication_seed": a.fabrication_seed,
        "dynamic_seeds": DYNAMIC_SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v09-seed-axis-factorial-fab{a.fabrication_seed}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
