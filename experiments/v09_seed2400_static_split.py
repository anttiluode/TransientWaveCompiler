"""Same-draw static/support split for failed fresh v0.9 seed 2400.

Every condition constructs the exact formal tile first, copies static disorder as
in the formal learner, then performs surgery.  Thermal sources are disabled only
after construction so fabrication RNG consumption is identical.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from v09_fresh_corner import config_for as formal_config
from transientwave.circuit_emulator_v05_segmented_mismatch import segmented_capacitance_codes
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_drift_kick import (
    DriftKickInterpreter,
    TW1ADriftKickTile,
    copy_circuit_disorder,
)
from transientwave.emulator import _rms
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient


SEED = 2400
CONDITIONS = [
    "thermal_zero_baseline",
    "no_drift_residual",
    "no_inherited_edge_kick",
    "no_state_leakage",
    "exact_edge_lane_holds",
    "exact_kick_self_gain",
    "ideal_edge_codebook",
    "ideal_converters",
    "ideal_credit_path",
    "all_support_clean",
]


def make_four(task, cfg, gain):
    exact_t = TW1ADriftKickTile(task["target"], cfg, sense_gain=gain)
    exact_d = TW1ADriftKickTile(task["distractor"], replace(cfg, seed=int(cfg.seed)+1), sense_gain=gain)
    copy_circuit_disorder(exact_t, exact_d)
    _sync_theta(exact_t, exact_d)

    scfg = replace(cfg, seed=int(cfg.seed)+100_003)
    shuffle_t = TW1ADriftKickTile(task["target"], scfg, sense_gain=gain)
    shuffle_d = TW1ADriftKickTile(task["distractor"], replace(scfg, seed=int(scfg.seed)+1), sense_gain=gain)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)
    return exact_t, exact_d, shuffle_t, shuffle_d


def thermal_zero(tile):
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=0.0,
        self_ktc_base_fraction=0.0,
        drift_ktc_base_fraction=0.0,
    )


def remove_drift_residual(tile):
    tile.config = replace(
        tile.config,
        drift_kick_common_rms_fraction=0.0,
        drift_kick_diff_rms_fraction=0.0,
    )


def remove_edge_kick(tile):
    e = len(tile.backend.physical_edges())
    tile.edge_injection_common = np.zeros(e, dtype=float)
    tile.edge_injection_diff = np.zeros(e, dtype=float)
    tile.edge_injection_a = np.zeros(e, dtype=float)
    tile.edge_injection_b = np.zeros(e, dtype=float)


def remove_leakage(tile):
    tile.leakage_rates = np.zeros(tile.nodes, dtype=float)
    tile.retention = np.ones(tile.nodes, dtype=float)


def exact_lane_holds(tile):
    e = len(tile.backend.physical_edges())
    tile.edge_lane_mismatch = np.zeros(e, dtype=float)
    tile.edge_lane_gain_a = np.ones(e, dtype=float)
    tile.edge_lane_gain_b = np.ones(e, dtype=float)


def exact_self_gain(tile):
    tile.self_gain = np.ones(tile.nodes, dtype=float)
    if hasattr(tile, "self_gain_measured"):
        tile.self_gain_measured = np.ones(tile.nodes, dtype=float)


def ideal_edge_codebook(tile):
    # Replace only the already-fabricated edge capacitor/codebook block by the
    # nominal 127-unit active-ratio ladder.  All other static fields survive.
    e = len(tile.backend.physical_edges())
    units = np.ones((e, 127), dtype=float)
    caps = segmented_capacitance_codes(units)
    ratio = float(tile.config.edge_cunit_over_csum)
    tile.edge_cap_units = units
    tile.edge_selected_capacitance_codes = caps.copy()
    tile.edge_site_ratio_scale = np.ones(e, dtype=float)
    tile.edge_cap_levels = caps * ratio
    tile.edge_codebook_steps = np.diff(tile.edge_cap_levels, axis=1)
    tile.edge_codebook_monotonic = np.all(tile.edge_codebook_steps > 0.0, axis=1)
    tile.edge_site_ratio_valid = True
    tile._rebuild_programmed_Q()


def ideal_converters(tile):
    tile.config = replace(
        tile.config,
        dac_bits=None,
        error_dac_bits=None,
        adc_bits=None,
    )


def ideal_credit(tile):
    tile.config = replace(
        tile.config,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
    )


def apply_condition(tile, condition):
    # Anti-redraw baseline common to every condition.
    thermal_zero(tile)
    if condition == "thermal_zero_baseline":
        return
    if condition == "no_drift_residual":
        remove_drift_residual(tile)
    elif condition == "no_inherited_edge_kick":
        remove_edge_kick(tile)
    elif condition == "no_state_leakage":
        remove_leakage(tile)
    elif condition == "exact_edge_lane_holds":
        exact_lane_holds(tile)
    elif condition == "exact_kick_self_gain":
        exact_self_gain(tile)
    elif condition == "ideal_edge_codebook":
        ideal_edge_codebook(tile)
    elif condition == "ideal_converters":
        ideal_converters(tile)
    elif condition == "ideal_credit_path":
        ideal_credit(tile)
    elif condition == "all_support_clean":
        remove_drift_residual(tile)
        remove_edge_kick(tile)
        remove_leakage(tile)
        exact_lane_holds(tile)
        exact_self_gain(tile)
        ideal_edge_codebook(tile)
        ideal_converters(tile)
        ideal_credit(tile)
    else:
        raise ValueError(condition)


def run_condition(task, cfg, gain, condition):
    et, ed, st, sd = make_four(task, cfg, gain)
    for tile in (et, ed, st, sd):
        apply_condition(tile, condition)

    eti, edi = DriftKickInterpreter(et), DriftKickInterpreter(ed)
    sti, sdi = DriftKickInterpreter(st), DriftKickInterpreter(sd)
    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    exact = [c0]
    shuffled = [sc0]
    credit_rms = []
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
        credit_rms.append(_rms(gc))
        et.apply_credits(-gc, step_size=0.20, normalize_rms=True)
        _sync_theta(et, ed)
        st.apply_credits(-gc[perm], step_size=0.20, normalize_rms=True)
        _sync_theta(st, sd)
        _, _, cv = _eval_pair(eti, edi)
        _, _, scv = _eval_pair(sti, sdi)
        exact.append(cv)
        shuffled.append(scv)

    return {
        "condition": condition,
        "sense_gain": gain,
        "initial_exact": float(exact[0]),
        "final_exact": float(exact[-1]),
        "final_shuffled": float(shuffled[-1]),
        "improvement": float(exact[-1]-exact[0]),
        "placement_gap": float(exact[-1]-shuffled[-1]),
        "final_win": bool(exact[-1] > shuffled[-1]),
        "mean_credit_rms": float(np.mean(credit_rms)),
    }


def main():
    task = compile_temporal_order_task(SEED)
    cfg = formal_config(SEED)
    gain = recommend_sense_gain(task, cfg)
    print(f"seed={SEED} frozen sense PGA={gain:g}", flush=True)
    rows=[]
    for condition in CONDITIONS:
        row=run_condition(task,cfg,gain,condition)
        rows.append(row)
        print(
            f"{condition:28s} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
            f"creditRMS={row['mean_credit_rms']:.3e}",
            flush=True,
        )
    baseline=rows[0]["improvement"]
    for row in rows:
        row["improvement_gain_vs_baseline"] = float(row["improvement"]-baseline)
    ranked=sorted(rows[1:-1],key=lambda r:r["improvement_gain_vs_baseline"],reverse=True)
    decision={
        "baseline_improvement":baseline,
        "strongest_single":ranked[0]["condition"] if ranked else None,
        "strongest_single_gain":ranked[0]["improvement_gain_vs_baseline"] if ranked else None,
        "all_support_clean_improvement":rows[-1]["improvement"],
        "pair_split_needed":bool(rows[-1]["improvement"]>=0.10 and (not ranked or ranked[0]["improvement"]<0.10)),
    }
    print("decision",decision,flush=True)
    Path("v09-seed2400-static-split.json").write_text(
        json.dumps({"experiment":"v09-seed2400-same-draw-static-split","preregistration":"docs/CIRCUIT_V09_SEED2400_STATIC_SPLIT_PREREG.md","seed":SEED,"sense_gain":gain,"conditions":rows,"decision":decision},indent=2)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__": main()
