"""Full-basis forward-only Hadamard finite-difference learner for TW-1A v0.9."""
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
C = 1.0
STEP_SIZE = 0.40
ITERATIONS = 30
B = 2e-5
SHUFFLE_SEED = 1729
HADAMARD_N = 64
RCOND = 1e-10


def sylvester_hadamard(n: int) -> np.ndarray:
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError("Sylvester Hadamard order must be a positive power of two")
    h = np.ones((1, 1), dtype=float)
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h


def configure(tile, mode: str, dynamic_seed: int, role: int) -> None:
    scale_switch_residuals(tile, 0.0)
    b = 0.0 if mode == "clean" else B
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=b,
        self_ktc_base_fraction=b,
        drift_ktc_base_fraction=b,
    )
    tile.reseed_dynamic_streams(int(dynamic_seed) * 16 + int(role))


def run_once(task, cfg, gain: float, mode: str, dynamic_seed: int) -> dict:
    et, ed, st, sd = make_four(task, cfg, gain)
    for role, tile in enumerate((et, ed, st, sd)):
        configure(tile, mode, dynamic_seed, role)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)
    _, _, c0 = _eval_pair(eti, edi)
    _, _, sc0 = _eval_pair(sti, sdi)
    exact = [float(c0)]
    shuffled = [float(sc0)]

    p = len(et.theta)
    if p > HADAMARD_N:
        raise RuntimeError(f"{p} trainable parameters exceed {HADAMARD_N}-row basis")
    directions = sylvester_hadamard(HADAMARD_N)[:, :p]
    gram = directions.T @ directions
    np.testing.assert_allclose(gram, HADAMARD_N * np.eye(p), rtol=0.0, atol=0.0)

    perm = np.random.default_rng(SHUFFLE_SEED).permutation(p)
    ranks: list[int] = []
    conds: list[float] = []
    clipped_coords: list[int] = []
    measured_abs_diffs: list[float] = []
    stochastic = mode == "thermal"

    for update in range(ITERATIONS):
        theta0 = et.theta.copy()
        v = np.zeros((HADAMARD_N, p), dtype=float)
        d = np.zeros(HADAMARD_N, dtype=float)
        clipped = 0

        for r, direction in enumerate(directions):
            plus = np.clip(theta0 + C * direction, et._theta_min, et._theta_max)
            minus = np.clip(theta0 - C * direction, et._theta_min, et._theta_max)
            actual = 0.5 * (plus - minus)
            v[r] = actual
            clipped += int(np.count_nonzero(np.abs(actual - C * direction) > 1e-12))

            set_theta(et, plus)
            _sync_theta(et, ed)
            _, _, cplus = forward_contrast(eti, edi, stochastic=stochastic)

            set_theta(et, minus)
            _sync_theta(et, ed)
            _, _, cminus = forward_contrast(eti, edi, stochastic=stochastic)

            d[r] = 0.5 * (float(cplus) - float(cminus))
            measured_abs_diffs.append(abs(float(cplus) - float(cminus)))

        set_theta(et, theta0)
        _sync_theta(et, ed)

        rank = int(np.linalg.matrix_rank(v))
        cond = float(np.linalg.cond(v))
        ranks.append(rank)
        conds.append(cond)
        clipped_coords.append(clipped)
        if rank < p:
            raise RuntimeError(f"Hadamard measurement matrix lost rank at update {update}: {rank} < {p}")

        g, *_ = np.linalg.lstsq(v, d, rcond=RCOND)

        # apply_credits is a descent update; negate dC/dtheta to maximize contrast.
        et.apply_credits(-g, step_size=STEP_SIZE, normalize_rms=True)
        _sync_theta(et, ed)
        st.apply_credits(-g[perm], step_size=STEP_SIZE, normalize_rms=True)
        _sync_theta(st, sd)

        _, _, cv = _eval_pair(eti, edi)
        _, _, sv = _eval_pair(sti, sdi)
        exact.append(float(cv))
        shuffled.append(float(sv))
        print(
            f"  update={update+1:02d}: C={cv:+.6f} shuffled={sv:+.6f} "
            f"rank={rank} cond={cond:.3f} clipped={clipped}",
            flush=True,
        )

    improvement = float(exact[-1] - exact[0])
    shuffled_improvement = float(shuffled[-1] - shuffled[0])
    return {
        "mode": mode,
        "dynamic_seed": int(dynamic_seed),
        "c": C,
        "step_size": STEP_SIZE,
        "iterations": ITERATIONS,
        "hadamard_rows": HADAMARD_N,
        "trainable_parameters": p,
        "training_forward_traversals": int(HADAMARD_N * 4 * ITERATIONS),
        "reverse_traversals": 0,
        "minimum_measurement_rank": int(min(ranks)),
        "maximum_measurement_condition": float(max(conds)),
        "median_measurement_condition": float(statistics.median(conds)),
        "maximum_clipped_coordinates_per_update": int(max(clipped_coords)),
        "median_abs_measured_contrast_difference": float(statistics.median(measured_abs_diffs)),
        "improvement": improvement,
        "shuffled_improvement": shuffled_improvement,
        "placement_gap": float(improvement - shuffled_improvement),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["clean", "thermal"], required=True)
    ap.add_argument("--dynamic-seed", type=int, default=8000)
    a = ap.parse_args()
    if a.mode == "thermal" and int(a.dynamic_seed) not in DYNAMIC_SEEDS:
        raise SystemExit(f"thermal dynamic seed must be one of {DYNAMIC_SEEDS}")

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    gain = recommend_sense_gain(task, cfg)
    row = run_once(task, cfg, gain, a.mode, int(a.dynamic_seed))
    print("summary", row, flush=True)

    out = {
        "experiment": "v10-forward-hadamard-small-cap-thermal",
        "preregistration": "docs/BENCHMARK_V10_FORWARD_HADAMARD_THERMAL_PREREG.md",
        "status": "spent-body estimator test",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "sense_gain": float(gain),
        "result": row,
    }
    Path(f"v10-forward-hadamard-{a.mode}-dyn{a.dynamic_seed}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
