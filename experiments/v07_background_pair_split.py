"""Controlled pair split of strongest v0.7 background interactions."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from v07_background_split import _apply_condition, _formal_no_thermal
from transientwave.circuit_emulator_v07_active_summing import (
    ActiveSummingLockstepInterpreter,
    _eval_pair,
    _make_pair,
    copy_circuit_disorder,
    recommend_sense_gain,
)
from transientwave.emulator import _rms
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_gradient,
)


SEEDS = list(range(2000, 2010))
TAIL = {2006, 2007, 2008}
PAIRS = (
    ("perfect_terminal_clone", "perfect_switch_kick"),
    ("perfect_terminal_clone", "perfect_error_sign"),
    ("perfect_terminal_clone", "perfect_credit_readout"),
    ("perfect_switch_kick", "perfect_error_sign"),
    ("perfect_switch_kick", "perfect_credit_readout"),
    ("perfect_error_sign", "perfect_credit_readout"),
)


def _train(task, cfg, pair, *, iterations=30, step_size=0.20):
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    for tile in (exact_t, exact_d, shuffle_t, shuffle_d):
        for condition in pair:
            _apply_condition(tile, condition)
    _sync_theta(exact_t, exact_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = ActiveSummingLockstepInterpreter(exact_t)
    edi = ActiveSummingLockstepInterpreter(exact_d)
    sti = ActiveSummingLockstepInterpreter(shuffle_t)
    sdi = ActiveSummingLockstepInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    exact_contrast = [c0]
    shuffled_contrast = [sc0]
    exact_target_energy = [et0]
    exact_distractor_energy = [ed0]
    shuffled_target_energy = [st0]
    shuffled_distractor_energy = [sd0]
    measured_t = []
    measured_d = []
    credit_rms = []
    perm = np.random.default_rng(1729).permutation(len(exact_t.theta))

    for _ in range(iterations):
        rt = eti.execute(stochastic_forward=True)
        rd = edi.execute(stochastic_forward=True)
        et = float(rt["objective"])
        ed = float(rd["objective"])
        gc = contrast_gradient(
            et,
            ed,
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
            eps=1e-30,
        )
        measured_t.append(et)
        measured_d.append(ed)
        credit_rms.append(_rms(gc))
        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=True)
        _sync_theta(exact_t, exact_d)
        shuffle_t.apply_credits(-gc[perm], step_size=step_size, normalize_rms=True)
        _sync_theta(shuffle_t, shuffle_d)
        etv, edv, cv = _eval_pair(eti, edi)
        stv, sdv, scv = _eval_pair(sti, sdi)
        exact_target_energy.append(etv)
        exact_distractor_energy.append(edv)
        exact_contrast.append(cv)
        shuffled_target_energy.append(stv)
        shuffled_distractor_energy.append(sdv)
        shuffled_contrast.append(scv)

    return OrderContrastTrainingResult(
        exact_contrast=exact_contrast,
        shuffled_contrast=shuffled_contrast,
        exact_target_energy=exact_target_energy,
        exact_distractor_energy=exact_distractor_energy,
        shuffled_target_energy=shuffled_target_energy,
        shuffled_distractor_energy=shuffled_distractor_energy,
        measured_target_energy=measured_t,
        measured_distractor_energy=measured_d,
        combined_credit_rms=credit_rms,
        final_theta=exact_t.theta.copy(),
        final_theta_shuffled=shuffle_t.theta.copy(),
    ), gain


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    return {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(bool(r["final_win"]) for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "tail": {
            str(r["seed"]): {
                "improvement": r["improvement"],
                "placement_gap": r["placement_gap"],
                "final_win": r["final_win"],
            }
            for r in rows if r["seed"] in TAIL
        },
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v07-controlled-background-pair-split",
        "status": "diagnostic-only-spent-2000-2009",
        "preregistration": "docs/CIRCUIT_V07_BACKGROUND_PAIR_PREREG.md",
        "conditions": [],
    }
    for pair in PAIRS:
        name = "+".join(pair)
        print(name, flush=True)
        rows = []
        for seed in SEEDS:
            result, gain = _train(
                compile_temporal_order_task(seed), _formal_no_thermal(seed), pair
            )
            row = {
                "seed": seed,
                "sense_gain": gain,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            }
            rows.append(row)
            print(
                f"  {seed}: DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} win={row['final_win']}",
                flush=True,
            )
        s = summarize(rows)
        print("  summary", s, flush=True)
        out["conditions"].append({"pair": list(pair), "summary": s, "runs": rows})

    Path("v07-background-pair-split.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
