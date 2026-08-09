"""Execute preregistered full-update coherent drift-boundary experiment."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .full_update_coherent_drift_v01 import challenge_config, run_block


DEV_SEEDS=tuple(range(990,1000))
CONFIRM_SEEDS=tuple(range(1000,1010))
GRID=[0,0.00025,0.0005,0.001,0.0015,0.002,0.003,0.005]


def main():
    base=challenge_config()
    points=[]
    for drift in GRID:
        cfg=replace(base,differential_pass_drift=float(drift))
        p=run_block(DEV_SEEDS,cfg,f'DEV coherent drift={drift}')
        p['drift']=float(drift)
        points.append(p)

    prefix=[]
    for drift,p in zip(GRID,points):
        if not p['summary']['qualified']:
            break
        prefix.append(float(drift))

    boundary=prefix[-1] if prefix else None
    first_fail=None if len(prefix)==len(GRID) else float(GRID[len(prefix)])
    candidate=None
    if prefix:
        if len(prefix)==len(GRID):
            candidate=float(GRID[-2])
        elif len(prefix)==1:
            candidate=0.0
        else:
            candidate=float(prefix[-2])

    out={
        'experiment':'full_update_coherent_boundary_v01',
        'prereg':'docs/FULL_UPDATE_COHERENT_BOUNDARY_PREREG_V01.md',
        'development_seeds':list(DEV_SEEDS),
        'grid':GRID,
        'points':points,
        'pass_prefix':prefix,
        'development_boundary':boundary,
        'first_failing':first_fail,
        'fresh_candidate':candidate,
        'confirmation':None,
        'confirmed':False,
    }
    print('BOUNDARY',boundary,'first_fail',first_fail,'candidate',candidate,flush=True)

    if candidate is not None and candidate>0:
        cfg=replace(base,differential_pass_drift=float(candidate))
        confirm=run_block(CONFIRM_SEEDS,cfg,f'CONFIRM coherent drift={candidate}')
        out['confirmation']=confirm
        out['confirmed']=bool(confirm['summary']['qualified'])
    else:
        out['stop_reason']='NO_NONZERO_COHERENT_DRIFT_CANDIDATE'

    path=Path('runs/full_update_coherent_boundary_v01.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'boundary':boundary,'candidate':candidate,'confirmed':out['confirmed']},sort_keys=True),flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__':main()
