"""Frozen diagnostics for failed fresh v0.9 bodies 2400..2409."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v08_self_thermal_corner import config_for as v08_config
from transientwave.circuit_emulator_v08_self_thermal import run_order_contrast_training as run_v08
from transientwave.circuit_emulator_v09_drift_kick import (
    TW1ADriftKickConfig,
    run_order_contrast_training as run_v09,
)
from transientwave.order_benchmarks import compile_temporal_order_task

SEEDS=list(range(2400,2410))
CONDITIONS=(
    "formal_reference",
    "no_drift_switch_residual",
    "no_drift_thermal",
    "no_edge_thermal",
    "no_kick_self_thermal",
    "all_thermal_zero",
    "all_thermal_1e-5",
    "v08_qualified_b1e-5",
)


def v09_config(seed:int,condition:str)->TW1ADriftKickConfig:
    base=v08_config(seed); kw=dict(base.__dict__)
    edge_b=2e-5; self_b=2e-5; drift_b=2e-5; common=5e-6; diff=5e-6
    if condition=="no_drift_switch_residual": common=diff=0.0
    elif condition=="no_drift_thermal": drift_b=0.0
    elif condition=="no_edge_thermal": edge_b=0.0
    elif condition=="no_kick_self_thermal": self_b=0.0
    elif condition=="all_thermal_zero": edge_b=self_b=drift_b=0.0
    elif condition=="all_thermal_1e-5": edge_b=self_b=drift_b=1e-5
    elif condition!="formal_reference": raise ValueError(condition)
    kw.update(
        edge_ktc_base_fraction=edge_b,
        self_ktc_base_fraction=self_b,
        kick_self_bits=10,
        kick_self_full_scale=0.125,
        drift_ktc_base_fraction=drift_b,
        drift_kick_common_rms_fraction=common,
        drift_kick_diff_rms_fraction=diff,
    )
    return TW1ADriftKickConfig(**kw)


def summarize(rows):
    imp=[r["improvement"] for r in rows]; gaps=[r["placement_gap"] for r in rows]
    n=sum(x>=.10 for x in imp); wins=sum(r["final_win"] for r in rows)
    mi=float(statistics.median(imp)); mg=float(statistics.median(gaps))
    return {
        "clean":bool(n==10 and wins==10 and mi>=.30 and mg>=.25),
        "improve_ge_0p10":n,
        "final_wins":wins,
        "median_improvement":mi,
        "minimum_improvement":float(min(imp)),
        "median_placement_gap":mg,
        "minimum_placement_gap":float(min(gaps)),
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--condition",choices=CONDITIONS,required=True); a=ap.parse_args()
    rows=[]
    print("condition",a.condition,flush=True)
    for seed in SEEDS:
        task=compile_temporal_order_task(seed)
        if a.condition=="v08_qualified_b1e-5":
            cfg=v08_config(seed); result,gain=run_v08(task,cfg,iterations=30,step_size=.20)
        else:
            cfg=v09_config(seed,a.condition); result,gain=run_v09(task,cfg,iterations=30,step_size=.20)
        row={"seed":seed,"sense_gain":gain,"improvement":float(result.exact_improvement),"placement_gap":float(result.placement_gap),"final_exact":float(result.exact_contrast[-1]),"final_shuffled":float(result.shuffled_contrast[-1]),"final_win":bool(result.exact_contrast[-1]>result.shuffled_contrast[-1])}
        rows.append(row)
        print(f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']}",flush=True)
    summary=summarize(rows); print("summary",summary,flush=True)
    out={"experiment":"v09-fresh-failure-diagnostic","condition":a.condition,"status":"spent-2400-2409","seeds":SEEDS,"summary":summary,"runs":rows}
    Path(f"v09-fresh-diag-{a.condition}.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
