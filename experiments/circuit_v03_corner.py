"""Run the preregistered TW-1A v0.3 simultaneous circuit corner."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator_v03 import (
    TW1ACircuitV03Config,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1300, 1310))


def config_for(seed: int) -> TW1ACircuitV03Config:
    return TW1ACircuitV03Config(
        weight_bits=8,
        self_bits=12,
        dac_bits=8,
        error_dac_bits=10,
        adc_bits=8,
        state_full_scale=20.0,
        clip_state=True,
        leakage_rate=0.0005,
        leakage_cv=0.50,
        state_noise_std=5e-9,
        credit_noise_fraction=0.25,
        credit_offset_fraction=0.00015,
        adc_full_scale=2.0,
        edge_gain_cv=0.10,
        self_gain_cv=0.10,
        self_calibration=True,
        self_calibration_error_std=0.001,
        terminal_clone_gain_std=0.01,
        terminal_clone_noise_std=0.0,
        edge_settling_error=0.10,
        ab_edge_memory=0.03,
        edge_charge_injection_std=0.0,
        edge_charge_injection_common_std=3e-5,
        edge_charge_injection_differential_std=1e-5,
        prev_ratio_error_std=0.003,
        error_dac_sign_asymmetry=0.10,
        lcc_curvature=1.0,
        credit_accumulator_leakage=0.01,
        seed=90_000 + seed,
    )


def main() -> None:
    rows = []
    for seed in SEEDS:
        result, gain = run_order_contrast_training(
            compile_temporal_order_task(seed),
            config_for(seed),
            iterations=30,
            step_size=0.20,
        )
        row = {
            "seed": seed,
            "sense_gain": gain,
            "improvement": result.exact_improvement,
            "placement_gap": result.placement_gap,
            "initial_contrast": result.exact_contrast[0],
            "final_exact": result.exact_contrast[-1],
            "final_shuffled": result.shuffled_contrast[-1],
            "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
        }
        rows.append(row)
        print(
            f"seed={seed} PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} C={row['final_exact']:+.6f} "
            f"Cshuffle={row['final_shuffled']:+.6f}",
            flush=True,
        )

    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(v >= .10 for v in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    qualified = n10 == 10 and wins == 10 and med_imp >= .30 and med_gap >= .25
    summary = {
        "qualified": qualified,
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": float(min(imp)),
        "min_placement_gap": float(min(gaps)),
    }
    print("summary", summary, flush=True)
    Path("circuit-v03-corner.json").write_text(json.dumps({
        "experiment": "tw1a-v03-simultaneous-corner",
        "preregistration": "docs/CIRCUIT_V03_CORNER_PREREG.md",
        "seeds": SEEDS,
        "iterations": 30,
        "step_size": .20,
        "config": config_for(SEEDS[0]).__dict__,
        "summary": summary,
        "runs": rows,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
