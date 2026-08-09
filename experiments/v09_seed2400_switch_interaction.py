"""Same-draw simultaneous edge/drift switch residual scale sweep for seed 2400."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_seed2400_static_split import make_four, thermal_zero
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_drift_kick import DriftKickInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient

SEED=2400
SCALES=[1.0,0.75,0.50,0.25,0.10,0.0]


def scale_switch_residuals(tile,s):
    s=float(s)
    for name in ("edge_injection_common","edge_injection_diff","edge_injection_a","edge_injection_b"):
        setattr(tile,name,np.asarray(getattr(tile,name),dtype=float)*s)
    tile.config=replace(
        tile.config,
        drift_kick_common_rms_fraction=float(tile.config.drift_kick_common_rms_fraction)*s,
        drift_kick_diff_rms_fraction=float(tile.config.drift_kick_diff_rms_fraction)*s,
    )


def audit(tile):
    fs=float(tile.config.state_full_scale)
    qa=np.asarray(tile.edge_injection_a)/fs
    qb=np.asarray(tile.edge_injection_b)/fs
    qc=tile.drift_kick_node_vector("C")/fs
    qd=tile.drift_kick_node_vector("D")/fs
    rms=lambda x:float(np.sqrt(np.mean(np.asarray(x,dtype=float)**2)))
    return {
        "edge_a_rms_fraction":rms(qa),
        "edge_b_rms_fraction":rms(qb),
        "edge_ab_diff_rms_fraction":rms(qa-qb),
        "drift_c_rms_fraction":rms(qc),
        "drift_d_rms_fraction":rms(qd),
        "drift_cd_diff_rms_fraction":rms(qc-qd),
    }


def run_scale(task,cfg,gain,s):
    et,ed,st,sd=make_four(task,cfg,gain)
    for tile in (et,ed,st,sd):
        thermal_zero(tile)
        scale_switch_residuals(tile,s)
    physical=audit(et)
    eti,edi,sti,sdi=DriftKickInterpreter(et),DriftKickInterpreter(ed),DriftKickInterpreter(st),DriftKickInterpreter(sd)
    _,_,c0=_eval_pair(eti,edi); _,_,sc0=_eval_pair(sti,sdi)
    exact=[c0]; shuffled=[sc0]
    perm=np.random.default_rng(1729).permutation(len(et.theta))
    for _ in range(30):
        rt=eti.execute(stochastic_forward=True); rd=edi.execute(stochastic_forward=True)
        gc=contrast_gradient(float(rt["objective"]),float(rd["objective"]),np.asarray(rt["credits"],dtype=float),np.asarray(rd["credits"],dtype=float))
        et.apply_credits(-gc,step_size=.20,normalize_rms=True); _sync_theta(et,ed)
        st.apply_credits(-gc[perm],step_size=.20,normalize_rms=True); _sync_theta(st,sd)
        _,_,cv=_eval_pair(eti,edi); _,_,sv=_eval_pair(sti,sdi)
        exact.append(cv); shuffled.append(sv)
    return {
        "scale":float(s),
        "physical":physical,
        "initial_exact":float(exact[0]),
        "final_exact":float(exact[-1]),
        "final_shuffled":float(shuffled[-1]),
        "improvement":float(exact[-1]-exact[0]),
        "placement_gap":float(exact[-1]-shuffled[-1]),
        "final_win":bool(exact[-1]>shuffled[-1]),
    }


def main():
    task=compile_temporal_order_task(SEED); cfg=formal_config(SEED); gain=recommend_sense_gain(task,cfg)
    rows=[]
    for s in SCALES:
        r=run_scale(task,cfg,gain,s); rows.append(r); p=r["physical"]
        print(f"s={s:4.2f} DeltaC={r['improvement']:+.6f} gap={r['placement_gap']:+.6f} win={r['final_win']} edgeA={p['edge_a_rms_fraction']*1e6:.2f}ppm edgeAB={p['edge_ab_diff_rms_fraction']*1e6:.2f}ppm driftC={p['drift_c_rms_fraction']*1e6:.2f}ppm driftCD={p['drift_cd_diff_rms_fraction']*1e6:.2f}ppm",flush=True)
    passing=[r for r in rows if r["improvement"]>=.10 and r["final_win"]]
    boundary=max((r["scale"] for r in passing),default=None)
    inward=None
    if boundary is not None:
        smaller=[s for s in SCALES if s<boundary]
        inward=max(smaller) if smaller else None
    decision={"largest_passing_scale":boundary,"next_tested_point_inward":inward,"spent_cohort_replay_authorized":inward is not None}
    print("decision",decision,flush=True)
    Path("v09-seed2400-switch-interaction.json").write_text(json.dumps({"experiment":"v09-seed2400-switch-interaction-scale","preregistration":"docs/CIRCUIT_V09_SEED2400_SWITCH_INTERACTION_PREREG.md","seed":SEED,"sense_gain":gain,"conditions":rows,"decision":decision},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
