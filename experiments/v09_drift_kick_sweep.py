"""Preregistered v0.9 drift-shear post-cancellation residual split."""
from __future__ import annotations

import argparse
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
LEVELS_PPM=[0.0,0.5,1.0,2.0,3.0,5.0,10.0]


def config_for(seed:int,axis:str,ppm:float)->TW1ADriftKickConfig:
    base=v08_config(seed); kw=dict(base.__dict__)
    common=ppm*1e-6 if axis=="common" else 0.0
    diff=ppm*1e-6 if axis=="diff" else 0.0
    kw.update(
        edge_ktc_base_fraction=2e-5,
        self_ktc_base_fraction=2e-5,
        kick_self_bits=10,
        kick_self_full_scale=0.125,
        drift_ktc_base_fraction=2e-5,
        drift_kick_common_rms_fraction=common,
        drift_kick_diff_rms_fraction=diff,
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


def summarize(rows):
    if any(r["improvement"] is None for r in rows): return {"clean":False,"fabrication_ok":False}
    imp=[r["improvement"] for r in rows]; gaps=[r["placement_gap"] for r in rows]
    n=sum(x>=.10 for x in imp); w=sum(r["final_win"] for r in rows)
    mi=float(statistics.median(imp)); mg=float(statistics.median(gaps))
    return {"clean":bool(n==10 and w==10 and mi>=.30 and mg>=.25),"fabrication_ok":True,"improve_ge_0p10":n,"final_wins":w,"median_improvement":mi,"minimum_improvement":float(min(imp)),"median_placement_gap":mg,"minimum_placement_gap":float(min(gaps))}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--axis",choices=["common","diff"],required=True); a=ap.parse_args()
    out={"experiment":"v09-drift-switch-residual-split","axis":a.axis,"seeds":SEEDS,"levels_ppm":LEVELS_PPM,"conditions":[]}
    for ppm in LEVELS_PPM:
        print(f"axis={a.axis} ppm={ppm:g}",flush=True); rows=[]
        for seed in SEEDS:
            task=compile_temporal_order_task(seed); cfg=config_for(seed,a.axis,ppm); fab=audit(task["target"],cfg)
            if not fab["valid"]:
                rows.append({"seed":seed,"fabrication":fab,"improvement":None,"placement_gap":None,"final_win":False}); print(f"  {seed}: AUDIT FAIL",flush=True); continue
            r,g=run_order_contrast_training(task,cfg,iterations=30,step_size=.20)
            row={"seed":seed,"fabrication":fab,"sense_gain":g,"improvement":float(r.exact_improvement),"placement_gap":float(r.placement_gap),"final_exact":float(r.exact_contrast[-1]),"final_shuffled":float(r.shuffled_contrast[-1]),"final_win":bool(r.exact_contrast[-1]>r.shuffled_contrast[-1])}; rows.append(row)
            print(f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']}",flush=True)
        s=summarize(rows); print("  summary",s,flush=True); out["conditions"].append({"ppm":ppm,"summary":s,"runs":rows})
    clean=[c["ppm"] for c in out["conditions"] if c["summary"].get("clean")]
    out["decision"]={"largest_clean_ppm":max(clean) if clean else None,"clean_ppm":clean,"fresh_seed_authorized":False}
    print("decision",out["decision"],flush=True)
    Path(f"v09-drift-kick-{a.axis}.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
