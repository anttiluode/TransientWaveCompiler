"""Frozen diagnosis of the failed TW-1A v0.7 fresh formal corner."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v05_edge_thermal_corner import config_for as c0e_config_for
from transientwave.circuit_emulator_v05_edge_thermal_fast import (
    run_order_contrast_training as run_c0e_training,
)
from transientwave.circuit_emulator_v07_active_summing import (
    TW1AActiveSummingConfig,
    run_order_contrast_training as run_v07_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2000, 2010))
EDGE_FS = 0.255
RATIO = EDGE_FS / 127.0
TAIL = {2006, 2007, 2008}


def formal_config(seed: int) -> TW1AActiveSummingConfig:
    kwargs = dict(c0e_config_for(seed).__dict__)
    kwargs.update(
        state_noise_std=0.0,
        edge_gain_cv=0.0,
        edge_common_settling_loss=0.0,
        prev_ratio_error_std=0.0,
        prev_ratio_calibration=False,
        prev_ratio_calibration_error_std=0.0,
        edge_cunit_over_csum=RATIO,
        edge_ktc_base_fraction=1e-5,
        seed=160_000 + seed,
    )
    return TW1AActiveSummingConfig(**kwargs)


def v07_conditions(seed: int) -> dict[str, TW1AActiveSummingConfig]:
    formal = formal_config(seed)
    no_thermal = replace(formal, edge_ktc_base_fraction=0.0)
    ideal_edge = replace(
        no_thermal,
        edge_unit_cap_sigma=0.0,
        edge_calibration_error_std=0.0,
        edge_lane_match_std=0.0,
    )
    clean_q = replace(
        ideal_edge,
        leakage_rate=0.0,
        leakage_cv=0.0,
        self_gain_cv=0.0,
        self_calibration_error_std=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        terminal_clone_calibration_error_std=0.0,
        edge_charge_raw_common_std=0.0,
        edge_charge_raw_differential_std=0.0,
        edge_charge_cancellation_error_std=0.0,
        edge_charge_residual_common_floor_std=0.0,
        edge_charge_residual_differential_floor_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
    )
    clean_precision = replace(
        clean_q,
        weight_bits=None,
        dac_bits=None,
        adc_bits=None,
        self_bits=None,
        error_dac_bits=None,
    )
    return {
        "formal": formal,
        "no_thermal": no_thermal,
        "ideal_edge_bank": ideal_edge,
        "clean_quantized_v07": clean_q,
        "clean_precision_v07": clean_precision,
    }


def summary(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    return {
        "improve_ge_0p10": sum(x >= 0.10 for x in imp),
        "final_wins": sum(bool(r["final_win"]) for r in rows),
        "median_improvement": float(statistics.median(imp)),
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": float(statistics.median(gaps)),
        "minimum_placement_gap": float(min(gaps)),
        "tail": {
            str(r["seed"]): {
                "improvement": r["improvement"],
                "placement_gap": r["placement_gap"],
                "final_win": r["final_win"],
            }
            for r in rows if r["seed"] in TAIL
        },
    }


def run_condition(name, runner, config_getter):
    print(name, flush=True)
    rows = []
    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        result, gain = runner(
            task,
            config_getter(seed),
            iterations=30,
            step_size=0.20,
        )
        row = {
            "seed": seed,
            "sense_gain": gain,
            "improvement": result.exact_improvement,
            "placement_gap": result.placement_gap,
            "final_exact": result.exact_contrast[-1],
            "final_shuffled": result.shuffled_contrast[-1],
            "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
        }
        rows.append(row)
        print(
            f"  {seed}: PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} win={row['final_win']}",
            flush=True,
        )
    s = summary(rows)
    print("  summary", s, flush=True)
    return {"name": name, "summary": s, "runs": rows}


def main() -> None:
    conditions = []
    for name in (
        "formal",
        "no_thermal",
        "ideal_edge_bank",
        "clean_quantized_v07",
        "clean_precision_v07",
    ):
        conditions.append(
            run_condition(
                name,
                run_v07_training,
                lambda seed, n=name: v07_conditions(seed)[n],
            )
        )

    conditions.append(
        run_condition(
            "old_c0e_formal",
            run_c0e_training,
            lambda seed: replace(c0e_config_for(seed), seed=170_000 + seed),
        )
    )
    conditions.append(
        run_condition(
            "old_c0e_no_thermal",
            run_c0e_training,
            lambda seed: replace(
                c0e_config_for(seed),
                edge_ktc_base_fraction=0.0,
                seed=170_000 + seed,
            ),
        )
    )

    out = {
        "experiment": "tw1a-v07-formal-failure-diagnosis",
        "status": "diagnostic-only-spent-2000-2009",
        "preregistration": "docs/CIRCUIT_V07_FAILURE_DIAG_PREREG.md",
        "seeds": SEEDS,
        "conditions": conditions,
    }
    Path("v07-failure-diagnosis.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
