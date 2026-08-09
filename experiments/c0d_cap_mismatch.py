"""C0d Monte Carlo: capacitor selection architecture under unit mismatch.

Frozen plan: docs/CIRCUIT_C0D_MISMATCH_PREREG.md
This is a physical architecture diagnostic, not a learning qualification.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import numpy as np


SIGMAS = [0.001, 0.003, 0.01, 0.03, 0.05, 0.10]
SAMPLES = 5000
SEED = 20260809
R = 1e-3
CODES = np.arange(128, dtype=int)


def bit_matrix(bits: int) -> np.ndarray:
    return np.asarray(
        [[(code >> k) & 1 for k in range(bits)] for code in CODES],
        dtype=float,
    )


BITS7 = bit_matrix(7)
BITS4 = bit_matrix(4)


def group_sums(units: np.ndarray, widths: list[int]) -> np.ndarray:
    out = []
    start = 0
    for width in widths:
        stop = start + width
        out.append(np.sum(units[:, start:stop], axis=1))
        start = stop
    if start != units.shape[1]:
        raise ValueError("group widths do not consume all unit capacitors")
    return np.stack(out, axis=1)


def effective_caps_binary(units: np.ndarray) -> np.ndarray:
    branches = group_sums(units, [1, 2, 4, 8, 16, 32, 64])
    return branches @ BITS7.T


def effective_caps_segmented(units: np.ndarray) -> np.ndarray:
    # First 15 units form the 1/2/4/8 lower binary branches. The remaining
    # 112 units form seven ordered 16-unit thermometer segments.
    low = group_sums(units[:, :15], [1, 2, 4, 8])
    high_units = units[:, 15:]
    high_segments = group_sums(high_units, [16] * 7)
    high_prefix = np.concatenate(
        [np.zeros((len(units), 1)), np.cumsum(high_segments, axis=1)], axis=1
    )
    high_code = (CODES >> 4).astype(int)
    low_caps = low @ BITS4.T
    high_caps = high_prefix[:, high_code]
    return low_caps + high_caps


def effective_caps_thermometer(units: np.ndarray) -> np.ndarray:
    return np.concatenate(
        [np.zeros((len(units), 1)), np.cumsum(units, axis=1)], axis=1
    )


ARCH = {
    "pure_binary": effective_caps_binary,
    "segmented_4plus3": effective_caps_segmented,
    "full_thermometer": effective_caps_thermometer,
}


def transfer(c: np.ndarray) -> np.ndarray:
    return (c * R) / (1.0 + 2.0 * c * R)


def summarize(caps: np.ndarray) -> dict:
    raw = transfer(caps)
    full = raw[:, -1]
    if np.any(full <= 0.0):
        raise ValueError("nonpositive code-127 transfer")
    levels = raw / full[:, None]
    steps = np.diff(levels, axis=1)

    monotonic = np.all(steps > 0.0, axis=1)
    min_step = np.min(steps, axis=1)
    max_gap = np.max(steps, axis=1)
    half_gap = 0.5 * max_gap
    worst_transition = np.argmin(steps, axis=1) + 1

    failed = np.flatnonzero(~monotonic)
    carry = None
    count = 0
    if len(failed):
        counts = Counter(int(worst_transition[i]) for i in failed)
        code, count = counts.most_common(1)[0]
        carry = f"{code - 1}->{code}"

    return {
        "monotonic_yield": float(np.mean(monotonic)),
        "failed_samples": int(np.sum(~monotonic)),
        "median_minimum_step": float(np.median(min_step)),
        "p01_minimum_step": float(np.percentile(min_step, 1.0)),
        "minimum_observed_step": float(np.min(min_step)),
        "median_calibrated_half_gap": float(np.median(half_gap)),
        "p99_calibrated_half_gap": float(np.percentile(half_gap, 99.0)),
        "maximum_calibrated_half_gap": float(np.max(half_gap)),
        "most_common_failing_carry": carry,
        "most_common_failing_carry_count": int(count),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    output = {
        "experiment": "tw1a-c0d-capacitor-mismatch-architecture-study",
        "preregistration": "docs/CIRCUIT_C0D_MISMATCH_PREREG.md",
        "samples_per_point": SAMPLES,
        "rng_seed": SEED,
        "cunit_over_csum": R,
        "sigmas": SIGMAS,
        "architectures": {name: [] for name in ARCH},
    }

    for sigma in SIGMAS:
        units = 1.0 + rng.normal(0.0, sigma, size=(SAMPLES, 127))
        valid = np.all(units > 0.0, axis=1)
        invalid = int(np.sum(~valid))
        if invalid:
            units = units[valid]
        print(f"sigma={sigma:g} valid={len(units)} invalid={invalid}", flush=True)

        for name, fn in ARCH.items():
            metrics = summarize(fn(units))
            row = {
                "sigma_unit": sigma,
                "valid_samples": int(len(units)),
                "invalid_samples": invalid,
                **metrics,
            }
            output["architectures"][name].append(row)
            print(
                f"  {name:18s} yield={metrics['monotonic_yield']:.6f} "
                f"p01step={metrics['p01_minimum_step']:+.6e} "
                f"p99halfgap={metrics['p99_calibrated_half_gap']:.6e} "
                f"carry={metrics['most_common_failing_carry']}",
                flush=True,
            )

    Path("c0d-cap-mismatch.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
