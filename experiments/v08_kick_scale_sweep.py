"""Frozen same-silicon switch-kick residual scale sweep for TW-1A v0.8."""
from __future__ import annotations

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
SCALES = [1.00, 0.75, 0.50, 0.25, 0.10, 0.00]
FOCUS = 2107


def _scale_kick(tile, scale: float) -> dict[str, float]:
    fs = float(tile.config.state_full_scale)
    common0 = np.asarray(tile.edge_injection_common, dtype=float).copy()
    diff0 = np.asarray(tile.edge_injection_diff, dtype=float).copy()

    tile.edge_injection_common = common0 * float(scale)
    tile.edge_injection_diff = diff0 * float(scale)
    tile.edge_injection_a = tile.edge_injection_common + tile.edge_injection_diff
    tile.edge_injection_b = tile.edge_injection_common - tile.edge_injection_diff

    return {
        "common_rms_unscaled_fraction": _rms(common0) / fs,
        "diff_rms_unscaled_fraction": _rms(diff0) / fs,
        "common_rms_scaled_fraction": _rms(tile.edge_injection_common) / fs,
        "diff_rms_scaled_fraction": _rms(tile.edge_injection_diff) / fs,
    }


def _train_same_draw(task, cfg, scale: float, *, iterations=30, step_size=0.20):
    # Freeze the exact formal PGA before touching the already-drawn kick residual.
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)

    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    # All four bodies now share the same formal physical tile. Scale only the
    # residual kick arrays after fabrication/autozero/cancellation are complete.
    stats = _scale_kick(exact_t, scale)
    for tile in (exact_d, shuffle_t, shuffle_d):
        _scale_kick(tile, scale)
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
    return result, gain, stats


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    focus = next(r for r in rows if r["seed"] == FOCUS)
    common_unscaled = [float(r["kick"]["common_rms_unscaled_fraction"]) for r in rows]
    diff_unscaled = [float(r["kick"]["diff_rms_unscaled_fraction"]) for r in rows]
    common_scaled = [float(r["kick"]["common_rms_scaled_fraction"]) for r in rows]
    diff_scaled = [float(r["kick"]["diff_rms_scaled_fraction"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    formal_predicate = bool(n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25)
    return {
        "formal_predicate": formal_predicate,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": med_gap,
        "minimum_placement_gap": float(min(gaps)),
        "focus_2107": {
            "improvement": focus["improvement"],
            "placement_gap": focus["placement_gap"],
            "final_exact": focus["final_exact"],
            "final_shuffled": focus["final_shuffled"],
            "final_win": focus["final_win"],
        },
        "kick_fraction": {
            "mean_common_rms_unscaled": float(np.mean(common_unscaled)),
            "mean_diff_rms_unscaled": float(np.mean(diff_unscaled)),
            "mean_common_rms_scaled": float(np.mean(common_scaled)),
            "mean_diff_rms_scaled": float(np.mean(diff_scaled)),
            "max_tile_common_rms_scaled": float(max(common_scaled)),
            "max_tile_diff_rms_scaled": float(max(diff_scaled)),
        },
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v08-switch-kick-residual-scale-sweep",
        "status": "diagnostic-only-spent-2100-2109",
        "preregistration": "docs/CIRCUIT_V08_KICK_SCALE_PREREG.md",
        "seeds": SEEDS,
        "scales": [],
    }

    for scale in SCALES:
        print(f"kick_scale={scale:g}", flush=True)
        rows = []
        for seed in SEEDS:
            result, gain, kick = _train_same_draw(
                compile_temporal_order_task(seed),
                formal_config(seed),
                scale,
            )
            row = {
                "seed": seed,
                "sense_gain": gain,
                "kick": kick,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            }
            rows.append(row)
            print(
                f"  {seed}: DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
                f"kickC={kick['common_rms_scaled_fraction']:.3e} "
                f"kickD={kick['diff_rms_scaled_fraction']:.3e}",
                flush=True,
            )
        s = summarize(rows)
        print("  summary", s, flush=True)
        out["scales"].append({"scale": scale, "summary": s, "runs": rows})

    passing_nonzero = [
        float(entry["scale"])
        for entry in out["scales"]
        if float(entry["scale"]) > 0.0 and entry["summary"]["formal_predicate"]
    ]
    out["decision"] = {
        "largest_passing_nonzero_scale": max(passing_nonzero) if passing_nonzero else None,
    }
    print("decision", out["decision"], flush=True)

    Path("v08-kick-scale-sweep.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
