"""Complete-gradient averaging at the failed combined b=2e-5 v0.8 corner."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for as qualified_config
from transientwave.circuit_emulator_v08_self_thermal import (
    CommonDiffSelfThermalInterpreter,
    _make_pair,
    copy_circuit_disorder,
)
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.emulator import _rms


SEEDS = list(range(2300, 2310))
REPEATS = [1, 2, 4, 8]
B = 2e-5


def config_for(seed: int):
    return replace(
        qualified_config(seed),
        edge_ktc_base_fraction=B,
        self_ktc_base_fraction=B,
    )


def run_averaged_training(task, cfg, repeats: int, *, iterations: int = 30, step_size: float = 0.20):
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = CommonDiffSelfThermalInterpreter(exact_t)
    edi = CommonDiffSelfThermalInterpreter(exact_d)
    sti = CommonDiffSelfThermalInterpreter(shuffle_t)
    sdi = CommonDiffSelfThermalInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    exact_contrast = [c0]
    shuffled_contrast = [sc0]
    gradient_rms = []
    perm = np.random.default_rng(1729).permutation(len(exact_t.theta))

    for _ in range(int(iterations)):
        grads = []
        for _rep in range(int(repeats)):
            rt = eti.execute(stochastic_forward=True)
            rd = edi.execute(stochastic_forward=True)
            grads.append(
                contrast_gradient(
                    float(rt["objective"]),
                    float(rd["objective"]),
                    np.asarray(rt["credits"], dtype=float),
                    np.asarray(rd["credits"], dtype=float),
                )
            )
        gc = np.mean(np.asarray(grads, dtype=float), axis=0)
        gradient_rms.append(_rms(gc))

        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=True)
        _sync_theta(exact_t, exact_d)
        shuffle_t.apply_credits(-gc[perm], step_size=step_size, normalize_rms=True)
        _sync_theta(shuffle_t, shuffle_d)

        etv, edv, cv = _eval_pair(eti, edi)
        stv, sdv, scv = _eval_pair(sti, sdi)
        exact_contrast.append(cv)
        shuffled_contrast.append(scv)

    return {
        "sense_gain": gain,
        "initial_exact": exact_contrast[0],
        "final_exact": exact_contrast[-1],
        "final_shuffled": shuffled_contrast[-1],
        "improvement": exact_contrast[-1] - exact_contrast[0],
        "placement_gap": exact_contrast[-1] - shuffled_contrast[-1],
        "final_win": exact_contrast[-1] > shuffled_contrast[-1],
        "mean_update_gradient_rms": float(np.mean(gradient_rms)),
        "final_theta": exact_t.theta.tolist(),
    }


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "clean": bool(n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25),
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": med_gap,
        "minimum_placement_gap": float(min(gaps)),
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v08-complete-gradient-averaging-at-b2e-5",
        "preregistration": "docs/CIRCUIT_V08_GRADIENT_AVERAGING_PREREG.md",
        "status": "diagnostic-only-spent-2300-2309",
        "seeds": SEEDS,
        "edge_b": B,
        "self_b": B,
        "conditions": [],
    }

    for m in REPEATS:
        print(f"M={m}", flush=True)
        rows=[]
        for seed in SEEDS:
            row = {"seed": seed, **run_averaged_training(compile_temporal_order_task(seed), config_for(seed), m)}
            rows.append(row)
            print(
                f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} "
                f"win={row['final_win']} gradRMS={row['mean_update_gradient_rms']:.3e}",
                flush=True,
            )
        s=summarize(rows)
        print("  summary", s, flush=True)
        out["conditions"].append({"repeats":m,"summary":s,"runs":rows})

    clean=[c["repeats"] for c in out["conditions"] if c["summary"]["clean"]]
    out["decision"]={
        "clean_repeat_counts":clean,
        "minimum_clean_repeats":min(clean) if clean else None,
        "fresh_seed_authorized":False,
    }
    print("decision",out["decision"],flush=True)
    Path("v08-gradient-averaging-sweep.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
