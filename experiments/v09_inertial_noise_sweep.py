"""Preregistered v0.9 fixed-inertial-path diagnostic on spent 2300..2309."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for as v08_self_config
from transientwave.circuit_emulator_v09_inertial_baseline import (
    TW1AInertialBaselineConfig,
    TW1AInertialBaselineTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2300, 2310))
INERTIAL_NOISE = [0.0, 1e-5, 1.5e-5, 2e-5, 2.5e-5, 3e-5]


def config_for(seed: int, inertial_noise: float) -> TW1AInertialBaselineConfig:
    base = v08_self_config(seed)
    kwargs = dict(base.__dict__)
    kwargs.update(
        edge_ktc_base_fraction=2e-5,
        self_ktc_base_fraction=2e-5,
        inertial_nominal_gain=2.0,
        inertial_raw_gain_std=0.01,
        inertial_measurement_error_std=0.001,
        inertial_noise_fraction=float(inertial_noise),
        residual_self_bits=10,
        residual_self_full_scale=0.125,
    )
    return TW1AInertialBaselineConfig(**kwargs)


def audit(manifest, cfg):
    tile = TW1AInertialBaselineTile(manifest, cfg, sense_gain=1.0)
    total_self, _, _ = tile.physical_components()
    onsite, _ = tile._edge_cell_decomposition()
    return {
        "residual_saturated": bool(tile.residual_self_saturated),
        "max_abs_residual_target": float(tile.max_abs_residual_target),
        "max_abs_residual_actual": float(tile.max_abs_residual_actual),
        "max_abs_total_self_error": float(np.max(np.abs(total_self - onsite))),
        "max_abs_inertial_raw_deviation_from_2": float(
            np.max(np.abs(tile.inertial_gain_raw - 2.0))
        ),
        "max_abs_inertial_measurement_error": float(
            np.max(np.abs(tile.inertial_gain_measured - tile.inertial_gain_raw))
        ),
        "minimum_edge_full_scale": float(tile.minimum_edge_full_scale),
        "all_edge_codebooks_monotonic": bool(np.all(tile.edge_codebook_monotonic)),
        "edge_site_ratio_valid": bool(tile.edge_site_ratio_valid),
    }


def summarize(rows):
    learned = [r for r in rows if r["improvement"] is not None]
    if len(learned) != len(SEEDS):
        return {
            "clean": False,
            "improve_ge_0p10": 0,
            "final_wins": 0,
            "median_improvement": None,
            "minimum_improvement": None,
            "median_placement_gap": None,
            "minimum_placement_gap": None,
        }
    imp = [float(r["improvement"]) for r in learned]
    gaps = [float(r["placement_gap"]) for r in learned]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in learned)
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
        "experiment": "tw1a-v09-fixed-inertial-baseline-noise-sweep",
        "status": "diagnostic-only-spent-2300-2309",
        "preregistration": "docs/CIRCUIT_V09_INERTIAL_BASELINE_PREREG.md",
        "seeds": SEEDS,
        "conditions": [],
    }

    for inoise in INERTIAL_NOISE:
        print(f"inertial_noise={inoise:g}", flush=True)
        rows=[]; fabrication_ok=True
        for seed in SEEDS:
            task=compile_temporal_order_task(seed); cfg=config_for(seed,inoise); a=audit(task["target"],cfg)
            ok=bool(
                not a["residual_saturated"]
                and a["all_edge_codebooks_monotonic"]
                and a["edge_site_ratio_valid"]
                and a["minimum_edge_full_scale"] >= 0.25
            )
            fabrication_ok = fabrication_ok and ok
            if not ok:
                rows.append({"seed":seed,"audit":a,"sense_gain":None,"improvement":None,"placement_gap":None,"final_exact":None,"final_shuffled":None,"final_win":False})
                print(f"  {seed}: AUDIT FAIL {a}",flush=True); continue
            result,gain=run_order_contrast_training(task,cfg,iterations=30,step_size=0.20)
            row={"seed":seed,"audit":a,"sense_gain":gain,"improvement":result.exact_improvement,"placement_gap":result.placement_gap,"final_exact":result.exact_contrast[-1],"final_shuffled":result.shuffled_contrast[-1],"final_win":result.exact_contrast[-1]>result.shuffled_contrast[-1]}
            rows.append(row)
            print(f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']} residual={a['max_abs_residual_target']:.5f}",flush=True)
        s=summarize(rows); s["fabrication_ok"]=bool(fabrication_ok)
        print("  summary",s,flush=True)
        out["conditions"].append({"inertial_noise_fraction":inoise,"summary":s,"runs":rows})

    clean=[c["inertial_noise_fraction"] for c in out["conditions"] if c["summary"]["clean"] and c["summary"]["fabrication_ok"]]
    out["decision"]={
        "clean_inertial_noise_points":clean,
        "largest_clean_inertial_noise_fraction":max(clean) if clean else None,
        "fresh_seed_authorized":False,
        "next_if_useful":"translate passing fixed-path noise into a circuit/SPICE gate before fresh qualification",
    }
    print("decision",out["decision"],flush=True)
    Path("v09-inertial-noise-sweep.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
