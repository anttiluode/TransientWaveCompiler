"""Run the preregistered C0c capacitor-codebook v0.5 learning gate."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v05_corner import config_for as v05_config_for
from transientwave.circuit_emulator_v05_capcodebook import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1600, 1610))


def config_for(seed: int):
    # Preserve every physical parameter from the qualified v0.5 gate; only use
    # a fresh deterministic disorder seed for these untouched bodies.
    return replace(v05_config_for(seed), seed=120_000 + seed)


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
    n10 = sum(v >= 0.10 for v in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    qualified = n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25
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
    Path("circuit-v05-capcodebook-corner.json").write_text(
        json.dumps(
            {
                "experiment": "tw1a-v05-c0c-capacitor-codebook-learning-gate",
                "preregistration": "docs/CIRCUIT_V05_CAPCODEBOOK_PREREG.md",
                "seeds": SEEDS,
                "cunit_over_csum": 1e-3,
                "iterations": 30,
                "step_size": 0.20,
                "config": config_for(SEEDS[0]).__dict__,
                "summary": summary,
                "runs": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
