"""Development-only leave-one-damage-out diagnosis on spent v0.7 seeds.

The v0.7 50% simultaneous corner failed on seeds 970..979. This script keeps
that corner fixed and removes exactly one damage component at a time. It is
mechanism diagnosis only; all seeds are already spent.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, run_point


SEEDS=tuple(range(970,980))
FULL={
    'leakage_rate':0.0005,
    'leakage_cv':0.50,
    'mirror_error':0.15,
    'differential_pass_drift':0.00025,
    'credit_noise_fraction':0.25,
    'credit_offset_fraction':0.00015,
    'state_noise_std':5e-9,
}
REMOVE_ORDER=[
    'leakage_rate',
    'leakage_cv',
    'mirror_error',
    'differential_pass_drift',
    'credit_noise_fraction',
    'credit_offset_fraction',
    'state_noise_std',
]


def main():
    clean=replace(base_config(),weight_bits=8,dac_bits=8,adc_bits=8)
    configs=[]
    configs.append(('clean',{}))
    configs.append(('full_50pct',dict(FULL)))
    for key in REMOVE_ORDER:
        kw=dict(FULL);kw[key]=0.0
        configs.append((f'without_{key}',kw))

    out={'experiment':'combined_damage_loo_diagnostic_v07','status':'development_only_spent_seeds','seeds':list(SEEDS),'full_corner':FULL,'points':{}}
    for name,kw in configs:
        cfg=replace(clean,**kw)
        p=run_point(SEEDS,cfg,f'DEV {name}',final=True)
        out['points'][name]=p
        weak=[(r['seed'],r['exact_improvement'],r['placement_gap']) for r in p['rows'] if r['exact_improvement']<0.10 or r['final_exact_contrast']<=r['final_shuffled_contrast']]
        print(name,p['summary'],flush=True)
        print('  weak',[(s,round(dc,6),round(g,6)) for s,dc,g in weak],flush=True)

    base=out['points']['full_50pct']['summary']
    ranked=[]
    for key in REMOVE_ORDER:
        s=out['points'][f'without_{key}']['summary']
        ranked.append({
            'removed':key,
            'qualified':s['qualified'],
            'delta_median_exact':s['median_exact_improvement']-base['median_exact_improvement'],
            'delta_median_gap':s['median_placement_gap']-base['median_placement_gap'],
            'delta_R10':s['count_exact_ge_0p10']-base['count_exact_ge_0p10'],
            'delta_better':s['exact_final_beats_shuffle_count']-base['exact_final_beats_shuffle_count'],
            'all_positive':s['all_positive'],
        })
    ranked.sort(key=lambda x:(x['qualified'],x['delta_R10'],x['delta_better'],x['delta_median_exact']),reverse=True)
    out['ranked_removals']=ranked
    print('ranked',ranked,flush=True)
    path=Path('runs/combined_damage_loo_diagnostic_v07.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
