"""Clean forward-only SPSA calibration on spent task/fabrication 2400."""
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
from transientwave.order_contrast import _sync_theta, contrast_from_energies


TASK_SEED = 2400
FABRICATION_SEED = 2400
DIRECTION_SEEDS = [9100, 9101, 9102]
C_GRID = [0.25, 0.5, 1.0, 2.0]
STEP_GRID = [0.10, 0.20, 0.40]
ITERATIONS = 30
SHUFFLE_SEED = 1729


def set_theta(tile, theta: np.ndarray) -> None:
    tile.theta = np.asarray(theta, dtype=float).copy()
    tile._rebuild_programmed_Q()


def configure_clean(tile) -> None:
    scale_switch_residuals(tile, 0.0)
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=0.0,
        self_ktc_base_fraction=0.0,
        drift_ktc_base_fraction=0.0,
    )


def forward_objective(interp: PartitionedRNGInterpreter, *, stochastic: bool = False) -> float:
    interp._run_forward(stochastic=stochastic)
    return float(interp._objective())


def forward_contrast(
    ti: PartitionedRNGInterpreter,
    di: PartitionedRNGInterpreter,
    *,
    stochastic: bool = False,
) -> tuple[float, float, float]:
    et = forward_objective(ti, stochastic=stochastic)
    ed = forward_objective(di, stochastic=stochastic)
    return et, ed, contrast_from_energies(et, ed)


def run_once(task, cfg, gain: float, c: float, step_size: float, direction_seed: int) -> dict:
    et, ed, st, sd = make_four(task, cfg, gain)
    for tile in (et, ed, st, sd):
        configure_clean(tile)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)

    _, _, c0 = _eval_pair(eti, edi)
    _, _, sc0 = _eval_pair(sti, sdi)
    exact = [float(c0)]
    shuffled = [float(sc0)]

    rng = np.random.default_rng(int(direction_seed))
    perm = np.random.default_rng(SHUFFLE_SEED).permutation(len(et.theta))
    clipped_perturbations = 0

    for _ in range(ITERATIONS):
        theta0 = et.theta.copy()
        delta = rng.choice(np.asarray([-1.0, 1.0]), size=len(theta0))
        plus = np.clip(theta0 + float(c) * delta, et._theta_min, et._theta_max)
        minus = np.clip(theta0 - float(c) * delta, et._theta_min, et._theta_max)
        clipped_perturbations += int(np.count_nonzero(np.abs((plus - minus) - 2.0 * float(c) * delta) > 1e-12))

        set_theta(et, plus)
        _sync_theta(et, ed)
        _, _, cplus = forward_contrast(eti, edi, stochastic=False)

        set_theta(et, minus)
        _sync_theta(et, ed)
        _, _, cminus = forward_contrast(eti, edi, stochastic=False)

        set_theta(et, theta0)
        _sync_theta(et, ed)
        g = ((float(cplus) - float(cminus)) / (2.0 * float(c))) * delta

        # apply_credits is a descent update; negate dC/dtheta to maximize contrast.
        et.apply_credits(-g, step_size=float(step_size), normalize_rms=True)
        _sync_theta(et, ed)
        st.apply_credits(-g[perm], step_size=float(step_size), normalize_rms=True)
        _sync_theta(st, sd)

        _, _, cv = _eval_pair(eti, edi)
        _, _, sv = _eval_pair(sti, sdi)
        exact.append(float(cv))
        shuffled.append(float(sv))

    improvement = float(exact[-1] - exact[0])
    shuffled_improvement = float(shuffled[-1] - shuffled[0])
    return {
        "direction_seed": int(direction_seed),
        "c": float(c),
        "step_size": float(step_size),
        "iterations": ITERATIONS,
        "trainable_parameters": int(len(et.theta)),
        "training_forward_traversals": int(4 * ITERATIONS),
        "reverse_traversals": 0,
        "clipped_perturbation_coordinates": int(clipped_perturbations),
        "improvement": improvement,
        "shuffled_improvement": shuffled_improvement,
        "placement_gap": float(improvement - shuffled_improvement),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c", type=float, choices=C_GRID, required=True)
    ap.add_argument("--step-size", type=float, choices=STEP_GRID, required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    gain = recommend_sense_gain(task, cfg)
    rows = []
    print(f"task={TASK_SEED} fab={FABRICATION_SEED} c={a.c:g} step={a.step_size:g} PGA={gain:g}", flush=True)
    for dseed in DIRECTION_SEEDS:
        row = run_once(task, cfg, gain, float(a.c), float(a.step_size), dseed)
        rows.append(row)
        print(
            f"  dir={dseed}: DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"clipcoords={row['clipped_perturbation_coordinates']}",
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
    summary["clean_viable"] = bool(
        summary["improve_ge_0p10"] == len(DIRECTION_SEEDS)
        and summary["final_wins"] == len(DIRECTION_SEEDS)
        and summary["median_improvement"] >= 0.30
        and summary["median_placement_gap"] >= 0.20
    )
    print("summary", summary, flush=True)

    ctag = str(a.c).replace(".", "p")
    stag = str(a.step_size).replace(".", "p")
    out = {
        "experiment": "v10-forward-only-spsa-clean-calibration",
        "preregistration": "docs/BENCHMARK_V10_FORWARD_SPSA_CLEAN_PREREG.md",
        "status": "spent-body algorithm calibration",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "c": float(a.c),
        "step_size": float(a.step_size),
        "direction_seeds": DIRECTION_SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v10-forward-spsa-clean-c{ctag}-s{stag}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
