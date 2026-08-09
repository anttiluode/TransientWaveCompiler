"""Preregistered TW-1A v0.1 hardware-envelope sweep runner."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any

import numpy as np

from .benchmarks import compile_irregular_arbor
from .emulator import TW1APhysicalTileConfig, run_closed_loop_training


TASK_SEEDS = (810, 811, 812, 813, 814)

WEIGHT_BITS = (12, 10, 8, 7, 6, 5, 4, 3)
CONVERTER_BITS = (12, 10, 8, 7, 6, 5, 4, 3)
LEAKAGE_RATE = (0.0, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2)
LEAKAGE_CV = (0.0, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0, 1.5)
MIRROR_ERROR = (0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0)
PASS_DRIFT = (0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)
CREDIT_NOISE = (0.0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0)


def baseline_config(seed: int) -> TW1APhysicalTileConfig:
    return TW1APhysicalTileConfig(
        weight_bits=8,
        weight_quantizer="uniform",
        dac_bits=8,
        adc_bits=8,
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
        seed=10_000 + int(seed),
    )


def _run_level(config_fn) -> dict[str, Any]:
    rows = []
    for seed in TASK_SEEDS:
        manifest = compile_irregular_arbor(seed)
        cfg = config_fn(seed)
        result = run_closed_loop_training(
            manifest,
            cfg,
            iterations=30,
            step_size=0.25,
            normalize_rms=True,
            include_shuffle=True,
            shuffle_seed=20_000 + seed,
        )
        rows.append(
            {
                "seed": seed,
                "exact_reduction": result.exact_reduction,
                "shuffle_reduction": result.shuffled_reduction,
                "initial_loss": result.exact_loss[0],
                "final_exact_loss": result.exact_loss[-1],
                "final_shuffle_loss": result.shuffled_loss[-1],
                "exact_better": bool(result.exact_loss[-1] < result.shuffled_loss[-1]),
                "final_credit_rms": result.credit_rms[-1] if result.credit_rms else 0.0,
            }
        )

    exact = np.asarray([r["exact_reduction"] for r in rows], dtype=float)
    shuffled = np.asarray([r["shuffle_reduction"] for r in rows], dtype=float)
    finite = bool(np.all(np.isfinite(exact)) and np.all(np.isfinite(shuffled)))
    n_r10 = int(np.sum(exact >= 0.10))
    exact_better = int(np.sum([r["exact_better"] for r in rows]))
    med = float(np.median(exact))
    med_shuffle = float(np.median(shuffled))
    med_gap = med - med_shuffle

    usable = bool(
        finite
        and n_r10 >= 4
        and med >= 0.15
        and med_gap >= 0.08
        and exact_better >= 4
    )
    return {
        "usable": usable,
        "n_reduction_ge_0p10": n_r10,
        "median_reduction": med,
        "median_shuffle_reduction": med_shuffle,
        "median_reduction_gap": med_gap,
        "exact_better_count": exact_better,
        "rows": rows,
    }


def _axis_levels(name: str):
    if name == "weight_bits":
        return WEIGHT_BITS
    if name == "converter_bits":
        return CONVERTER_BITS
    if name == "leakage_rate":
        return LEAKAGE_RATE
    if name == "leakage_cv":
        return LEAKAGE_CV
    if name == "mirror_error":
        return MIRROR_ERROR
    if name == "pass_drift":
        return PASS_DRIFT
    if name == "credit_noise":
        return CREDIT_NOISE
    raise KeyError(name)


def _config_for(name: str, value: float | int, seed: int) -> TW1APhysicalTileConfig:
    c = baseline_config(seed)
    if name == "weight_bits":
        return replace(c, weight_bits=int(value))
    if name == "converter_bits":
        return replace(c, dac_bits=int(value), adc_bits=int(value))
    if name == "leakage_rate":
        return replace(c, leakage_rate=float(value), leakage_cv=0.0)
    if name == "leakage_cv":
        return replace(c, leakage_rate=0.002, leakage_cv=float(value))
    if name == "mirror_error":
        return replace(c, mirror_error=float(value))
    if name == "pass_drift":
        return replace(c, differential_pass_drift=float(value))
    if name == "credit_noise":
        return replace(c, credit_noise_fraction=float(value))
    raise KeyError(name)


def _summarize_boundary(name: str, levels: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [r["value"] for r in levels if r["usable"]]
    if name in {"weight_bits", "converter_bits"}:
        return {
            "passing_values": passing,
            "minimum_passing": None if not passing else min(passing),
        }

    pattern = [bool(r["usable"]) for r in levels]
    seen_fail = False
    monotone = True
    for p in pattern:
        if not p:
            seen_fail = True
        elif seen_fail:
            monotone = False
    return {
        "passing_values": passing,
        "monotone_pass_then_fail": monotone,
        "maximum_passing": None if not passing else max(passing),
        "first_failing": next((r["value"] for r in levels if not r["usable"]), None),
    }


def run_axis(name: str) -> dict[str, Any]:
    out = []
    for value in _axis_levels(name):
        print(f"\nAXIS {name} value={value}", flush=True)
        result = _run_level(lambda seed, v=value: _config_for(name, v, seed))
        row = {"value": value, **result}
        out.append(row)
        print(
            f"usable={row['usable']} median={row['median_reduction']:+.4f} "
            f"shuffle={row['median_shuffle_reduction']:+.4f} "
            f"gap={row['median_reduction_gap']:+.4f} "
            f"R10={row['n_reduction_ge_0p10']}/5 exact_better={row['exact_better_count']}/5",
            flush=True,
        )
    return {"axis": name, "levels": out, "boundary": _summarize_boundary(name, out)}


def run_all() -> dict[str, Any]:
    axes = {}
    for name in (
        "converter_bits",
        "weight_bits",
        "leakage_rate",
        "leakage_cv",
        "mirror_error",
        "pass_drift",
        "credit_noise",
    ):
        axes[name] = run_axis(name)

    # The preregistered baseline is already a formal failure, but include an
    # independently recomputed summary in the sweep artifact.
    baseline = _run_level(lambda seed: baseline_config(seed))
    return {
        "experiment": "tw1a_hardware_envelope_v01",
        "task_seeds": list(TASK_SEEDS),
        "baseline_config_example": asdict(baseline_config(TASK_SEEDS[0])),
        "baseline": baseline,
        "axes": axes,
    }


def main(out: str | Path = "runs/hardware_envelope_v01.json") -> None:
    result = run_all()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("\nFINAL BOUNDARIES")
    for name, axis in result["axes"].items():
        print(name, json.dumps(axis["boundary"], sort_keys=True))
    print("wrote", path)


if __name__ == "__main__":
    main()
