"""Frozen simultaneous 5 ppm common + 5 ppm differential drift residual gate."""
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

SEEDS=list(range(2300,2310))
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
    t=TW1ADriftKickTile(manifest,cfg,sense_gain=1.0); t.physical_components()
    qc=t.drift_kick_node_vector("C")/cfg.state_full_scale
    qd=t.drift_kick_node_vector("D")/cfg.state_full_scale
    return {
        "valid":bool(np.all(t.edge_codebook_monotonic) and t.edge_site_ratio_valid and t.minimum_edge_full_scale>=0.25 and not t.kick_self_saturated),
        "minimum_edge_full_scale":float(t.minimum_edge_full_scale),
        "max_abs_kick_self_target":float(t.max_abs_kick_self_target),
        "realized_c_rms_fraction":float(np.sqrt(np.mean(qc*qc))),
        "realized_d_rms_fraction":float(np.sqrt(np.mean(qd*qd))),
        "realized_cd_difference_rms_fraction":float(np.sqrt(np.mean((qc-qd)**2))),
    }


def main():
    rows=[]
    for seed in SEEDS:
        task=compile_temporal_order_task(seed); cfg=config_for(seed); fab=audit(task["target"],cfg)
        if not fab["valid"]:
            row={"seed":seed,"fabrication":fab,"improvement":None,"placement_gap":None,"final_win":False}; rows.append(row); print(seed,"AUDIT FAIL",fab,flush=True); continue
        r,g=run_order_contrast_training(task,cfg,iterations=30,step_size=.20)
        row={"seed":seed,"fabrication":fab,"sense_gain":g,"improvement":float(r.exact_improvement),"placement_gap":float(r.placement_gap),"final_exact":float(r.exact_contrast[-1]),"final_shuffled":float(r.shuffled_contrast[-1]),"final_win":bool(r.exact_contrast[-1]>r.shuffled_contrast[-1])}; rows.append(row)
        print(f"{seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']} Ckick={fab['realized_c_rms_fraction']*1e6:.2f}ppm Dkick={fab['realized_d_rms_fraction']*1e6:.2f}ppm CD={fab['realized_cd_difference_rms_fraction']*1e6:.2f}ppm",flush=True)
    ok=[r for r in rows if r["improvement"] is not None]
    imp=[r["improvement"] for r in ok]; gaps=[r["placement_gap"] for r in ok]
    n=sum(x>=.10 for x in imp); w=sum(r["final_win"] for r in ok)
    mi=float(statistics.median(imp)) if imp else None; mg=float(statistics.median(gaps)) if gaps else None
    qualified=bool(len(ok)==10 and n==10 and w==10 and mi>=.30 and mg>=.25)
    summary={"qualified":qualified,"fabrication_pass":len(ok)==10,"improve_ge_0p10":n,"final_wins":w,"median_improvement":mi,"minimum_improvement":float(min(imp)) if imp else None,"median_placement_gap":mg,"minimum_placement_gap":float(min(gaps)) if gaps else None}
    print("summary",summary,flush=True)
    out={"experiment":"v09-drift-kick-combined-reference","status":"spent-body-reference","seeds":SEEDS,"common_rms_fraction":COMMON,"diff_rms_fraction":DIFF,"summary":summary,"runs":rows,"decision":{"fresh_2400_2409_authorized":qualified}}
    Path("v09-drift-kick-combined.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    if not qualified: raise SystemExit("combined v0.9 reference failed frozen predicate")

if __name__=="__main__": main()
