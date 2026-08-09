"""Execute preregistered v0.6 near-zero refinement and combined backoff."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, damage_boundary, run_point


REFINE_SEEDS=tuple(range(940,946))
BACKOFF_SEEDS=tuple(range(946,952))
CONFIRM_SEEDS=tuple(range(952,962))
STATE_GRID=[0,1e-8,3e-8,1e-7,3e-7,1e-6,3e-6,1e-5]
OFFSET_GRID=[0,1e-5,3e-5,1e-4,3e-4,1e-3,2e-3,5e-3]
SCALE_GRID=[0,0.25,0.50,0.75,1.00]


def clean8():
    return replace(base_config(),weight_bits=8,dac_bits=8,adc_bits=8)


def scale_boundary(points):
    flags=[bool(p['summary']['qualified']) for p in points]
    prefix=[]
    for s,ok in zip(SCALE_GRID,flags):
        if not ok:break
        prefix.append(float(s))
    if not prefix:
        return {'pass_prefix':[],'boundary':None,'recommended':None,'first_failing':0.0}
    boundary=prefix[-1]
    first=None if len(prefix)==len(SCALE_GRID) else float(SCALE_GRID[len(prefix)])
    if len(prefix)==len(SCALE_GRID):rec=float(SCALE_GRID[-2])
    elif len(prefix)<=1:rec=float(prefix[0])
    else:rec=float(prefix[-2])
    return {'pass_prefix':prefix,'boundary':boundary,'recommended':rec,'first_failing':first}


def main():
    out={'experiment':'tw1a_hardware_envelope_order_v06','prereg':'docs/HARDWARE_ENVELOPE_ORDER_PREREG_V06.md','stage_a':{},'stage_b':{},'stage_c':None}
    base=clean8()

    state_pts=[]
    for v in STATE_GRID:
        state_pts.append(run_point(REFINE_SEEDS,replace(base,state_noise_std=float(v)),f'A state_noise_std={v}'))
    state_b=damage_boundary(STATE_GRID,state_pts)
    out['stage_a']['state_noise_std']={'points':state_pts,'boundary':state_b}
    print('A state',json.dumps(state_b,sort_keys=True),flush=True)

    offset_pts=[]
    for v in OFFSET_GRID:
        offset_pts.append(run_point(REFINE_SEEDS,replace(base,credit_offset_fraction=float(v)),f'A credit_offset_fraction={v}'))
    offset_b=damage_boundary(OFFSET_GRID,offset_pts)
    out['stage_a']['credit_offset_fraction']={'points':offset_pts,'boundary':offset_b}
    print('A offset',json.dumps(offset_b,sort_keys=True),flush=True)

    state_rec=float(state_b['recommended'] or 0.0)
    offset_rec=float(offset_b['recommended'] or 0.0)
    full={
        'leakage_rate':0.001,
        'leakage_cv':1.0,
        'mirror_error':0.30,
        'differential_pass_drift':0.0005,
        'credit_noise_fraction':0.50,
        'state_noise_std':state_rec,
        'credit_offset_fraction':offset_rec,
    }
    pts=[]
    for s in SCALE_GRID:
        cfg=replace(base,**{k:float(v)*float(s) for k,v in full.items()})
        pts.append(run_point(BACKOFF_SEEDS,cfg,f'B combined_scale={s}'))
    sb=scale_boundary(pts)
    out['stage_b']={'full_damage_vector':full,'points':pts,'scale_boundary':sb}
    print('B scale',json.dumps(sb,sort_keys=True),flush=True)

    rec_s=float(sb['recommended'] or 0.0)
    corner={k:float(v)*rec_s for k,v in full.items()}
    cfg=replace(base,**corner)
    final=run_point(CONFIRM_SEEDS,cfg,f'C combined_scale={rec_s}',final=True)
    out['stage_c']={'recommended_scale':rec_s,'corner':corner,'config':cfg.__dict__,'result':final}
    out['final_corner_earned']=bool(final['summary']['qualified'])
    p=Path('runs/hardware_envelope_order_v06.json');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'state_recommended':state_rec,'offset_recommended':offset_rec,'scale_boundary':sb,'final_corner_earned':out['final_corner_earned']},sort_keys=True),flush=True)
    print(f'wrote {p}',flush=True)

if __name__=='__main__':main()
