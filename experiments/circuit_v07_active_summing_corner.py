"""Fresh preregistered qualification for TW-1A v0.7 active summing."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v05_edge_thermal_corner import config_for as c0e_config_for
from transientwave.circuit_emulator_v07_active_summing import (
    TW1AActiveSummingConfig,
    TW1AActiveSummingTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2000, 2010))
EDGE_FULL_SCALE = 0.255
CUNIT_OVER_CSTATE = EDGE_FULL_SCALE / 127.0


def config_for(seed: int) -> TW1AActiveSummingConfig:
    kwargs = dict(c0e_config_for(seed).__dict__)
    kwargs.update(
        state_noise_std=0.0,
        edge_gain_cv=0.0,
        edge_common_settling_loss=0.0,
        prev_ratio_error_std=0.0,
        prev_ratio_calibration=False,
        prev_ratio_calibration_error_std=0.0,
        edge_cunit_over_csum=CUNIT_OVER_CSTATE,
        edge_ktc_base_fraction=1e-5,
        seed=160_000 + seed,
    )
    return TW1AActiveSummingConfig(**kwargs)


def audit_fabrication(manifest, cfg: TW1AActiveSummingConfig) -> dict:
    tile = TW1AActiveSummingTile(manifest, cfg, sense_gain=1.0)
    full_scales = np.asarray(tile.edge_cap_levels[:, -1], dtype=float)
    failing_monotonic = np.flatnonzero(~tile.edge_codebook_monotonic)
    failing_headroom = np.flatnonzero(full_scales < 0.25)
    return {
        "all_monotonic": bool(tile.all_edge_codebooks_monotonic),
        "all_headroom": bool(np.all(full_scales >= 0.25)),
        "failing_monotonic_count": int(len(failing_monotonic)),
        "failing_headroom_count": int(len(failing_headroom)),
        "minimum_edge_full_scale": float(np.min(full_scales)),
        "maximum_edge_full_scale": float(np.max(full_scales)),
        "minimum_codebook_step": float(tile.minimum_codebook_step),
    }


def main() -> None:
    rows = []
    fabrication_pass = True

    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        cfg = config_for(seed)
        fab = audit_fabrication(task["target"], cfg)
        fab_ok = bool(fab["all_monotonic"] and fab["all_headroom"])
        fabrication_pass = fabrication_pass and fab_ok
        print(
            f"seed={seed} mono={fab['all_monotonic']} "
            f"headroom={fab['all_headroom']} "
            f"FSmin={fab['minimum_edge_full_scale']:.6f}",
            flush=True,
        )

        if not fab_ok:
            rows.append({
                "seed": seed,
                "fabrication": fab,
                "sense_gain": None,
                "improvement": None,
                "placement_gap": None,
                "initial_contrast": None,
                "final_exact": None,
                "final_shuffled": None,
                "final_win": False,
            })
            continue

        result, gain = run_order_contrast_training(
            task,
            cfg,
            iterations=30,
            step_size=0.20,
        )
        row = {
            "seed": seed,
            "fabrication": fab,
            "sense_gain": gain,
            "improvement": result.exact_improvement,
            "placement_gap": result.placement_gap,
            "initial_contrast": result.exact_contrast[0],
            "final_exact": result.exact_contrast[-1],
            "final_shuffled": result.shuffled_contrast[-1],
            "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
        }
        rows.append(row)
        print(
            f"  PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} C={row['final_exact']:+.6f} "
            f"Cshuffle={row['final_shuffled']:+.6f}",
            flush=True,
        )

    learned = [r for r in rows if r["improvement"] is not None]
    if len(learned) == len(SEEDS):
        imp = [float(r["improvement"]) for r in learned]
        gaps = [float(r["placement_gap"]) for r in learned]
        n10 = sum(v >= 0.10 for v in imp)
        wins = sum(bool(r["final_win"]) for r in learned)
        med_imp = float(statistics.median(imp))
        med_gap = float(statistics.median(gaps))
        min_imp = float(min(imp))
        min_gap = float(min(gaps))
    else:
        n10 = 0
        wins = 0
        med_imp = None
        med_gap = None
        min_imp = None
        min_gap = None

    qualified = bool(
        fabrication_pass
        and len(learned) == 10
        and n10 == 10
        and wins == 10
        and med_imp is not None
        and med_imp >= 0.30
        and med_gap is not None
        and med_gap >= 0.25
    )
    summary = {
        "qualified": qualified,
        "fabrication_pass": fabrication_pass,
        "fabricated_tiles_total": len(rows),
        "fabricated_tiles_pass": sum(
            bool(r["fabrication"]["all_monotonic"] and r["fabrication"]["all_headroom"])
            for r in rows
        ),
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": min_imp,
        "min_placement_gap": min_gap,
        "minimum_edge_full_scale": float(
            min(r["fabrication"]["minimum_edge_full_scale"] for r in rows)
        ),
        "minimum_codebook_step": float(
            min(r["fabrication"]["minimum_codebook_step"] for r in rows)
        ),
    }
    print("summary", summary, flush=True)

    Path("circuit-v07-active-summing-corner.json").write_text(
        json.dumps(
            {
                "experiment": "tw1a-v07-active-summing-formal-gate",
                "preregistration": "docs/CIRCUIT_V07_ACTIVE_SUMMING_PREREG.md",
                "seeds": SEEDS,
                "edge_ktc_base_fraction": 1e-5,
                "edge_nominal_full_scale": EDGE_FULL_SCALE,
                "cunit_over_cstate": CUNIT_OVER_CSTATE,
                "iterations": 30,
                "step_size": 0.20,
                "config": config_for(SEEDS[0]).__dict__,
                "summary": summary,
                "runs": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if not qualified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
