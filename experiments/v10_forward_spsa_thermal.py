"""Forward-only SPSA on partitioned TW-1A v0.9 at b=2e-5."""
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
from v10_forward_spsa_clean import forward_contrast, set_theta
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_partitioned_rng import PartitionedRNGInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta


TASK_SEED = 2400
FABRICATION_SEED = 2400
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]
DIRECTION_SEEDS = [9100, 9101, 9102]
C = 1.0
STEP_SIZE = 0.40
ITERATIONS = 30
B = 2e-5
SHUFFLE_SEED = 1729


def configure_thermal(tile, dynamic_seed: int, role: int) -> None:
    scale_switch_residuals(tile, 0.0)
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=B,
        self_ktc_base_fraction=B,
        drift_ktc_base_fraction=B,
    )
    tile.reseed_dynamic_streams(int(dynamic_seed) * 16 + int(role))


def run_once(task, cfg, gain: float, dynamic_seed: int, direction_seed: int) -> dict:
    et, ed, st, sd = make_four(task, cfg, gain)
    configure_thermal(et, dynamic_seed, 0)
    configure_thermal(ed, dynamic_seed, 1)
    # Shuffled arm is never used for stochastic measurement; configure the same
    # physical point for deterministic placement-control evaluation only.
    configure_thermal(st, dynamic_seed, 2)
    configure_thermal(sd, dynamic_seed, 3)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)
    _, _, c0 = _eval_pair(eti, edi)
    _, _, sc0 = _eval_pair(sti, sdi)
    exact = [float(c0)]
    shuffled = [float(sc0)]

    rng = np.random.default_rng(int(direction_seed))
    perm = np.random.default_rng(SHUFFLE_SEED).permutation(len(et.theta))
    clipped_perturbations = 0
    measured_delta_c = []

    for _ in range(ITERATIONS):
        theta0 = et.theta.copy()
        delta = rng.choice(np.asarray([-1.0, 1.0]), size=len(theta0))
        plus = np.clip(theta0 + C * delta, et._theta_min, et._theta_max)
        minus = np.clip(theta0 - C * delta, et._theta_min, et._theta_max)
        clipped_perturbations += int(np.count_nonzero(np.abs((plus - minus) - 2.0 * C * delta) > 1e-12))

        set_theta(et, plus)
        _sync_theta(et, ed)
        _, _, cplus = forward_contrast(eti, edi, stochastic=True)

        set_theta(et, minus)
        _sync_theta(et, ed)
        _, _, cminus = forward_contrast(eti, edi, stochastic=True)

        set_theta(et, theta0)
        _sync_theta(et, ed)
        diff = float(cplus) - float(cminus)
        measured_delta_c.append(diff)
        g = (diff / (2.0 * C)) * delta

        et.apply_credits(-g, step_size=STEP_SIZE, normalize_rms=True)
        _sync_theta(et, ed)
        st.apply_credits(-g[perm], step_size=STEP_SIZE, normalize_rms=True)
        _sync_theta(st, sd)

        _, _, cv = _eval_pair(eti, edi)
        _, _, sv = _eval_pair(sti, sdi)
        exact.append(float(cv))
        shuffled.append(float(sv))

    improvement = float(exact[-1] - exact[0])
    shuffled_improvement = float(shuffled[-1] - shuffled[0])
    return {
        "dynamic_seed": int(dynamic_seed),
        "direction_seed": int(direction_seed),
        "c": C,
        "step_size": STEP_SIZE,
        "iterations": ITERATIONS,
        "trainable_parameters": int(len(et.theta)),
        "training_forward_traversals": int(4 * ITERATIONS),
        "reverse_traversals": 0,
        "clipped_perturbation_coordinates": int(clipped_perturbations),
        "median_abs_measured_contrast_difference": float(statistics.median(abs(x) for x in measured_delta_c)),
        "improvement": improvement,
        "shuffled_improvement": shuffled_improvement,
        "placement_gap": float(improvement - shuffled_improvement),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dynamic-seed", type=int, choices=DYNAMIC_SEEDS, required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    gain = recommend_sense_gain(task, cfg)
    rows = []
    print(f"task={TASK_SEED} fab={FABRICATION_SEED} dyn={a.dynamic_seed} c={C:g} step={STEP_SIZE:g} b={B:g} PGA={gain:g}", flush=True)
    for rseed in DIRECTION_SEEDS:
        row = run_once(task, cfg, gain, int(a.dynamic_seed), rseed)
        rows.append(row)
        print(
            f"  dir={rseed}: DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"|dCmeas|med={row['median_abs_measured_contrast_difference']:.6f}",
            flush=True,
        )

    imp = [r["improvement"] for r in rows]
    gaps = [r["placement_gap"] for r in rows]
    summary = {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(r["final_win"] for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "maximum_improvement": float(max(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "training_forward_traversals_per_run": int(4 * ITERATIONS),
        "reverse_traversals_per_run": 0,
    }
    print("summary", summary, flush=True)

    out = {
        "experiment": "v10-forward-only-spsa-small-cap-thermal",
        "preregistration": "docs/BENCHMARK_V10_FORWARD_SPSA_THERMAL_PREREG.md",
        "status": "spent-body thermal diagnostic",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "dynamic_seed": int(a.dynamic_seed),
        "direction_seeds": DIRECTION_SEEDS,
        "b": B,
        "c": C,
        "step_size": STEP_SIZE,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v10-forward-spsa-thermal-dyn{a.dynamic_seed}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
