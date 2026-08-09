"""Development-only precision sweep under corrected rank-one edge-cell hardware.

Uses only already-spent v0.4 seeds 880..885.  Its purpose is to decide whether
a monotone `bits >= B` preregistration is scientifically reasonable after the
v0.5 hardware-semantic correction.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from .edge_cell_quantization_diagnostic_v05 import base_config
from .emulator_v05 import run_order_contrast_training
from .order_benchmarks import compile_temporal_order_task


SEEDS=tuple(range(880,886))
BITS=[4,5,6,7,8,9,10,12]


def run(cfg,label):
    rows=[]
    for seed in SEEDS:
        result,gain=run_order_contrast_training(
            compile_temporal_order_task(seed),replace(cfg,seed=700_000+seed),
            iterations=40,step_size=0.20,normalize_rms=True,
            include_shuffle=True,shuffle_seed=800_000+seed,
        )
        rows.append({
            'seed':seed,'sense_gain':gain,
            'exact_improvement':result.exact_improvement,
            'shuffled_improvement':result.shuffled_improvement,
            'final_exact_contrast':result.exact_contrast[-1],
            'final_shuffled_contrast':result.shuffled_contrast[-1],
        })
    e=np.asarray([r['exact_improvement'] for r in rows]);s=np.asarray([r['shuffled_improvement'] for r in rows])
    ef=np.asarray([r['final_exact_contrast'] for r in rows]);sf=np.asarray([r['final_shuffled_contrast'] for r in rows])
    summary={
        'all_positive':bool(np.all(e>0)),
        'count_exact_ge_0p10':int(np.sum(e>=.10)),
        'median_exact_improvement':float(np.median(e)),
        'exact_final_beats_shuffle_count':int(np.sum(ef>sf)),
        'median_placement_gap':float(np.median(e-s)),
    }
    summary['qualified']=bool(summary['all_positive'] and summary['count_exact_ge_0p10']>=5 and summary['median_exact_improvement']>=.15 and summary['exact_final_beats_shuffle_count']>=5 and summary['median_placement_gap']>=.10)
    print(label,summary,flush=True)
    return {'label':label,'config':cfg.__dict__,'rows':rows,'summary':summary}


def main():
    out={'experiment':'precision_monotonicity_diagnostic_v05','status':'development_only_spent_seeds','seeds':list(SEEDS),'axes':{}}
    for axis in ('weight_bits','dac_bits','adc_bits'):
        pts=[]
        for bit in BITS:
            kw={'weight_bits':None,'dac_bits':None,'adc_bits':None}
            kw[axis]=bit
            pts.append(run(replace(base_config(),**kw),f'{axis}={bit}'))
        flags=[p['summary']['qualified'] for p in pts]
        stable=None
        for i,b in enumerate(BITS):
            if all(flags[i:]):
                stable=b;break
        out['axes'][axis]={'points':pts,'stable_minimum_on_spent_seeds':stable,'flags':flags}
        print(axis,'flags',list(zip(BITS,flags)),'stable',stable,flush=True)
    path=Path('runs/precision_monotonicity_diagnostic_v05.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
