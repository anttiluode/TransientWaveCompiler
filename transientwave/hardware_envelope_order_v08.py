"""Execute preregistered v0.8 10-ppm simultaneous corner confirmation."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v05 import base_config, run_point


SEEDS=tuple(range(980,990))
CORNER={
    'weight_bits':8,
    'dac_bits':8,
    'adc_bits':8,
    'leakage_rate':0.0005,
    'leakage_cv':0.50,
    'mirror_error':0.15,
    'differential_pass_drift':1e-5,
    'credit_noise_fraction':0.25,
    'credit_offset_fraction':0.00015,
    'state_noise_std':5e-9,
}


def main():
    cfg=replace(base_config(),**CORNER)
    result=run_point(SEEDS,cfg,'v0.8 frozen 10ppm simultaneous corner',final=True)
    out={
        'experiment':'tw1a_hardware_envelope_order_v08',
        'prereg':'docs/HARDWARE_ENVELOPE_ORDER_PREREG_V08.md',
        'seeds':list(SEEDS),
        'corner':CORNER,
        'result':result,
        'final_corner_earned':bool(result['summary']['qualified']),
    }
    path=Path('runs/hardware_envelope_order_v08.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('\nFINAL',json.dumps({'final_corner_earned':out['final_corner_earned'],'summary':result['summary']},sort_keys=True),flush=True)
    print('rows',[(r['seed'],round(r['exact_improvement'],6),round(r['placement_gap'],6)) for r in result['rows']],flush=True)
    print(f'wrote {path}',flush=True)

if __name__=='__main__': main()
