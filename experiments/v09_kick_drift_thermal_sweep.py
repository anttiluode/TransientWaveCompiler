"""Preregistered full v0.9 kick-drift thermal diagnostic on spent 2300..2309."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for as v08_config
from transientwave.circuit_emulator_v09_kick_drift import (
    TW1AKickDriftConfig,
    TW1AKickDriftTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2300, 2310))
DRIFT_B = [0.0, 2.5e-6, 5e-6, 7.5e-6, 1e-5, 1.5e-5, 2e-5]


def config_for(seed: int, drift_b: float) -> TW1AKickDriftConfig:
    base = v08_config(seed)
    kwargs = dict(base.__dict__)
    kwargs.update(
        edge_ktc_base_fraction=2e-5,
        self_ktc_base_fraction=2e-5,
        kick_self_bits=10,
        kick_self_full_scale=0.125,
        drift_ktc_base_fraction=float(drift_b),
    )
    return TW1AKickDriftConfig(**kwargs)


def audit(manifest, cfg):
    tile = TW1AKickDriftTile(manifest, cfg, sense_gain=1.0)
    kick_self, _, _ = tile.physical_components()
    sigma = tile.self_thermal_sigma_fraction(kick_self)
    return {
        "all_monotonic": bool(np.all(tile.edge_codebook_monotonic)),
        "all_site_scales_positive": bool(tile.edge_site_ratio_valid),
        "all_headroom": bool(tile.minimum_edge_full_scale >= 0.25),
        "minimum_edge_full_scale": float(tile.minimum_edge_full_scale),
        "kick_self_saturated": bool(tile.kick_self_saturated),
        "max_abs_kick_self_target": float(tile.max_abs_kick_self_target),
        "max_abs_kick_self_actual": float(tile.max_abs_kick_self_actual),
        "max_kick_self_thermal_rms_fraction": float(np.max(sigma)),
    }


def summarize(rows):
    learned=[r for r in rows if r["improvement"] is not None]
    if len(learned) != len(SEEDS):
        return {
            "clean":False,"fabrication_ok":False,"improve_ge_0p10":0,"final_wins":0,
            "median_improvement":None,"minimum_improvement":None,
            "median_placement_gap":None,"minimum_placement_gap":None,
        }
    imp=[float(r["improvement"]) for r in learned]
    gaps=[float(r["placement_gap"]) for r in learned]
    n10=sum(x>=0.10 for x in imp)
    wins=sum(bool(r["final_win"]) for r in learned)
    med_imp=float(statistics.median(imp)); med_gap=float(statistics.median(gaps))
    fab=all(bool(r["fabrication_ok"]) for r in learned)
    return {
        "clean":bool(fab and n10==10 and wins==10 and med_imp>=0.30 and med_gap>=0.25),
        "fabrication_ok":bool(fab),
        "improve_ge_0p10":n10,
        "final_wins":wins,
        "median_improvement":med_imp,
        "minimum_improvement":float(min(imp)),
        "median_placement_gap":med_gap,
        "minimum_placement_gap":float(min(gaps)),
    }


def main() -> None:
    out={
        "experiment":"tw1a-v09-full-kick-drift-drift-thermal-sweep",
        "status":"diagnostic-only-spent-2300-2309",
        "preregistration":"docs/CIRCUIT_V09_KICK_DRIFT_THERMAL_PREREG.md",
        "seeds":SEEDS,
        "edge_b":2e-5,
        "kick_self_b":2e-5,
        "conditions":[],
    }

    for drift_b in DRIFT_B:
        print(f"drift_b={drift_b:g}",flush=True)
        rows=[]
        for seed in SEEDS:
            task=compile_temporal_order_task(seed); cfg=config_for(seed,drift_b)
            fab=audit(task["target"],cfg)
            fab_ok=bool(
                fab["all_monotonic"] and fab["all_site_scales_positive"] and
                fab["all_headroom"] and not fab["kick_self_saturated"]
            )
            if not fab_ok:
                row={"seed":seed,"fabrication":fab,"fabrication_ok":False,"sense_gain":None,
                     "improvement":None,"placement_gap":None,"final_exact":None,
                     "final_shuffled":None,"final_win":False}
                rows.append(row); print(f"  {seed}: AUDIT FAIL {fab}",flush=True); continue
            result,gain=run_order_contrast_training(task,cfg,iterations=30,step_size=0.20)
            row={
                "seed":seed,"fabrication":fab,"fabrication_ok":True,"sense_gain":gain,
                "improvement":float(result.exact_improvement),
                "placement_gap":float(result.placement_gap),
                "final_exact":float(result.exact_contrast[-1]),
                "final_shuffled":float(result.shuffled_contrast[-1]),
                "final_win":bool(result.exact_contrast[-1]>result.shuffled_contrast[-1]),
            }
            rows.append(row)
            print(
                f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} "
                f"win={row['final_win']} |Kself|max={fab['max_abs_kick_self_target']:.5f}",
                flush=True,
            )
        s=summarize(rows); print("  summary",s,flush=True)
        out["conditions"].append({"drift_b":drift_b,"summary":s,"runs":rows})

    clean=[c["drift_b"] for c in out["conditions"] if c["summary"]["clean"]]
    baseline=out["conditions"][0]["summary"]["clean"]
    out["decision"]={
        "zero_drift_noise_baseline_clean":bool(baseline),
        "clean_drift_b_points":clean,
        "largest_clean_drift_b":max(clean) if clean else None,
        "same_scale_2e-5_clean":bool(2e-5 in clean),
        "fresh_seed_authorized":False,
    }
    print("decision",out["decision"],flush=True)
    Path("v09-kick-drift-thermal-sweep.json").write_text(
        json.dumps(out,indent=2)+"\n",encoding="utf-8"
    )


if __name__=="__main__": main()
