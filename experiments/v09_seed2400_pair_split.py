"""All six same-draw pairs among the strongest seed-2400 static surgeries."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_seed2400_static_split import (
    exact_self_gain,
    ideal_edge_codebook,
    make_four,
    remove_drift_residual,
    remove_edge_kick,
    thermal_zero,
)
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_drift_kick import DriftKickInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient

SEED=2400
PAIRS=[
    ("edge_kick","drift_residual"),
    ("edge_kick","edge_codebook"),
    ("edge_kick","kick_self_gain"),
    ("drift_residual","edge_codebook"),
    ("drift_residual","kick_self_gain"),
    ("edge_codebook","kick_self_gain"),
]

SURGERY={
    "edge_kick":remove_edge_kick,
    "drift_residual":remove_drift_residual,
    "edge_codebook":ideal_edge_codebook,
    "kick_self_gain":exact_self_gain,
}


def run_pair(task,cfg,gain,pair):
    et,ed,st,sd=make_four(task,cfg,gain)
    for tile in (et,ed,st,sd):
        thermal_zero(tile)
        SURGERY[pair[0]](tile)
        SURGERY[pair[1]](tile)
    eti,edi,sti,sdi=DriftKickInterpreter(et),DriftKickInterpreter(ed),DriftKickInterpreter(st),DriftKickInterpreter(sd)
    _,_,c0=_eval_pair(eti,edi); _,_,sc0=_eval_pair(sti,sdi)
    exact=[c0]; shuffled=[sc0]
    perm=np.random.default_rng(1729).permutation(len(et.theta))
    for _ in range(30):
        rt=eti.execute(stochastic_forward=True); rd=edi.execute(stochastic_forward=True)
        gc=contrast_gradient(float(rt["objective"]),float(rd["objective"]),np.asarray(rt["credits"],dtype=float),np.asarray(rd["credits"],dtype=float))
        et.apply_credits(-gc,step_size=.20,normalize_rms=True); _sync_theta(et,ed)
        st.apply_credits(-gc[perm],step_size=.20,normalize_rms=True); _sync_theta(st,sd)
        _,_,cv=_eval_pair(eti,edi); _,_,scv=_eval_pair(sti,sdi)
        exact.append(cv); shuffled.append(scv)
    return {
        "pair":" + ".join(pair),
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
    for pair in PAIRS:
        row=run_pair(task,cfg,gain,pair); rows.append(row)
        print(f"{row['pair']:34s} DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']}",flush=True)
    passing=[r for r in rows if r["improvement"]>=.10 and r["final_win"]]
    decision={
        "pairs_clearing_seed2400_0p10":[r["pair"] for r in passing],
        "best_pair":max(rows,key=lambda r:r["improvement"])["pair"],
        "best_improvement":max(r["improvement"] for r in rows),
        "group_split_needed":not bool(passing),
    }
    print("decision",decision,flush=True)
    Path("v09-seed2400-pair-split.json").write_text(json.dumps({"experiment":"v09-seed2400-same-draw-pair-split","preregistration":"docs/CIRCUIT_V09_SEED2400_PAIR_SPLIT_PREREG.md","seed":SEED,"sense_gain":gain,"conditions":rows,"decision":decision},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
