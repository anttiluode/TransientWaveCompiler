"""Fixed task-2400 fabrication x dynamic-noise factorial for partitioned-RNG v0.9."""
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
FABRICATION_SEEDS = [2400, 2401, 2402, 2403, 2404]
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]


def run_once(task, fabrication_seed: int, dynamic_seed: int):
    cfg = formal_config(int(fabrication_seed))
    r, gain = run_order_contrast_training(
        task,
        cfg,
        iterations=30,
        step_size=0.20,
        normalize_rms=True,
        include_shuffle=True,
        dynamic_seed=int(dynamic_seed),
    )
    improvement = float(r.exact_improvement)
    return {
        "fabrication_seed": int(fabrication_seed),
        "dynamic_seed": int(dynamic_seed),
        "sense_gain": float(gain),
        "improvement": improvement,
        "placement_gap": float(r.placement_gap),
        "final_exact": float(r.exact_contrast[-1]),
        "final_shuffled": float(r.shuffled_contrast[-1]),
        "final_win": bool(r.exact_contrast[-1] > r.shuffled_contrast[-1]),
        "hardware_over_ideal_improvement": float(improvement / IDEAL_IMPROVEMENT),
    }


def summarize(rows):
    imp = [r["improvement"] for r in rows]
    gaps = [r["placement_gap"] for r in rows]
    ratios = [r["hardware_over_ideal_improvement"] for r in rows]
    return {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(r["final_win"] for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "maximum_improvement": float(max(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "median_hw_over_ideal": float(statistics.median(ratios)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fabrication-seed", type=int, choices=FABRICATION_SEEDS, required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    rows = []
    print(f"task={TASK_SEED} fabrication={a.fabrication_seed}", flush=True)
    for dseed in DYNAMIC_SEEDS:
        row = run_once(task, a.fabrication_seed, dseed)
        rows.append(row)
        print(
            f"  dyn={dseed}: DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"hw/ideal={row['hardware_over_ideal_improvement']:.3f}",
            flush=True,
        )

    summary = summarize(rows)
    print("summary", summary, flush=True)
    out = {
        "experiment": "v09-fixed-task-fabrication-dynamic-factorial",
        "preregistration": "docs/BENCHMARK_V09_FIXED_TASK_FACTORIAL_PREREG.md",
        "status": "diagnostic",
        "task_seed": TASK_SEED,
        "ideal_improvement": IDEAL_IMPROVEMENT,
        "fabrication_seed": int(a.fabrication_seed),
        "dynamic_seeds": DYNAMIC_SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v09-fixed-task-fab-{a.fabrication_seed}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
