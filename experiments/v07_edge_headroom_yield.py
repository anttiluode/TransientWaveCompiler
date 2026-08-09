"""Frozen fabrication-yield study for v0.7 edge full-scale headroom."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


TILES = 20_000
EDGES = 112
UNITS = 127
UNIT_SIGMA = 0.03
SITE_SIGMAS = [0.0025, 0.005, 0.01, 0.02]
NOMINAL_FS = [0.255, 0.260, 0.265, 0.270]
REQUIRED_FS = 0.250
SEED = 707_2026


def run_point(rng, nominal_fs: float, site_sigma: float) -> dict:
    minima = np.empty(TILES, dtype=float)
    passes = 0
    batch = 1000
    # Sum of 127 independent N(1, unit_sigma) variables is exactly Gaussian.
    unit_sum_sigma = UNIT_SIGMA * np.sqrt(UNITS)
    for start in range(0, TILES, batch):
        n = min(batch, TILES - start)
        unit_sum = UNITS + rng.normal(0.0, unit_sum_sigma, size=(n, EDGES))
        site_scale = 1.0 + rng.normal(0.0, site_sigma, size=(n, EDGES))
        full_scale = nominal_fs * (unit_sum / UNITS) * site_scale
        m = np.min(full_scale, axis=1)
        minima[start : start + n] = m
        passes += int(np.sum(m >= REQUIRED_FS))
    return {
        "nominal_full_scale": nominal_fs,
        "site_ratio_sigma": site_sigma,
        "tile_yield": passes / TILES,
        "minimum_fs_p01": float(np.quantile(minima, 0.01)),
        "minimum_fs_median": float(np.median(minima)),
        "minimum_fs_min": float(np.min(minima)),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    for sigma in SITE_SIGMAS:
        print(f"site_sigma={sigma:.4f}", flush=True)
        for fs in NOMINAL_FS:
            row = run_point(rng, fs, sigma)
            rows.append(row)
            print(
                f"  FS={fs:.3f} yield={row['tile_yield']:.5f} "
                f"p01(minFS)={row['minimum_fs_p01']:.6f} "
                f"median(minFS)={row['minimum_fs_median']:.6f}",
                flush=True,
            )

    out = {
        "experiment": "tw1a-v07-edge-headroom-yield",
        "status": "diagnostic-only-no-learning",
        "preregistration": "docs/CIRCUIT_V07_EDGE_HEADROOM_YIELD_PREREG.md",
        "tiles_per_point": TILES,
        "edges_per_tile": EDGES,
        "units_per_edge": UNITS,
        "unit_cap_sigma": UNIT_SIGMA,
        "required_edge_full_scale": REQUIRED_FS,
        "seed": SEED,
        "results": rows,
    }
    Path("v07-edge-headroom-yield.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
