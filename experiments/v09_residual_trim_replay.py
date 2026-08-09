"""Replay spent 2400..2409 with 0.10x of both switch-residual fields, full thermal on."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_seed2400_static_split import make_four
from v09_seed2400_switch_interaction import scale_switch_residuals, audit as residual_audit
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v08_common_diff import _eval_pair
from transientwave.circuit_emulator_v09_drift_kick import DriftKickInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta, contrast_gradient

SEEDS=list(range(2400,2410))
SCALE=0.10
IDEAL_LEARNABLE={2400,2401,2402,2403,2404,2406,2407,2408,2409}
IDEAL_IMPROVEMENT={
    2400:0.864382,2401:0.841869,2402:0.555789,2403:0.843161,2404:0.993097,
    2405:0.052904,2406:0.744431,2407:0.998321,2408:0.757526,2409:0.491374,
}


def run_seed(seed):
    task=compile_temporal_order_task(seed); cfg=formal_config(seed); gain=recommend_sense_gain(task,cfg)
    et,ed,st,sd=make_four(task,cfg,gain)
    for tile in (et,ed,st,sd): scale_switch_residuals(tile,SCALE)
    pa=residual_audit(et)
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
    improvement=float(exact[-1]-exact[0])
    return {
        "seed":seed,
        "sense_gain":gain,
        "physical":pa,
        "initial_exact":float(exact[0]),
        "final_exact":float(exact[-1]),
        "final_shuffled":float(shuffled[-1]),
        "improvement":improvement,
        "placement_gap":float(exact[-1]-shuffled[-1]),
        "final_win":bool(exact[-1]>shuffled[-1]),
        "ideal_improvement":IDEAL_IMPROVEMENT[seed],
        "ideal_learnable":seed in IDEAL_LEARNABLE,
        "hardware_over_ideal_improvement":float(improvement/IDEAL_IMPROVEMENT[seed]),
    }


def main():
    rows=[]
    for seed in SEEDS:
        r=run_seed(seed); rows.append(r); p=r["physical"]
        print(f"{seed}: DeltaC={r['improvement']:+.6f} gap={r['placement_gap']:+.6f} win={r['final_win']} hw/ideal={r['hardware_over_ideal_improvement']:.3f} edgeA={p['edge_a_rms_fraction']*1e6:.2f}ppm driftC={p['drift_c_rms_fraction']*1e6:.2f}ppm",flush=True)
    imp=[r["improvement"] for r in rows]; gaps=[r["placement_gap"] for r in rows]
    eligible=[r for r in rows if r["ideal_learnable"]]
    tail=next(r for r in rows if r["seed"]==2405)
    summary={
        "historical_improve_ge_0p10":sum(x>=.10 for x in imp),
        "final_wins":sum(r["final_win"] for r in rows),
        "median_improvement":float(statistics.median(imp)),
        "minimum_improvement":float(min(imp)),
        "median_placement_gap":float(statistics.median(gaps)),
        "minimum_placement_gap":float(min(gaps)),
        "ideal_learnable_count":len(eligible),
        "ideal_learnable_improve_ge_0p10":sum(r["improvement"]>=.10 for r in eligible),
        "minimum_ideal_learnable_improvement":float(min(r["improvement"] for r in eligible)),
        "median_hw_over_ideal_improvement":float(statistics.median(r["hardware_over_ideal_improvement"] for r in eligible)),
        "tail_2405_improvement":tail["improvement"],
        "tail_2405_ideal_improvement":tail["ideal_improvement"],
        "tail_2405_final_win":tail["final_win"],
        "tail_2405_placement_gap":tail["placement_gap"],
    }
    decision={
        "seed2400_rescued":next(r for r in rows if r["seed"]==2400)["improvement"]>=.10,
        "all_ideal_learnable_ge_0p10":summary["ideal_learnable_improve_ge_0p10"]==len(eligible),
        "node_level_residual_trim_candidate":bool(next(r for r in rows if r["seed"]==2400)["improvement"]>=.10 and summary["ideal_learnable_improve_ge_0p10"]==len(eligible)),
        "fresh_seed_authorized":False,
    }
    print("summary",summary,flush=True); print("decision",decision,flush=True)
    Path("v09-residual-trim-replay.json").write_text(json.dumps({"experiment":"v09-0p10-switch-residual-spent-cohort-replay","preregistration":"docs/CIRCUIT_V09_RESIDUAL_TRIM_REPLAY_PREREG.md","scale":SCALE,"seeds":SEEDS,"summary":summary,"decision":decision,"runs":rows},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
