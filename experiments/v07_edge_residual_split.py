"""Controlled physical split of v0.7 edge residuals on spent 2000--2009."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v07_active_summing_corner import config_for as formal_config
from transientwave.circuit_emulator_v07_active_summing import (
    ActiveSummingLockstepInterpreter,
    TW1AActiveSummingTile,
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
CONDITIONS = {
    "baseline_no_thermal": (),
    "perfect_caps": ("caps",),
    "perfect_cal": ("cal",),
    "perfect_lane": ("lane",),
    "perfect_caps_cal": ("caps", "cal"),
    "perfect_caps_lane": ("caps", "lane"),
    "perfect_cal_lane": ("cal", "lane"),
    "perfect_all_edge": ("caps", "cal", "lane"),
}


def _formal_no_thermal(seed: int):
    cfg = formal_config(seed)
    return cfg.__class__(**{**cfg.__dict__, "edge_ktc_base_fraction": 0.0})


def _idealize(tile: TW1AActiveSummingTile, defects: tuple[str, ...]) -> None:
    if "caps" in defects:
        e = len(tile.backend.physical_edges())
        tile.edge_cap_units = np.ones((e, 127), dtype=float)
        magnitudes = np.arange(128, dtype=float)
        levels = magnitudes * float(tile.config.edge_cunit_over_csum)
        tile.edge_selected_capacitance_codes = np.broadcast_to(
            magnitudes, (e, 128)
        ).copy()
        tile.edge_cap_levels = np.broadcast_to(levels, (e, 128)).copy()
        tile.edge_codebook_steps = np.diff(tile.edge_cap_levels, axis=1)
        tile.edge_codebook_monotonic = np.ones(e, dtype=bool)

    if "cal" in defects:
        tile.edge_effective_gain_measured = tile.edge_effective_gain_raw.copy()

    if "lane" in defects:
        e = len(tile.backend.physical_edges())
        tile.edge_lane_mismatch = np.zeros(e, dtype=float)
        tile.edge_lane_gain_a = np.ones(e, dtype=float)
        tile.edge_lane_gain_b = np.ones(e, dtype=float)

    tile._rebuild_programmed_Q()


def _training_with_fixed_draw(task, cfg, defects, *, iterations=30, step_size=0.20):
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)

    # Force the shuffled control to use the exact same formal physical tile.
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    # Surgical post-draw idealization. Because the four tiles are already
    # disorder-copied, this removes only the named defect and does not redraw
    # any other block.
    for tile in (exact_t, exact_d, shuffle_t, shuffle_d):
        _idealize(tile, defects)
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

    result = OrderContrastTrainingResult(
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
    )
    return result, gain


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
    output = {
        "experiment": "tw1a-v07-controlled-edge-residual-split",
        "status": "diagnostic-only-spent-2000-2009",
        "preregistration": "docs/CIRCUIT_V07_EDGE_RESIDUAL_SPLIT_PREREG.md",
        "conditions": [],
    }

    for name, defects in CONDITIONS.items():
        print(name, defects, flush=True)
        rows = []
        for seed in SEEDS:
            result, gain = _training_with_fixed_draw(
                compile_temporal_order_task(seed),
                _formal_no_thermal(seed),
                defects,
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
        output["conditions"].append(
            {"name": name, "removed_defects": list(defects), "summary": s, "runs": rows}
        )

    Path("v07-edge-residual-split.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
