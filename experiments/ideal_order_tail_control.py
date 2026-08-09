"""Ideal exact physical-credit control for spent task seeds 2400..2409."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from transientwave.emulator import TW1APhysicalTileConfig
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import run_order_contrast_training

SEEDS=list(range(2400,2410))

IDEAL=TW1APhysicalTileConfig(
    weight_bits=None,
    dac_bits=None,
    adc_bits=None,
    state_noise_std=0.0,
    state_full_scale=2.0,
    clip_state=False,
    leakage_rate=0.0,
    leakage_cv=0.0,
    mirror_error=0.0,
    differential_pass_drift=0.0,
    credit_offset_fraction=0.0,
    credit_noise_fraction=0.0,
    adc_full_scale=2.0,
    seed=0,
)


def main():
    rows=[]
    for seed in SEEDS:
        cfg=TW1APhysicalTileConfig(**{**IDEAL.__dict__,"seed":seed})
        r=run_order_contrast_training(compile_temporal_order_task(seed),cfg,iterations=30,step_size=.20)
        row={"seed":seed,"improvement":float(r.exact_improvement),"placement_gap":float(r.placement_gap),"final_exact":float(r.exact_contrast[-1]),"final_shuffled":float(r.shuffled_contrast[-1]),"final_win":bool(r.exact_contrast[-1]>r.shuffled_contrast[-1])}; rows.append(row)
        print(f"{seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']}",flush=True)
    imp=[r["improvement"] for r in rows]; gaps=[r["placement_gap"] for r in rows]
    summary={"improve_ge_0p10":sum(x>=.10 for x in imp),"final_wins":sum(r["final_win"] for r in rows),"median_improvement":float(statistics.median(imp)),"minimum_improvement":float(min(imp)),"median_placement_gap":float(statistics.median(gaps)),"minimum_placement_gap":float(min(gaps))}
    print("summary",summary,flush=True)
    Path("ideal-order-tail-control.json").write_text(json.dumps({"experiment":"ideal-exact-physical-credit-tail-control","status":"spent-2400-2409","config":"no quantization/noise/leakage/mirror error/pass drift/credit error; unclipped","updates":30,"step_size":.20,"summary":summary,"runs":rows},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
