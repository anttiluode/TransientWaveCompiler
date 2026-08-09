"""Execute the preregistered small-N differential-drift averaging kill test."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from .drift_averaging import run_order_contrast_training_repeated
from .hardware_envelope_order_v05 import base_config
from .order_benchmarks import compile_temporal_order_task


SEEDS=tuple(range(970,980))
REPEATS=[1,2,4,8,16]


def config():
    return replace(
        base_config(),
        weight_bits=8,
        dac_bits=8,
        adc_bits=8,
        leakage_rate=0.0005,
        leakage_cv=0.50,
        mirror_error=0.15,
        differential_pass_drift=0.002,
        credit_noise_fraction=0.25,
        credit_offset_fraction=0.00015,
        state_noise_std=5e-9,
    )


def summarize(rows):
    e=np.asarray([r['exact_improvement'] for r in rows],float)
    s=np.asarray([r['shuffled_improvement'] for r in rows],float)
    ef=np.asarray([r['final_exact_contrast'] for r in rows],float)
    sf=np.asarray([r['final_shuffled_contrast'] for r in rows],float)
    q={
        'all_positive':bool(np.all(e>0)),
        'count_exact_ge_0p10':int(np.sum(e>=.10)),
        'median_exact_improvement':float(np.median(e)),
        'exact_final_beats_shuffle_count':int(np.sum(ef>sf)),
        'median_placement_gap':float(np.median(e-s)),
        'all_finite':bool(np.all(np.isfinite(e)) and np.all(np.isfinite(s)) and np.all(np.isfinite(ef)) and np.all(np.isfinite(sf))),
    }
    q['qualified']=bool(q['all_positive'] and q['count_exact_ge_0p10']>=8 and q['median_exact_improvement']>=.15 and q['exact_final_beats_shuffle_count']>=8 and q['median_placement_gap']>=.10 and q['all_finite'])
    return q


def main():
    cfg=config()
    out={'experiment':'drift_averaging_kill_v01','prereg':'docs/DRIFT_AVERAGING_KILL_PREREG_V01.md','status':'development_only_spent_seeds','seeds':list(SEEDS),'config':cfg.__dict__,'points':[]}
    for n in REPEATS:
        rows=[]
        for seed in SEEDS:
            result,gain=run_order_contrast_training_repeated(
                compile_temporal_order_task(seed),
                replace(cfg,seed=1_100_000+seed),
                repeats=n,
                iterations=40,
                step_size=.20,
                normalize_rms=True,
                include_shuffle=True,
                shuffle_seed=1_200_000+seed,
            )
            rows.append({
                'seed':seed,'sense_gain':gain,
                'initial_contrast':result.exact_contrast[0],
                'final_exact_contrast':result.exact_contrast[-1],
                'final_shuffled_contrast':result.shuffled_contrast[-1],
                'exact_improvement':result.exact_improvement,
                'shuffled_improvement':result.shuffled_improvement,
                'placement_gap':result.placement_gap,
            })
        summary=summarize(rows)
        point={'repeats':n,'physical_traversals_per_contrast_update':8*n,'rows':rows,'summary':summary}
        out['points'].append(point)
        print(f"N={n}: qualified={summary['qualified']} median={summary['median_exact_improvement']:+.4f} gap={summary['median_placement_gap']:+.4f} R10={summary['count_exact_ge_0p10']}/10 better={summary['exact_final_beats_shuffle_count']}/10",flush=True)
        print(' weak',[(r['seed'],round(r['exact_improvement'],5),round(r['placement_gap'],5)) for r in rows if r['exact_improvement']<.10 or r['final_exact_contrast']<=r['final_shuffled_contrast']],flush=True)
    passing=[p['repeats'] for p in out['points'] if p['summary']['qualified']]
    out['small_n_survives']=bool(passing)
    out['smallest_qualifying_repeats']=min(passing) if passing else None
    path=Path('runs/drift_averaging_kill_v01.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'small_n_survives':out['small_n_survives'],'smallest_qualifying_repeats':out['smallest_qualifying_repeats']},sort_keys=True),flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
