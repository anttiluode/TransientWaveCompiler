"""Development-only replay of spent v0.4 seeds under edge-cell quantization."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from .emulator import TW1APhysicalTileConfig
from .emulator_v05 import run_order_contrast_training
from .order_benchmarks import compile_temporal_order_task


SEEDS = tuple(range(880, 886))
CONFIGS = {
    "q9_d5_a7_clean": dict(weight_bits=9, dac_bits=5, adc_bits=7),
    "q8_d8_a8_clean": dict(weight_bits=8, dac_bits=8, adc_bits=8),
    "q8_d8_a8_nominal": dict(
        weight_bits=8,
        dac_bits=8,
        adc_bits=8,
        mirror_error=0.05,
        differential_pass_drift=0.002,
        credit_noise_fraction=0.05,
    ),
}


def base_config() -> TW1APhysicalTileConfig:
    return TW1APhysicalTileConfig(
        weight_bits=None,
        weight_quantizer="uniform",
        dac_bits=None,
        adc_bits=None,
        state_noise_std=0.0,
        state_full_scale=20.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.0,
        differential_pass_drift=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        adc_full_scale=2.0,
        seed=0,
    )


def summarize(rows):
    exact=np.asarray([r["exact_improvement"] for r in rows],float)
    sh=np.asarray([r["shuffled_improvement"] for r in rows],float)
    ef=np.asarray([r["final_exact_contrast"] for r in rows],float)
    sf=np.asarray([r["final_shuffled_contrast"] for r in rows],float)
    return {
        "all_positive": bool(np.all(exact>0)),
        "count_exact_ge_0p10": int(np.sum(exact>=0.10)),
        "median_exact_improvement": float(np.median(exact)),
        "exact_final_beats_shuffle_count": int(np.sum(ef>sf)),
        "median_placement_gap": float(np.median(exact-sh)),
        "qualified_v04_predicate": bool(
            np.all(exact>0) and np.sum(exact>=0.10)>=5 and np.median(exact)>=0.15
            and np.sum(ef>sf)>=5 and np.median(exact-sh)>=0.10
        ),
    }


def main():
    out={"experiment":"edge_cell_quantization_diagnostic_v05","status":"development_only_spent_seeds","seeds":list(SEEDS),"configs":{}}
    for name,kw in CONFIGS.items():
        cfg=replace(base_config(),**kw)
        rows=[]
        for seed in SEEDS:
            local=replace(cfg,seed=500_000+seed)
            result,gain=run_order_contrast_training(
                compile_temporal_order_task(seed),local,
                iterations=40,step_size=0.20,normalize_rms=True,
                include_shuffle=True,shuffle_seed=600_000+seed,
            )
            row={
                "seed":seed,"sense_gain":gain,
                "initial_contrast":result.exact_contrast[0],
                "final_exact_contrast":result.exact_contrast[-1],
                "final_shuffled_contrast":result.shuffled_contrast[-1],
                "exact_improvement":result.exact_improvement,
                "shuffled_improvement":result.shuffled_improvement,
                "placement_gap":result.placement_gap,
            }
            rows.append(row)
        summary=summarize(rows)
        out["configs"][name]={"config":cfg.__dict__,"rows":rows,"summary":summary}
        print(name,summary,flush=True)
        print([(r['seed'],round(r['exact_improvement'],4),round(r['placement_gap'],4)) for r in rows],flush=True)
    path=Path('runs/edge_cell_quantization_diagnostic_v05.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'wrote {path}',flush=True)

if __name__=='__main__':
    main()
