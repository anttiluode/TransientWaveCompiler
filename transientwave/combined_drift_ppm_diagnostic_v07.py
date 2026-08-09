"""Development-only ppm-scale differential drift refinement on spent seeds.

All non-drift terms remain fixed at the failed v0.7 50% combined corner.  The
previous refinement found that 0 passed while 2.5e-5 and above failed the final
predicate.  This probe resolves whether a finite ppm-scale pass prefix exists.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, run_point


SEEDS=tuple(range(970,980))
DRIFT_GRID=[0.0,1e-7,3e-7,1e-6,3e-6,1e-5,2e-5,2.5e-5]
FIXED={
    'weight_bits':8,
    'dac_bits':8,
    'adc_bits':8,
    'leakage_rate':0.0005,
    'leakage_cv':0.50,
    'mirror_error':0.15,
    'credit_noise_fraction':0.25,
    'credit_offset_fraction':0.00015,
    'state_noise_std':5e-9,
}


def main():
    base=replace(base_config(),**FIXED)
    points=[]
    for drift in DRIFT_GRID:
        p=run_point(SEEDS,replace(base,differential_pass_drift=drift),f'DEV ppm drift={drift}',final=True)
        p['drift']=drift
        points.append(p)
        weak=[(r['seed'],r['exact_improvement'],r['placement_gap']) for r in p['rows'] if r['exact_improvement']<0.10 or r['final_exact_contrast']<=r['final_shuffled_contrast']]
        print('  weak',[(s,round(dc,6),round(g,6)) for s,dc,g in weak],flush=True)
    flags=[bool(p['summary']['qualified']) for p in points]
    prefix=[]
    for d,ok in zip(DRIFT_GRID,flags):
        if not ok: break
        prefix.append(d)
    boundary=prefix[-1] if prefix else None
    first=None if len(prefix)==len(DRIFT_GRID) else DRIFT_GRID[len(prefix)]
    rec=None
    if prefix:
        if len(prefix)==len(DRIFT_GRID): rec=DRIFT_GRID[-2]
        elif len(prefix)==1: rec=0.0
        else: rec=prefix[-2]
    out={
        'experiment':'combined_drift_ppm_diagnostic_v07',
        'status':'development_only_spent_seeds',
        'seeds':list(SEEDS),
        'fixed_damage':FIXED,
        'grid':DRIFT_GRID,
        'points':points,
        'pass_prefix':prefix,
        'boundary_on_spent_seeds':boundary,
        'first_failing':first,
        'one_step_inward_candidate':rec,
    }
    path=Path('runs/combined_drift_ppm_diagnostic_v07.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('boundary',boundary,'first_fail',first,'candidate',rec,flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__': main()
