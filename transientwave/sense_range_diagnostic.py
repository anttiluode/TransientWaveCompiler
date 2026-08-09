"""Development-only diagnosis of the v0.2 fixed sense-range failure.

Uses already-inspected seeds 820-824. No threshold or novelty claim may be
frozen from this file.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .benchmarks import compile_irregular_arbor
from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig
from .emulator_v02 import TW1APhysicalTile, run_closed_loop_training, signed_midtread_quantize


SEEDS = range(820, 825)


def cfg(seed: int, adc_bits):
    return TW1APhysicalTileConfig(
        weight_bits=12,
        weight_quantizer="uniform",
        dac_bits=12,
        adc_bits=adc_bits,
        state_noise_std=0.0,
        state_full_scale=2.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.05,
        differential_pass_drift=0.002,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.05,
        adc_full_scale=2.0,
        seed=50_000 + seed,
    )


def one(seed: int):
    manifest = compile_irregular_arbor(seed)

    # Raw high-precision sense trace, same quantized Q/DAC but no ADC quantizer.
    raw_tile = TW1APhysicalTile(manifest, cfg(seed, None))
    raw_interp = MicrocodeInterpreter(raw_tile)
    raw_interp.tile.reset_state()
    raw_interp._run_forward(raw_interp.tile.steps, stochastic=False)
    raw = np.asarray(raw_interp.forward_trace, dtype=float)

    fixed12 = signed_midtread_quantize(raw, 12, 2.0)
    nonzero = int(np.count_nonzero(fixed12))
    unique = int(len(np.unique(fixed12)))
    peak = float(np.max(np.abs(raw)))
    rms = float(np.sqrt(np.mean(raw * raw)))
    gain75 = 1.5 / max(peak, 1e-30)
    gain75 = min(gain75, 1e6)
    ranged = signed_midtread_quantize(gain75 * raw, 12, 2.0) / gain75

    weights = np.asarray(manifest["objective"]["compiled_quadratic_weights"], dtype=float)
    j_raw = float(np.sum(weights * raw * raw))
    j_fixed = float(np.sum(weights * fixed12 * fixed12))
    j_ranged = float(np.sum(weights * ranged * ranged))

    fixed_train = run_closed_loop_training(
        manifest, cfg(seed, 12), iterations=30, step_size=.25,
        normalize_rms=True, include_shuffle=True, shuffle_seed=60_000 + seed,
    )
    ideal_train = run_closed_loop_training(
        manifest, cfg(seed, None), iterations=30, step_size=.25,
        normalize_rms=True, include_shuffle=True, shuffle_seed=60_000 + seed,
    )

    return {
        "seed": seed,
        "raw_peak": peak,
        "raw_rms": rms,
        "fixed12_nonzero_samples": nonzero,
        "fixed12_unique_codes": unique,
        "gain_to_75pct_fs": gain75,
        "objective_raw": j_raw,
        "objective_fixed12": j_fixed,
        "objective_offline_ranged12": j_ranged,
        "fixed12_training_R": fixed_train.exact_reduction,
        "fixed12_shuffle_R": fixed_train.shuffled_reduction,
        "ideal_adc_training_R": ideal_train.exact_reduction,
        "ideal_adc_shuffle_R": ideal_train.shuffled_reduction,
    }


def main(out="runs/sense_range_diagnostic.json"):
    rows=[]
    for seed in SEEDS:
        r=one(seed); rows.append(r)
        print(json.dumps(r, sort_keys=True), flush=True)
    p=Path(out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"experiment":"sense_range_dev","rows":rows}, indent=2))
    print("wrote",p)


if __name__ == "__main__":
    main()
