"""Execute preregistered full-update coherent 0.2% drift experiment."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from .full_update_coherent import run_order_contrast_training_full_coherent
from .hardware_envelope_order_v05 import base_config
from .order_benchmarks import compile_temporal_order_task


DEV_SEEDS=tuple(range(970,980))
CONFIRM_SEEDS=tuple(range(990,1000))


def challenge_config():
    return replace(
        base_config(),
        weight_bits=8,dac_bits=8,adc_bits=8,
        leakage_rate=0.0005,leakage_cv=0.50,
        mirror_error=0.15,differential_pass_drift=0.002,
        credit_noise_fraction=0.25,credit_offset_fraction=0.00015,
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


def run_block(seeds,cfg,label):
    rows=[]
    for seed in seeds:
        result,gain=run_order_contrast_training_full_coherent(
            compile_temporal_order_task(seed),replace(cfg,seed=1_500_000+seed),
            iterations=40,step_size=.20,normalize_rms=True,include_shuffle=True,
            shuffle_seed=1_600_000+seed,
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
    print(f"{label}: qualified={summary['qualified']} median={summary['median_exact_improvement']:+.4f} gap={summary['median_placement_gap']:+.4f} R10={summary['count_exact_ge_0p10']}/10 better={summary['exact_final_beats_shuffle_count']}/10",flush=True)
    print(' rows',[(r['seed'],round(r['exact_improvement'],6),round(r['placement_gap'],6)) for r in rows],flush=True)
    return {'label':label,'rows':rows,'summary':summary}


def main():
    cfg=challenge_config()
    out={'experiment':'full_update_coherent_drift_v01','prereg':'docs/FULL_UPDATE_COHERENT_DRIFT_PREREG_V01.md','config':cfg.__dict__,'stage_a':None,'stage_b':None}
    dev=run_block(DEV_SEEDS,cfg,'A spent full-update coherent drift')
    out['stage_a']=dev
    if not dev['summary']['qualified']:
        out['stop_reason']='FULL_UPDATE_COHERENCE_FAILED_ON_SPENT_SEEDS'
        out['confirmed']=False
        _write(out);return
    confirm=run_block(CONFIRM_SEEDS,cfg,'B fresh full-update coherent drift')
    out['stage_b']=confirm
    out['confirmed']=bool(confirm['summary']['qualified'])
    _write(out)


def _write(out):
    path=Path('runs/full_update_coherent_drift_v01.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'stop_reason':out.get('stop_reason'),'confirmed':out.get('confirmed',False)},sort_keys=True),flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
