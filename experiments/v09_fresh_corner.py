"""Preregistered fresh TW-1A v0.9 kick-drift qualification, seeds 2400..2409."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for as v08_config
from transientwave.circuit_emulator_v09_drift_kick import (
    TW1ADriftKickConfig,
    TW1ADriftKickTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task

SEEDS=list(range(2400,2410))
COMMON=5e-6
DIFF=5e-6


def config_for(seed:int)->TW1ADriftKickConfig:
    base=v08_config(seed); kw=dict(base.__dict__)
    kw.update(
        edge_ktc_base_fraction=2e-5,
        self_ktc_base_fraction=2e-5,
        kick_self_bits=10,
        kick_self_full_scale=0.125,
        drift_ktc_base_fraction=2e-5,
        drift_kick_common_rms_fraction=COMMON,
        drift_kick_diff_rms_fraction=DIFF,
    )
    return TW1ADriftKickConfig(**kw)


def audit(manifest,cfg):
    t=TW1ADriftKickTile(manifest,cfg,sense_gain=1.0); kself,_,_=t.physical_components()
    qc=t.drift_kick_node_vector("C")/cfg.state_full_scale
    qd=t.drift_kick_node_vector("D")/cfg.state_full_scale
    return {
        "all_monotonic":bool(np.all(t.edge_codebook_monotonic)),
        "site_ratio_valid":bool(t.edge_site_ratio_valid),
        "minimum_edge_full_scale":float(t.minimum_edge_full_scale),
        "edge_headroom":bool(t.minimum_edge_full_scale>=0.25),
        "kick_self_saturated":bool(t.kick_self_saturated),
        "max_abs_kick_self_target":float(t.max_abs_kick_self_target),
        "max_abs_kick_self_actual":float(t.max_abs_kick_self_actual),
        "max_kick_self_thermal_rms_fraction":float(np.max(t.self_thermal_sigma_fraction(kself))),
        "realized_c_rms_fraction":float(np.sqrt(np.mean(qc*qc))),
        "realized_d_rms_fraction":float(np.sqrt(np.mean(qd*qd))),
        "realized_cd_difference_rms_fraction":float(np.sqrt(np.mean((qc-qd)**2))),
    }


def main():
    rows=[]
    for seed in SEEDS:
        task=compile_temporal_order_task(seed); cfg=config_for(seed); fab=audit(task["target"],cfg)
        fab_ok=bool(fab["all_monotonic"] and fab["site_ratio_valid"] and fab["edge_headroom"] and not fab["kick_self_saturated"])
        print(f"seed={seed} mono={fab['all_monotonic']} site={fab['site_ratio_valid']} headroom={fab['edge_headroom']} FSmin={fab['minimum_edge_full_scale']:.6f} Kself={fab['max_abs_kick_self_target']:.6f} Ckick={fab['realized_c_rms_fraction']*1e6:.2f}ppm Dkick={fab['realized_d_rms_fraction']*1e6:.2f}ppm CD={fab['realized_cd_difference_rms_fraction']*1e6:.2f}ppm",flush=True)
        if not fab_ok:
            rows.append({"seed":seed,"fabrication":fab,"fabrication_ok":False,"sense_gain":None,"improvement":None,"placement_gap":None,"final_exact":None,"final_shuffled":None,"final_win":False}); continue
        r,g=run_order_contrast_training(task,cfg,iterations=30,step_size=.20)
        row={"seed":seed,"fabrication":fab,"fabrication_ok":True,"sense_gain":g,"improvement":float(r.exact_improvement),"placement_gap":float(r.placement_gap),"final_exact":float(r.exact_contrast[-1]),"final_shuffled":float(r.shuffled_contrast[-1]),"final_win":bool(r.exact_contrast[-1]>r.shuffled_contrast[-1])}; rows.append(row)
        print(f"  PGA={g:g} DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} C={row['final_exact']:+.6f} Cshuffle={row['final_shuffled']:+.6f}",flush=True)

    learned=[r for r in rows if r["improvement"] is not None]
    imp=[r["improvement"] for r in learned]; gaps=[r["placement_gap"] for r in learned]
    n=sum(x>=.10 for x in imp); w=sum(r["final_win"] for r in learned)
    mi=float(statistics.median(imp)) if imp else None; mg=float(statistics.median(gaps)) if gaps else None
    qualified=bool(len(learned)==10 and n==10 and w==10 and mi>=.30 and mg>=.25)
    summary={
        "qualified":qualified,
        "fabrication_pass":len(learned)==10,
        "fabricated_tiles_pass":len(learned),
        "fabricated_tiles_total":10,
        "improve_ge_0p10":n,
        "final_wins":w,
        "median_improvement":mi,
        "minimum_improvement":float(min(imp)) if imp else None,
        "median_placement_gap":mg,
        "minimum_placement_gap":float(min(gaps)) if gaps else None,
        "minimum_edge_full_scale":float(min(r["fabrication"]["minimum_edge_full_scale"] for r in rows)),
        "maximum_abs_kick_self_target":float(max(r["fabrication"]["max_abs_kick_self_target"] for r in rows)),
        "maximum_kick_self_thermal_rms_fraction":float(max(r["fabrication"]["max_kick_self_thermal_rms_fraction"] for r in rows)),
        "mean_realized_c_drift_kick_rms_fraction":float(np.mean([r["fabrication"]["realized_c_rms_fraction"] for r in rows])),
        "mean_realized_d_drift_kick_rms_fraction":float(np.mean([r["fabrication"]["realized_d_rms_fraction"] for r in rows])),
        "mean_realized_cd_diff_rms_fraction":float(np.mean([r["fabrication"]["realized_cd_difference_rms_fraction"] for r in rows])),
    }
    print("summary",summary,flush=True)
    out={"experiment":"tw1a-v09-fresh-kick-drift-corner","status":"formal-fresh","preregistration":"docs/CIRCUIT_V09_FRESH_PREREG.md","seeds":SEEDS,"config":{"edge_b":2e-5,"kick_self_b":2e-5,"drift_b":2e-5,"drift_common_rms_fraction":COMMON,"drift_diff_rms_fraction":DIFF},"summary":summary,"runs":rows}
    Path("v09-fresh-corner.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    if not qualified: raise SystemExit("fresh v0.9 gate failed frozen predicate")

if __name__=="__main__": main()
