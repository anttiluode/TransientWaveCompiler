"""Fixed task/fabrication v0.9 thermal-source factorial with partitioned RNGs."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_seed2400_switch_interaction import scale_switch_residuals
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_partitioned_rng import (
    PartitionedRNGInterpreter,
    TW1APartitionedRNGTile,
    copy_circuit_disorder,
)
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient


TASK_SEED = 2400
FABRICATION_SEED = 2400
IDEAL_IMPROVEMENT = 0.864382
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]
B = 2e-5
CONDITIONS = {
    "none": (False, False, False),
    "edge": (True, False, False),
    "self": (False, True, False),
    "drift": (False, False, True),
    "edge_self": (True, True, False),
    "edge_drift": (True, False, True),
    "self_drift": (False, True, True),
    "all": (True, True, True),
}


def make_four(task, cfg, gain):
    et = TW1APartitionedRNGTile(task["target"], cfg, sense_gain=gain)
    ed = TW1APartitionedRNGTile(
        task["distractor"], replace(cfg, seed=int(cfg.seed) + 1), sense_gain=gain
    )
    copy_circuit_disorder(et, ed)
    _sync_theta(et, ed)

    scfg = replace(cfg, seed=int(cfg.seed) + 100_003)
    st = TW1APartitionedRNGTile(task["target"], scfg, sense_gain=gain)
    sd = TW1APartitionedRNGTile(
        task["distractor"], replace(scfg, seed=int(scfg.seed) + 1), sense_gain=gain
    )
    copy_circuit_disorder(et, st)
    copy_circuit_disorder(et, sd)
    _sync_theta(et, st)
    _sync_theta(et, sd)
    return et, ed, st, sd


def configure_after_construction(tile, condition, dynamic_seed, role):
    # Remove only switch residuals after the exact formal silicon has been
    # constructed. This prevents fabrication RNG redraws.
    scale_switch_residuals(tile, 0.0)
    edge_on, self_on, drift_on = CONDITIONS[condition]
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=B if edge_on else 0.0,
        self_ktc_base_fraction=B if self_on else 0.0,
        drift_ktc_base_fraction=B if drift_on else 0.0,
    )
    tile.reseed_dynamic_streams(int(dynamic_seed) * 16 + int(role))


def run_once(task, cfg, gain, condition, dynamic_seed):
    et, ed, st, sd = make_four(task, cfg, gain)
    for role, tile in enumerate((et, ed, st, sd)):
        configure_after_construction(tile, condition, dynamic_seed, role)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)
    _, _, c0 = _eval_pair(eti, edi)
    _, _, sc0 = _eval_pair(sti, sdi)
    exact = [c0]
    shuffled = [sc0]
    perm = np.random.default_rng(1729).permutation(len(et.theta))

    for _ in range(30):
        rt = eti.execute(stochastic_forward=True)
        rd = edi.execute(stochastic_forward=True)
        gc = contrast_gradient(
            float(rt["objective"]),
            float(rd["objective"]),
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
        )
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
        "improvement": improvement,
        "placement_gap": float(exact[-1] - shuffled[-1]),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
        "hardware_over_ideal_improvement": float(improvement / IDEAL_IMPROVEMENT),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    gain = recommend_sense_gain(task, cfg)
    rows = []
    print(
        f"task={TASK_SEED} fab={FABRICATION_SEED} condition={a.condition} PGA={gain:g}",
        flush=True,
    )
    for dseed in DYNAMIC_SEEDS:
        row = run_once(task, cfg, gain, a.condition, dseed)
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
    }
    print("summary", summary, flush=True)
    out = {
        "experiment": "v09-partitioned-thermal-source-factorial",
        "preregistration": "docs/BENCHMARK_V09_THERMAL_FACTORIAL_PREREG.md",
        "status": "diagnostic",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "condition": a.condition,
        "thermal_factors": CONDITIONS[a.condition],
        "dynamic_seeds": DYNAMIC_SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v09-thermal-factorial-{a.condition}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
