"""Fixed-theta gradient SNR/bias microscope for partitioned TW-1A v0.9."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

import numpy as np

from v09_fresh_corner import config_for as formal_config
from v09_partitioned_thermal_factorial import make_four
from v09_seed2400_switch_interaction import scale_switch_residuals
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.circuit_emulator_v09_partitioned_rng import PartitionedRNGInterpreter
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import contrast_gradient


TASK_SEED = 2400
FABRICATION_SEED = 2400
DYNAMIC_SEEDS = [8000, 8001, 8002, 8003, 8004]
CHECKPOINTS = [1, 4, 16, 64, 256, 1024]
B = 2e-5


def configure_switches_zero(tile) -> None:
    scale_switch_residuals(tile, 0.0)


def set_clean_dynamic(tile) -> None:
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=0.0,
        self_ktc_base_fraction=0.0,
        drift_ktc_base_fraction=0.0,
        credit_noise_fraction=0.0,
    )


def set_noisy_dynamic(tile, formal_credit_noise: float) -> None:
    tile.config = replace(
        tile.config,
        edge_ktc_base_fraction=B,
        self_ktc_base_fraction=B,
        drift_ktc_base_fraction=B,
        credit_noise_fraction=float(formal_credit_noise),
    )


def acquire_gradient(eti: PartitionedRNGInterpreter, edi: PartitionedRNGInterpreter, *, stochastic: bool) -> np.ndarray:
    rt = eti.execute(stochastic_forward=stochastic)
    rd = edi.execute(stochastic_forward=stochastic)
    return contrast_gradient(
        float(rt["objective"]),
        float(rd["objective"]),
        np.asarray(rt["credits"], dtype=float),
        np.asarray(rd["credits"], dtype=float),
    )


def metrics(mean_g: np.ndarray, g_ref: np.ndarray, sum_sq_norm: float, n: int, mean_single_norm: float) -> dict:
    ref_norm = float(np.linalg.norm(g_ref))
    mean_norm = float(np.linalg.norm(mean_g))
    dot = float(np.dot(mean_g, g_ref))
    cosine = dot / (mean_norm * ref_norm + 1e-300)
    projection = dot / (ref_norm * ref_norm + 1e-300)
    relative_error = float(np.linalg.norm(mean_g - g_ref) / (ref_norm + 1e-300))
    mean_sq_norm = float(sum_sq_norm / float(n))
    trace_var = max(0.0, mean_sq_norm - mean_norm * mean_norm)
    trace_se_rel = math.sqrt(trace_var / float(n)) / (ref_norm + 1e-300)
    return {
        "n": int(n),
        "reference_norm": ref_norm,
        "mean_gradient_norm": mean_norm,
        "mean_single_gradient_norm": float(mean_single_norm),
        "cosine": float(cosine),
        "projection_gain": float(projection),
        "relative_error": relative_error,
        "trace_standard_error_relative": float(trace_se_rel),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dynamic-seed", type=int, choices=DYNAMIC_SEEDS, required=True)
    a = ap.parse_args()

    task = compile_temporal_order_task(TASK_SEED)
    cfg = formal_config(FABRICATION_SEED)
    formal_credit_noise = float(cfg.credit_noise_fraction)
    gain = recommend_sense_gain(task, cfg)
    et, ed, _st, _sd = make_four(task, cfg, gain)
    for tile in (et, ed):
        configure_switches_zero(tile)
        set_clean_dynamic(tile)

    eti = PartitionedRNGInterpreter(et)
    edi = PartitionedRNGInterpreter(ed)
    g_ref = acquire_gradient(eti, edi, stochastic=False)
    ref_norm = float(np.linalg.norm(g_ref))
    print(f"clean reference norm={ref_norm:.9e} PGA={gain:g}", flush=True)

    for tile in (et, ed):
        set_noisy_dynamic(tile, formal_credit_noise)
    et.reseed_dynamic_streams(int(a.dynamic_seed) * 16 + 0)
    ed.reseed_dynamic_streams(int(a.dynamic_seed) * 16 + 1)

    sum_g = np.zeros_like(g_ref)
    sum_sq_norm = 0.0
    sum_norm = 0.0
    rows = []
    check = set(CHECKPOINTS)
    for n in range(1, max(CHECKPOINTS) + 1):
        g = acquire_gradient(eti, edi, stochastic=True)
        sum_g += g
        gn = float(np.linalg.norm(g))
        sum_sq_norm += gn * gn
        sum_norm += gn
        if n in check:
            row = metrics(sum_g / float(n), g_ref, sum_sq_norm, n, sum_norm / float(n))
            rows.append(row)
            print(
                f"N={n:4d} cos={row['cosine']:+.6f} proj={row['projection_gain']:+.6f} "
                f"relerr={row['relative_error']:.6f} se={row['trace_standard_error_relative']:.6f} "
                f"|gbar|={row['mean_gradient_norm']:.6e}",
                flush=True,
            )

    out = {
        "experiment": "v09-fixed-theta-gradient-snr",
        "preregistration": "docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_PREREG.md",
        "status": "spent-body diagnostic",
        "task_seed": TASK_SEED,
        "fabrication_seed": FABRICATION_SEED,
        "dynamic_seed": int(a.dynamic_seed),
        "b": B,
        "sense_gain": float(gain),
        "formal_credit_noise_fraction": formal_credit_noise,
        "reference_norm": ref_norm,
        "checkpoints": rows,
    }
    Path(f"v09-fixed-theta-gradient-snr-{a.dynamic_seed}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
