"""Execute the preregistered rank-one edge-cell TW-1A v0.5 envelope."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import numpy as np

from .emulator import TW1APhysicalTileConfig
from .emulator_v05 import run_order_contrast_training
from .hardware_envelope_order_v03 import DAMAGE_GRIDS, LEAKAGE_CV_GRID, damage_boundary
from .order_benchmarks import compile_temporal_order_task


BIT_GRID=[4,5,6,7,8,9,10,12]
PRECISION_SEEDS=tuple(range(910,916))
JOINT_SEEDS=tuple(range(916,922))
TOLERANCE_SEEDS=tuple(range(922,928))
CONFIRM_SEEDS=tuple(range(930,940))
_TASKS:dict[int,dict[str,Any]]={}


def task(seed:int)->dict[str,Any]:
    if seed not in _TASKS:
        _TASKS[seed]=compile_temporal_order_task(seed)
    return _TASKS[seed]


def base_config()->TW1APhysicalTileConfig:
    return TW1APhysicalTileConfig(
        weight_bits=None,weight_quantizer='uniform',dac_bits=None,adc_bits=None,
        state_noise_std=0.0,state_full_scale=20.0,clip_state=True,
        leakage_rate=0.0,leakage_cv=0.0,mirror_error=0.0,
        differential_pass_drift=0.0,credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,adc_full_scale=2.0,seed=0,
    )


def qualify(rows:list[dict[str,Any]],*,final:bool=False)->dict[str,Any]:
    e=np.asarray([r['exact_improvement'] for r in rows],float)
    s=np.asarray([r['shuffled_improvement'] for r in rows],float)
    ef=np.asarray([r['final_exact_contrast'] for r in rows],float)
    sf=np.asarray([r['final_shuffled_contrast'] for r in rows],float)
    needed=8 if final else 5
    q={
        'all_positive':bool(np.all(e>0)),
        'count_exact_ge_0p10':int(np.sum(e>=.10)),
        'median_exact_improvement':float(np.median(e)),
        'exact_final_beats_shuffle_count':int(np.sum(ef>sf)),
        'median_placement_gap':float(np.median(e-s)),
        'all_finite':bool(all(r['finite'] for r in rows)),
    }
    q['qualified']=bool(q['all_positive'] and q['count_exact_ge_0p10']>=needed and q['median_exact_improvement']>=.15 and q['exact_final_beats_shuffle_count']>=needed and q['median_placement_gap']>=.10 and q['all_finite'])
    return q


def run_point(seeds,config,label,*,final=False):
    rows=[]
    for seed in seeds:
        result,gain=run_order_contrast_training(
            task(seed),replace(config,seed=900_000+seed),
            iterations=40,step_size=.20,normalize_rms=True,include_shuffle=True,
            shuffle_seed=1_000_000+seed,
        )
        rows.append({
            'seed':seed,'sense_gain':gain,
            'initial_contrast':result.exact_contrast[0],
            'final_exact_contrast':result.exact_contrast[-1],
            'final_shuffled_contrast':result.shuffled_contrast[-1],
            'exact_improvement':result.exact_improvement,
            'shuffled_improvement':result.shuffled_improvement,
            'placement_gap':result.placement_gap,
            'finite':bool(np.all(np.isfinite(result.exact_contrast)) and np.all(np.isfinite(result.shuffled_contrast)) and np.all(np.isfinite(result.final_theta)) and np.all(np.isfinite(result.final_theta_shuffled)) and np.all(np.isfinite(result.combined_credit_rms))),
        })
    q=qualify(rows,final=final)
    print(f"{label}: qualified={q['qualified']} median={q['median_exact_improvement']:+.4f} gap={q['median_placement_gap']:+.4f} R10={q['count_exact_ge_0p10']}/{len(seeds)} better={q['exact_final_beats_shuffle_count']}/{len(seeds)}",flush=True)
    return {'label':label,'config':config.__dict__,'rows':rows,'summary':q}


def stable_minimum(points):
    flags=[bool(p['summary']['qualified']) for p in points]
    for i,b in enumerate(BIT_GRID):
        if all(flags[i:]):return b
    return None


def next_bit(b):
    i=BIT_GRID.index(b);return BIT_GRID[min(i+1,len(BIT_GRID)-1)]


def main():
    out={'experiment':'tw1a_hardware_envelope_order_v05','prereg':'docs/HARDWARE_ENVELOPE_ORDER_PREREG_V05.md','stage_a':{},'stage_b':{},'stage_c':None}
    minima={};margins={}
    for axis in ('weight_bits','dac_bits','adc_bits'):
        pts=[]
        for bit in BIT_GRID:
            kw={'weight_bits':None,'dac_bits':None,'adc_bits':None};kw[axis]=bit
            pts.append(run_point(PRECISION_SEEDS,replace(base_config(),**kw),f'A {axis}={bit}'))
        m=stable_minimum(pts);minima[axis]=m;margins[axis]=None if m is None else next_bit(m)
        out['stage_a'][axis]={'points':pts,'stable_minimum':m,'one_step_margin_bits':margins[axis]}
        print(f'A {axis}: stable_min={m} margin={margins[axis]}',flush=True)
    if any(v is None for v in minima.values()):
        out['stop_reason']='NO_STABLE_PRECISION_SUFFIX';out['final_envelope_earned']=False;_write(out);return

    clean=replace(base_config(),weight_bits=8,dac_bits=8,adc_bits=8)
    joint=run_point(JOINT_SEEDS,clean,'A4 clean 8/8/8')
    nominal=run_point(JOINT_SEEDS,replace(clean,mirror_error=.05,differential_pass_drift=.002,credit_noise_fraction=.05),'A4 nominal 8/8/8 + errors')
    out['stage_a']['clean_8bit_joint']=joint
    out['stage_a']['nominal_requested']=nominal
    out['stage_a']['precision_minima']=minima
    out['stage_a']['one_step_margin_bits']=margins
    if not joint['summary']['qualified']:
        out['stop_reason']='CLEAN_8BIT_JOINT_FAILED';out['final_envelope_earned']=False;_write(out);return

    boundaries={}
    for axis,vals in DAMAGE_GRIDS.items():
        pts=[]
        for v in vals:
            pts.append(run_point(TOLERANCE_SEEDS,replace(clean,**{axis:float(v)}),f'B {axis}={v}'))
        b=damage_boundary(vals,pts);boundaries[axis]=b
        out['stage_b'][axis]={'points':pts,'boundary':b}
        print(f'B {axis}: {json.dumps(b,sort_keys=True)}',flush=True)

    rec_leak=boundaries['leakage_rate']['recommended']
    if rec_leak is None or float(rec_leak)==0.0:
        b={'boundary':None,'recommended':None,'first_failing':None,'pass_prefix':[]}
        boundaries['leakage_cv']=b
        out['stage_b']['leakage_cv']={'resolved':False,'reason':'recommended leakage rate is zero','boundary':b}
    else:
        pts=[]
        for v in LEAKAGE_CV_GRID:
            pts.append(run_point(TOLERANCE_SEEDS,replace(clean,leakage_rate=float(rec_leak),leakage_cv=float(v)),f'B leakage_cv={v}'))
        b=damage_boundary(LEAKAGE_CV_GRID,pts);boundaries['leakage_cv']=b
        out['stage_b']['leakage_cv']={'resolved':True,'fixed_leakage_rate':rec_leak,'points':pts,'boundary':b}
        print(f'B leakage_cv: {json.dumps(b,sort_keys=True)}',flush=True)

    rec={k:v.get('recommended') for k,v in boundaries.items()}
    corner=replace(clean,
        leakage_rate=float(rec['leakage_rate'] or 0),
        leakage_cv=float(rec['leakage_cv'] or 0),
        mirror_error=float(rec['mirror_error'] or 0),
        differential_pass_drift=float(rec['differential_pass_drift'] or 0),
        state_noise_std=float(rec['state_noise_std'] or 0),
        credit_noise_fraction=float(rec['credit_noise_fraction'] or 0),
        credit_offset_fraction=float(rec['credit_offset_fraction'] or 0),
    )
    combined=run_point(CONFIRM_SEEDS,corner,'C combined conservative 8/8/8',final=True)
    out['stage_c']={'recommended_damage':rec,'config':corner.__dict__,'result':combined}
    out['final_envelope_earned']=bool(combined['summary']['qualified'])
    _write(out)


def _write(out):
    p=Path('runs/hardware_envelope_order_v05.json');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'stop_reason':out.get('stop_reason'),'clean8':out.get('stage_a',{}).get('clean_8bit_joint',{}).get('summary',{}).get('qualified'),'nominal':out.get('stage_a',{}).get('nominal_requested',{}).get('summary',{}).get('qualified'),'final_envelope_earned':out.get('final_envelope_earned',False)},sort_keys=True),flush=True)
    print(f'wrote {p}',flush=True)

if __name__=='__main__':main()
