"""Development-only leave-one-out diagnosis for the coherent zero-drift tail.

Uses only already-spent seeds 990..999.  Full-update coherent drift is fixed at
zero and one remaining simultaneous damage term is removed at a time.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .full_update_coherent_drift_v01 import run_block
from .hardware_envelope_order_v05 import base_config


SEEDS=tuple(range(990,1000))
FULL={
    'weight_bits':8,
    'dac_bits':8,
    'adc_bits':8,
    'leakage_rate':0.0005,
    'leakage_cv':0.50,
    'mirror_error':0.15,
    'differential_pass_drift':0.0,
    'credit_noise_fraction':0.25,
    'credit_offset_fraction':0.00015,
    'state_noise_std':5e-9,
}
REMOVE=['leakage_rate','leakage_cv','mirror_error','credit_noise_fraction','credit_offset_fraction','state_noise_std']


def main():
    base=replace(base_config(),**FULL)
    points={}
    points['full_zero_drift']=run_block(SEEDS,base,'DEV coherent baseline full')
    for key in REMOVE:
        kw=dict(FULL);kw[key]=0.0
        points[f'without_{key}']=run_block(SEEDS,replace(base_config(),**kw),f'DEV without {key}')
    ranked=[]
    ref=points['full_zero_drift']['summary']
    for key in REMOVE:
        s=points[f'without_{key}']['summary']
        ranked.append({
            'removed':key,
            'qualified':s['qualified'],
            'delta_R10':s['count_exact_ge_0p10']-ref['count_exact_ge_0p10'],
            'delta_better':s['exact_final_beats_shuffle_count']-ref['exact_final_beats_shuffle_count'],
            'delta_median_exact':s['median_exact_improvement']-ref['median_exact_improvement'],
            'delta_median_gap':s['median_placement_gap']-ref['median_placement_gap'],
            'all_positive':s['all_positive'],
        })
    ranked.sort(key=lambda x:(x['qualified'],x['all_positive'],x['delta_R10'],x['delta_median_exact']),reverse=True)
    out={'experiment':'coherent_baseline_loo_diagnostic','status':'development_only_spent_seeds','seeds':list(SEEDS),'full_config':FULL,'points':points,'ranked_removals':ranked}
    print('ranked',ranked,flush=True)
    path=Path('runs/coherent_baseline_loo_diagnostic.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
