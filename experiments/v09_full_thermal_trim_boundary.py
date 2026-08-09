"""Full-thermal switch-residual boundary on spent v0.9 bodies 2400..2409."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_seed2400_static_split import make_four
from v09_seed2400_switch_interaction import scale_switch_residuals, audit as residual_audit
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_drift_kick import DriftKickInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient


SEEDS = list(range(2400, 2410))
SCALES = {
    "s000": 0.000,
    "s025": 0.025,
    "s050": 0.050,
    "s075": 0.075,
    "s100": 0.100,
    "s150": 0.150,
    "s250": 0.250,
}
IDEAL_IMPROVEMENT = {
    2400: 0.864382,
    2401: 0.841869,
    2402: 0.555789,
    2403: 0.843161,
    2404: 0.993097,
    2405: 0.052904,
    2406: 0.744431,
    2407: 0.998321,
    2408: 0.757526,
    2409: 0.491374,
}
IDEAL_LEARNABLE = {s for s, v in IDEAL_IMPROVEMENT.items() if v >= 0.10}


def run_seed(seed: int, scale: float):
    task = compile_temporal_order_task(seed)
    cfg = formal_config(seed)
    gain = recommend_sense_gain(task, cfg)
    et, ed, st, sd = make_four(task, cfg, gain)
    for tile in (et, ed, st, sd):
        scale_switch_residuals(tile, scale)

    physical = residual_audit(et)
    eti, edi = DriftKickInterpreter(et), DriftKickInterpreter(ed)
    sti, sdi = DriftKickInterpreter(st), DriftKickInterpreter(sd)
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
    ideal = float(IDEAL_IMPROVEMENT[seed])
    return {
        "seed": seed,
        "sense_gain": gain,
        "physical": physical,
        "initial_exact": float(exact[0]),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "improvement": improvement,
        "placement_gap": float(exact[-1] - shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
        "ideal_improvement": ideal,
        "ideal_learnable": seed in IDEAL_LEARNABLE,
        "hardware_over_ideal_improvement": float(improvement / ideal),
    }


def summarize(rows):
    imp = [r["improvement"] for r in rows]
    gaps = [r["placement_gap"] for r in rows]
    eligible = [r for r in rows if r["ideal_learnable"]]
    ratios = [r["hardware_over_ideal_improvement"] for r in eligible]
    n_eligible = sum(r["improvement"] >= 0.10 for r in eligible)
    wins = sum(r["final_win"] for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "cohort_closed": bool(
            n_eligible == len(eligible)
            and wins == 10
            and med_imp >= 0.30
            and med_gap >= 0.25
        ),
        "ideal_learnable_count": len(eligible),
        "ideal_learnable_ge_0p10": n_eligible,
        "final_wins": wins,
        "historical_all10_ge_0p10": sum(x >= 0.10 for x in imp),
        "median_improvement": med_imp,
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": med_gap,
        "minimum_placement_gap": float(min(gaps)),
        "median_hw_over_ideal": float(statistics.median(ratios)),
        "minimum_hw_over_ideal": float(min(ratios)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", choices=sorted(SCALES), required=True)
    a = ap.parse_args()
    scale = SCALES[a.label]
    rows = []
    print(f"label={a.label} scale={scale:g}", flush=True)
    for seed in SEEDS:
        r = run_seed(seed, scale)
        rows.append(r)
        p = r["physical"]
        print(
            f"  {seed}: DeltaC={r['improvement']:+.6f} "
            f"gap={r['placement_gap']:+.6f} win={r['final_win']} "
            f"hw/ideal={r['hardware_over_ideal_improvement']:.3f} "
            f"edgeA={p['edge_a_rms_fraction']*1e6:.3f}ppm "
            f"edgeAB={p['edge_ab_diff_rms_fraction']*1e6:.3f}ppm "
            f"driftC={p['drift_c_rms_fraction']*1e6:.3f}ppm "
            f"driftCD={p['drift_cd_diff_rms_fraction']*1e6:.3f}ppm",
            flush=True,
        )
    summary = summarize(rows)
    print("summary", summary, flush=True)
    out = {
        "experiment": "v09-full-thermal-switch-residual-boundary",
        "preregistration": "docs/CIRCUIT_V09_FULL_THERMAL_TRIM_BOUNDARY_PREREG.md",
        "status": "spent-2400-2409-diagnostic",
        "label": a.label,
        "scale": scale,
        "seeds": SEEDS,
        "summary": summary,
        "runs": rows,
    }
    Path(f"v09-full-thermal-trim-{a.label}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
