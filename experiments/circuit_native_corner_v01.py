"""Run the preregistered TW-1A v0.2 simultaneous circuit-native corner."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from transientwave.circuit_emulator import (
    TW1ACircuitEmulatorConfig,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1200, 1210))


def config_for(seed: int) -> TW1ACircuitEmulatorConfig:
    return TW1ACircuitEmulatorConfig(
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
        self_gain_cv=0.003,
        terminal_clone_gain_std=0.01,
        terminal_clone_noise_std=0.0,
        edge_settling_error=0.10,
        ab_edge_memory=0.03,
        edge_charge_injection_std=3e-5,
        prev_ratio_error_std=0.003,
        error_dac_sign_asymmetry=0.10,
        lcc_curvature=1.0,
        credit_accumulator_leakage=0.01,
        seed=70_000 + seed,
    )


def main() -> None:
    runs = []
    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        result, gain = run_order_contrast_training(
            task,
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
        runs.append(row)
        print(
            f"seed={seed} PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} C0={row['initial_contrast']:+.6f} "
            f"C={row['final_exact']:+.6f} Cshuffle={row['final_shuffled']:+.6f}",
            flush=True,
        )

    improvements = [float(r["improvement"]) for r in runs]
    gaps = [float(r["placement_gap"]) for r in runs]
    final_wins = sum(bool(r["final_win"]) for r in runs)
    n10 = sum(v >= 0.10 for v in improvements)
    median_improvement = float(statistics.median(improvements))
    median_gap = float(statistics.median(gaps))
    qualified = (
        n10 == 10
        and final_wins == 10
        and median_improvement >= 0.30
        and median_gap >= 0.25
    )

    summary = {
        "qualified": qualified,
        "improve_ge_0p10": n10,
        "final_wins": final_wins,
        "median_improvement": median_improvement,
        "median_placement_gap": median_gap,
        "min_improvement": float(min(improvements)),
        "min_placement_gap": float(min(gaps)),
    }
    print("summary", summary, flush=True)

    payload = {
        "experiment": "tw1a-circuit-native-corner-v01",
        "preregistration": "docs/CIRCUIT_NATIVE_CORNER_PREREG_V01.md",
        "seeds": SEEDS,
        "iterations": 30,
        "step_size": 0.20,
        "config": config_for(SEEDS[0]).__dict__,
        "summary": summary,
        "runs": runs,
    }
    Path("circuit-native-corner-v01.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
