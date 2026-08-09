"""Diagnostic circuit-native edge thermal-noise sweep on spent C0d bodies."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from circuit_v05_segmented_mismatch_corner import SEEDS, config_for as c0d_config_for
from transientwave.circuit_emulator_v05_edge_thermal import TW1AEdgeThermalConfig
from transientwave.circuit_emulator_v05_edge_thermal_fast import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


VALUES = [0.0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]


def config_for(seed: int, value: float) -> TW1AEdgeThermalConfig:
    kwargs = dict(c0d_config_for(seed).__dict__)
    kwargs.update(
        state_noise_std=0.0,
        edge_ktc_base_fraction=float(value),
    )
    return TW1AEdgeThermalConfig(**kwargs)


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "all_body_clean": n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gaps)),
    }


def main() -> None:
    out = {
        "experiment": "tw1a-c0e-circuit-native-edge-ktc-diagnostic",
        "status": "diagnostic-only-spent-bodies",
        "preregistration": "docs/CIRCUIT_C0E_EDGE_THERMAL_PREREG.md",
        "seeds": SEEDS,
        "execution_note": "selected edge thermal amplitudes cached once per PARAM_HOLD traversal; physics/RNG unchanged",
        "values": [],
    }

    for value in VALUES:
        rows = []
        print(f"edge_ktc_base_fraction={value:g}", flush=True)
        for seed in SEEDS:
            result, gain = run_order_contrast_training(
                compile_temporal_order_task(seed),
                config_for(seed, value),
                iterations=30,
                step_size=0.20,
            )
            rows.append({
                "seed": seed,
                "sense_gain": gain,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            })
        summary = summarize(rows)
        print("  ", summary, flush=True)
        out["values"].append({
            "edge_ktc_base_fraction": value,
            "summary": summary,
            "runs": rows,
        })

    Path("c0e-edge-thermal-sweep.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
