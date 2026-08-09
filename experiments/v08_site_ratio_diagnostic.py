"""Frozen v0.8 common/difference diagnostic with explicit site ratio error."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v07_active_summing_corner import config_for as v07_formal_config
from transientwave.circuit_emulator_v08_site_ratio import (
    TW1ACommonDiffSiteConfig,
    TW1ACommonDiffSiteTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2000, 2010))
EDGE_FS = 0.265
CUNIT_OVER_CSTATE = EDGE_FS / 127.0


def config_for(seed: int) -> TW1ACommonDiffSiteConfig:
    base = v07_formal_config(seed)
    kwargs = dict(base.__dict__)
    kwargs.update(
        edge_cunit_over_csum=CUNIT_OVER_CSTATE,
        edge_ktc_base_fraction=1e-5,
        edge_site_ratio_sigma=0.01,
    )
    return TW1ACommonDiffSiteConfig(**kwargs)


def fabrication_audit(manifest, cfg):
    tile = TW1ACommonDiffSiteTile(manifest, cfg, sense_gain=1.0)
    full_scale = np.asarray(tile.edge_cap_levels[:, -1], dtype=float)
    return {
        "all_monotonic": bool(np.all(tile.edge_codebook_monotonic)),
        "all_site_scales_positive": bool(tile.edge_site_ratio_valid),
        "all_headroom": bool(np.all(full_scale >= 0.25)),
        "minimum_edge_full_scale": float(np.min(full_scale)),
        "maximum_edge_full_scale": float(np.max(full_scale)),
        "minimum_site_scale": float(np.min(tile.edge_site_ratio_scale)),
        "maximum_site_scale": float(np.max(tile.edge_site_ratio_scale)),
        "minimum_codebook_step": float(np.min(tile.edge_codebook_steps)),
    }


def main():
    rows = []
    fabrication_pass = True
    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        cfg = config_for(seed)
        fab = fabrication_audit(task["target"], cfg)
        fab_ok = fab["all_monotonic"] and fab["all_site_scales_positive"] and fab["all_headroom"]
        fabrication_pass = fabrication_pass and fab_ok
        print(
            f"seed={seed} mono={fab['all_monotonic']} positive={fab['all_site_scales_positive']} "
            f"headroom={fab['all_headroom']} FSmin={fab['minimum_edge_full_scale']:.6f}",
            flush=True,
        )
        if not fab_ok:
            rows.append({
                "seed": seed,
                "fabrication": fab,
                "improvement": None,
                "placement_gap": None,
                "final_win": False,
            })
            continue
        result, gain = run_order_contrast_training(
            task, cfg, iterations=30, step_size=0.20
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
            f"  PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']}",
            flush=True,
        )

    learned = [r for r in rows if r["improvement"] is not None]
    if len(learned) == 10:
        imp = [float(r["improvement"]) for r in learned]
        gaps = [float(r["placement_gap"]) for r in learned]
        n10 = sum(x >= 0.10 for x in imp)
        wins = sum(bool(r["final_win"]) for r in learned)
        med_imp = float(statistics.median(imp))
        med_gap = float(statistics.median(gaps))
        min_imp = float(min(imp))
        min_gap = float(min(gaps))
    else:
        n10 = wins = 0
        med_imp = med_gap = min_imp = min_gap = None

    diagnostic_pass = bool(
        fabrication_pass
        and len(learned) == 10
        and n10 == 10
        and wins == 10
        and med_imp is not None and med_imp >= 0.30
        and med_gap is not None and med_gap >= 0.25
    )
    summary = {
        "diagnostic_pass": diagnostic_pass,
        "fabrication_pass": fabrication_pass,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "minimum_improvement": min_imp,
        "median_placement_gap": med_gap,
        "minimum_placement_gap": min_gap,
        "minimum_edge_full_scale": float(
            min(r["fabrication"]["minimum_edge_full_scale"] for r in rows)
        ),
    }
    print("summary", summary, flush=True)
    out = {
        "experiment": "tw1a-v08-site-ratio-spent-body-diagnostic",
        "status": "diagnostic-only-spent-2000-2009",
        "preregistration": "docs/CIRCUIT_V08_SITE_RATIO_DIAGNOSTIC_PREREG.md",
        "seeds": SEEDS,
        "edge_nominal_full_scale": EDGE_FS,
        "edge_unit_cap_sigma": 0.03,
        "edge_site_ratio_sigma": 0.01,
        "edge_ktc_base_fraction": 1e-5,
        "summary": summary,
        "runs": rows,
        "fresh_seed_reservation_if_pass": list(range(2100, 2110)),
    }
    Path("v08-site-ratio-diagnostic.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
