"""Development-only differential-drift refinement on spent v0.7 seeds.

The v0.7 leave-one-out diagnostic identified differential PLUS/MINUS pass drift
as the only single damage term whose removal restored the final predicate. Keep
all other 50% corner damages fixed and refine only drift on the already-spent
970..979 block. This chooses a candidate for a new preregistration only.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, run_point


SEEDS=tuple(range(970,980))
DRIFT_GRID=[0.0,2.5e-5,5e-5,1e-4,1.5e-4,2e-4,2.5e-4]
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
        cfg=replace(base,differential_pass_drift=drift)
        p=run_point(SEEDS,cfg,f'DEV combined drift={drift}',final=True)
        p['drift']=drift
        points.append(p)
        print('  rows',[(r['seed'],round(r['exact_improvement'],6),round(r['placement_gap'],6)) for r in p['rows']],flush=True)

    flags=[bool(p['summary']['qualified']) for p in points]
    prefix=[]
    for drift,ok in zip(DRIFT_GRID,flags):
        if not ok:break
        prefix.append(drift)
    boundary=prefix[-1] if prefix else None
    first_fail=None if len(prefix)==len(DRIFT_GRID) else DRIFT_GRID[len(prefix)]
    if not prefix:
        recommended=None
    elif len(prefix)==len(DRIFT_GRID):
        recommended=DRIFT_GRID[-2]
    elif len(prefix)==1:
        recommended=prefix[0]
    else:
        recommended=prefix[-2]

    out={
        'experiment':'combined_drift_refine_diagnostic_v07',
        'status':'development_only_spent_seeds',
        'seeds':list(SEEDS),
        'fixed_damage':FIXED,
        'drift_grid':DRIFT_GRID,
        'points':points,
        'pass_prefix':prefix,
        'boundary_on_spent_seeds':boundary,
        'first_failing':first_fail,
        'one_step_inward_candidate':recommended,
    }
    path=Path('runs/combined_drift_refine_diagnostic_v07.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('boundary',boundary,'first_fail',first_fail,'candidate',recommended,flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
