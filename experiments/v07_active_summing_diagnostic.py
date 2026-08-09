"""Frozen spent-body diagnostic for TW-1A v0.7 active summing."""
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


SEEDS = list(range(1800, 1810))
VALUES = [0.0, 1e-5, 3e-5, 1e-4]
EDGE_FULL_SCALE = 0.255
CUNIT_OVER_CSTATE = EDGE_FULL_SCALE / 127.0


def config_for(seed: int, b: float) -> TW1AActiveSummingConfig:
    kwargs = dict(c0e_config_for(seed).__dict__)
    kwargs.update(
        state_noise_std=0.0,
        edge_gain_cv=0.0,
        edge_common_settling_loss=0.0,
        prev_ratio_error_std=0.0,
        prev_ratio_calibration=False,
        prev_ratio_calibration_error_std=0.0,
        edge_cunit_over_csum=CUNIT_OVER_CSTATE,
        edge_ktc_base_fraction=float(b),
        seed=150_000 + seed,
    )
    return TW1AActiveSummingConfig(**kwargs)


def audit_fabrication(manifest, cfg: TW1AActiveSummingConfig) -> dict:
    tile = TW1AActiveSummingTile(manifest, cfg, sense_gain=1.0)
    failing_monotonic = np.flatnonzero(~tile.edge_codebook_monotonic)
    full_scales = np.asarray(tile.edge_cap_levels[:, -1], dtype=float)
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


def summarize(rows: list[dict]) -> dict:
    learned = [r for r in rows if r["improvement"] is not None]
    fabrication_pass = all(
        r["fabrication"]["all_monotonic"] and r["fabrication"]["all_headroom"]
        for r in rows
    )
    if len(learned) != len(SEEDS):
        return {
            "all_body_clean": False,
            "fabrication_pass": fabrication_pass,
            "improve_ge_0p10": 0,
            "final_wins": 0,
            "median_improvement": None,
            "median_placement_gap": None,
            "min_improvement": None,
            "min_placement_gap": None,
        }
    imp = [float(r["improvement"]) for r in learned]
    gaps = [float(r["placement_gap"]) for r in learned]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in learned)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "all_body_clean": bool(
            fabrication_pass
            and n10 == 10
            and wins == 10
            and med_imp >= 0.30
            and med_gap >= 0.25
        ),
        "fabrication_pass": fabrication_pass,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gaps)),
    }


def main() -> None:
    output = {
        "experiment": "tw1a-v07-active-summing-spent-body-diagnostic",
        "status": "diagnostic-only-spent-task-bodies",
        "preregistration": "docs/CIRCUIT_V07_ACTIVE_SUMMING_DIAGNOSTIC_PREREG.md",
        "seeds": SEEDS,
        "values": [],
    }

    for b in VALUES:
        print(f"b={b:g}", flush=True)
        rows = []
        for seed in SEEDS:
            task = compile_temporal_order_task(seed)
            cfg = config_for(seed, b)
            fab = audit_fabrication(task["target"], cfg)
            print(
                f"  seed={seed} mono={fab['all_monotonic']} "
                f"headroom={fab['all_headroom']} "
                f"FSmin={fab['minimum_edge_full_scale']:.6f}",
                flush=True,
            )
            if not (fab["all_monotonic"] and fab["all_headroom"]):
                rows.append({
                    "seed": seed,
                    "fabrication": fab,
                    "sense_gain": None,
                    "improvement": None,
                    "placement_gap": None,
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
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            }
            rows.append(row)
            print(
                f"    PGA={gain:g} DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} "
                f"C={row['final_exact']:+.6f} "
                f"Cshuffle={row['final_shuffled']:+.6f}",
                flush=True,
            )

        summary = summarize(rows)
        min_fs = float(min(r["fabrication"]["minimum_edge_full_scale"] for r in rows))
        min_step = float(min(r["fabrication"]["minimum_codebook_step"] for r in rows))
        summary["minimum_edge_full_scale"] = min_fs
        summary["minimum_codebook_step"] = min_step
        print("  summary", summary, flush=True)
        output["values"].append({
            "edge_ktc_base_fraction": b,
            "summary": summary,
            "runs": rows,
        })

    clean = [
        float(v["edge_ktc_base_fraction"])
        for v in output["values"]
        if v["summary"]["all_body_clean"]
    ]
    last_clean = max(clean) if clean else None
    inward = None if last_clean is None else last_clean / 3.0
    output["decision"] = {
        "largest_clean_tested_b": last_clean,
        "three_x_inward_b": inward,
        "fresh_seed_reservation": list(range(2000, 2010)),
    }
    print("decision", output["decision"], flush=True)

    Path("v07-active-summing-diagnostic.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
