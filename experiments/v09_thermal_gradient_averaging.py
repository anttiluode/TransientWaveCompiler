"""Complete-gradient averaging at the partitioned v0.9 b=2e-5 point."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_partitioned_thermal_factorial import make_four
from v09_seed2400_switch_interaction import scale_switch_residuals
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_partitioned_rng import PartitionedRNGInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient


TASK_SEED = 2400
FABRICATION_SEED = 2400
IDEAL_IMPROVEMENT = 0.864382
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]
B = 2e-5
N_GRID = [1, 4, 16, 64]


def configure(tile, dynamic_seed: int, role: int) -> None:
    scale_switch_residuals(tile, 0.0)
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=B,
        self_ktc_base_fraction=B,
        drift_ktc_base_fraction=B,
    )
    tile.reseed_dynamic_streams(int(dynamic_seed) * 16 + int(role))


def run_once(task, cfg, gain: float, repeats: int, dynamic_seed: int) -> dict:
    et, ed, st, sd = make_four(task, cfg, gain)
    for role, tile in enumerate((et, ed, st, sd)):
        configure(tile, dynamic_seed, role)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)
    _, _, c0 = _eval_pair(eti, edi)
    _, _, sc0 = _eval_pair(sti, sdi)
    exact = [c0]
    shuffled = [sc0]
    perm = np.random.default_rng(1729).permutation(len(et.theta))

    for _ in range(30):
        gc_sum = np.zeros(len(et.theta), dtype=float)
        for _rep in range(int(repeats)):
            rt = eti.execute(stochastic_forward=True)
            rd = edi.execute(stochastic_forward=True)
            gc_sum += contrast_gradient(
                float(rt["objective"]),
                float(rd["objective"]),
                np.asarray(rt["credits"], dtype=float),
                np.asarray(rd["credits"], dtype=float),
            )
        gc = gc_sum / float(repeats)

        et.apply_credits(-gc, step_size=0.20, normalize_rms=True)
        _sync_theta(et, ed)
        st.apply_credits(-gc[perm], step_size=0.20, normalize_rms=True)
        _sync_theta(st, sd)

        _, _, cv = _eval_pair(eti, edi)
        _, _, sv = _eval_pair(sti, sdi)
        exact.append(cv)
        shuffled.append(sv)

    improvement = float(exact[-1] - exact[0])
    return {
        "dynamic_seed": int(dynamic_seed),
        "repeats": int(repeats),
        "physical_gradient_acquisition_multiplier": int(repeats),
        "improvement": improvement,
        "placement_gap": float(exact[-1] - shuffled[-1]),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
        "hardware_over_ideal_improvement": float(improvement / IDEAL_IMPROVEMENT),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, choices=N_GRID, required=True)
    a = ap.parse_args()
    repeats = int(a.repeats)

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    gain = recommend_sense_gain(task, cfg)
    rows = []
    print(
        f"task={TASK_SEED} fab={FABRICATION_SEED} b={B:g} repeats={repeats} PGA={gain:g}",
        flush=True,
    )
    for dseed in DYNAMIC_SEEDS:
        row = run_once(task, cfg, gain, repeats, dseed)
        rows.append(row)
        print(
            f"  dyn={dseed}: DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"hw/ideal={row['hardware_over_ideal_improvement']:.3f}",
            flush=True,
        )

    imp = [r["improvement"] for r in rows]
    gaps = [r["placement_gap"] for r in rows]
    ratios = [r["hardware_over_ideal_improvement"] for r in rows]
    summary = {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(r["final_win"] for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "maximum_improvement": float(max(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "median_hw_over_ideal": float(statistics.median(ratios)),
        "minimum_hw_over_ideal": float(min(ratios)),
    }
    summary["robust"] = bool(
        summary["improve_ge_0p10"] == 5
        and summary["final_wins"] == 5
        and summary["median_improvement"] >= 0.30
        and summary["median_placement_gap"] >= 0.25
    )
    print("summary", summary, flush=True)

    out = {
        "experiment": "v09-partitioned-complete-gradient-thermal-averaging",
        "preregistration": "docs/BENCHMARK_V09_THERMAL_GRADIENT_AVERAGING_PREREG.md",
        "status": "spent-body diagnostic",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "b": B,
        "repeats": repeats,
        "dynamic_seeds": DYNAMIC_SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v09-thermal-gradient-avg-n{repeats}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
