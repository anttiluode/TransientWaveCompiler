"""Same-silicon diagnosis of the failed fresh v0.8 2100--2109 gate."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_common_diff_corner import config_for as formal_config
from transientwave.circuit_emulator_v08_common_diff import (
    CommonDiffLockstepInterpreter,
    _eval_pair,
)
from transientwave.circuit_emulator_v08_site_ratio import (
    TW1ACommonDiffSiteTile,
    _make_pair,
    copy_circuit_disorder,
)
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.emulator import _rms
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_gradient,
)


SEEDS = list(range(2100, 2110))
FOCUS = 2107
CONDITIONS = (
    "formal",
    "no_thermal",
    "perfect_switch_kick",
    "perfect_cd_hold",
    "perfect_self_path",
    "perfect_credit_readout",
    "perfect_state_retention",
    "perfect_credit_accumulator",
    "ideal_lcc",
    "perfect_edge_fabrication",
    "perfect_converters",
)


def _apply_condition(tile: TW1ACommonDiffSiteTile, condition: str) -> None:
    if condition == "formal":
        return
    if condition == "no_thermal":
        tile.config = replace(tile.config, edge_ktc_base_fraction=0.0)
        return
    if condition == "perfect_switch_kick":
        e = len(tile.backend.physical_edges())
        tile.edge_injection_common = np.zeros(e, dtype=float)
        tile.edge_injection_diff = np.zeros(e, dtype=float)
        tile.edge_injection_a = np.zeros(e, dtype=float)
        tile.edge_injection_b = np.zeros(e, dtype=float)
        return
    if condition == "perfect_cd_hold":
        e = len(tile.backend.physical_edges())
        tile.edge_lane_mismatch = np.zeros(e, dtype=float)
        tile.edge_lane_gain_a = np.ones(e, dtype=float)
        tile.edge_lane_gain_b = np.ones(e, dtype=float)
        return
    if condition == "perfect_self_path":
        tile.self_gain = np.ones(tile.nodes, dtype=float)
        tile.self_gain_measured = np.ones(tile.nodes, dtype=float)
        tile._rebuild_programmed_Q()
        return
    if condition == "perfect_credit_readout":
        tile.config = replace(
            tile.config,
            credit_noise_fraction=0.0,
            credit_offset_fraction=0.0,
        )
        return
    if condition == "perfect_state_retention":
        tile.leakage_rates = np.zeros(tile.nodes, dtype=float)
        tile.retention = np.ones(tile.nodes, dtype=float)
        return
    if condition == "perfect_credit_accumulator":
        tile.config = replace(tile.config, credit_accumulator_leakage=0.0)
        return
    if condition == "ideal_lcc":
        tile.config = replace(tile.config, lcc_curvature=0.0)
        return
    if condition == "perfect_edge_fabrication":
        e = len(tile.backend.physical_edges())
        magnitudes = np.arange(128, dtype=float)
        ratio = float(tile.config.edge_cunit_over_csum)
        tile.edge_cap_units = np.ones((e, 127), dtype=float)
        tile.edge_selected_capacitance_codes = np.broadcast_to(
            magnitudes, (e, 128)
        ).copy()
        tile.edge_site_ratio_scale = np.ones(e, dtype=float)
        tile.edge_site_ratio_valid = True
        tile.edge_cap_levels = np.broadcast_to(
            magnitudes * ratio, (e, 128)
        ).copy()
        tile.edge_codebook_steps = np.diff(tile.edge_cap_levels, axis=1)
        tile.edge_codebook_monotonic = np.ones(e, dtype=bool)
        tile._rebuild_programmed_Q()
        return
    if condition == "perfect_converters":
        tile.config = replace(
            tile.config,
            self_bits=None,
            dac_bits=None,
            adc_bits=None,
            error_dac_bits=None,
        )
        tile._rebuild_programmed_Q()
        return
    raise ValueError(f"unknown condition {condition}")


def _train_same_draw(task, cfg, condition, *, iterations=30, step_size=0.20):
    # Freeze the formal sense PGA before any surgical idealization.
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)

    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    for tile in (exact_t, exact_d, shuffle_t, shuffle_d):
        _apply_condition(tile, condition)
    _sync_theta(exact_t, exact_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = CommonDiffLockstepInterpreter(exact_t)
    edi = CommonDiffLockstepInterpreter(exact_d)
    sti = CommonDiffLockstepInterpreter(shuffle_t)
    sdi = CommonDiffLockstepInterpreter(shuffle_d)

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

    for _ in range(int(iterations)):
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
    focus = next(r for r in rows if r["seed"] == FOCUS)
    return {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(bool(r["final_win"]) for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "focus_2107": {
            "improvement": focus["improvement"],
            "placement_gap": focus["placement_gap"],
            "final_exact": focus["final_exact"],
            "final_shuffled": focus["final_shuffled"],
            "final_win": focus["final_win"],
        },
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v08-fresh-failure-same-silicon-diagnosis",
        "status": "diagnostic-only-spent-2100-2109",
        "preregistration": "docs/CIRCUIT_V08_2107_DIAG_PREREG.md",
        "seeds": SEEDS,
        "conditions": [],
    }

    for condition in CONDITIONS:
        print(condition, flush=True)
        rows = []
        for seed in SEEDS:
            task = compile_temporal_order_task(seed)
            result, gain = _train_same_draw(task, formal_config(seed), condition)
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
        out["conditions"].append({"name": condition, "summary": s, "runs": rows})

    Path("v08-2107-failure-diagnosis.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
