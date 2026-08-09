"""Development-only replay of the spent v0.6 final seeds at lower damage scales.

Uses only already-consumed seeds 952..961.  This may choose a candidate scale
for a new preregistration but is not confirmatory evidence.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, run_point


SEEDS=tuple(range(952,962))
SCALES=[0.0,0.25,0.50,0.75]
FULL={
    'leakage_rate':0.001,
    'leakage_cv':1.0,
    'mirror_error':0.30,
    'differential_pass_drift':0.0005,
    'credit_noise_fraction':0.50,
    'state_noise_std':1e-8,
    'credit_offset_fraction':0.0003,
}


def main():
    clean=replace(base_config(),weight_bits=8,dac_bits=8,adc_bits=8)
    points=[]
    for s in SCALES:
        cfg=replace(clean,**{k:v*s for k,v in FULL.items()})
        p=run_point(SEEDS,cfg,f'DEV spent-final combined_scale={s}',final=True)
        p['scale']=s
        points.append(p)
        print('  rows',[(r['seed'],round(r['exact_improvement'],6),round(r['placement_gap'],6)) for r in p['rows']],flush=True)
    passing=[p for p in points if p['summary']['qualified']]
    candidate=max((p['scale'] for p in passing),default=None)
    out={
        'experiment':'combined_backoff_tail_diagnostic_v06',
        'status':'development_only_spent_seeds',
        'seeds':list(SEEDS),
        'full_damage_vector':FULL,
        'points':points,
        'largest_passing_scale_on_spent_seeds':candidate,
    }
    path=Path('runs/combined_backoff_tail_diagnostic_v06.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('largest passing',candidate,flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
