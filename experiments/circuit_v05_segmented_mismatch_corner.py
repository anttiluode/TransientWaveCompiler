"""Run the preregistered v0.5 C0d per-edge segmented-mismatch gate."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from circuit_v05_corner import config_for as v05_config_for
from transientwave.circuit_emulator_v05_segmented_mismatch import (
    TW1ASegmentedMismatchConfig,
    audit_fabricated_tile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(1700, 1710))


def config_for(seed: int) -> TW1ASegmentedMismatchConfig:
    base = v05_config_for(seed)
    return TW1ASegmentedMismatchConfig(
        **base.__dict__,
        edge_unit_cap_sigma=0.03,
        edge_cunit_over_csum=1e-3,
        seed=130_000 + seed,
    )


def main() -> None:
    rows = []
    fabrication_pass = True

    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        cfg = config_for(seed)
        fab = audit_fabricated_tile(task["target"], cfg)
        fabrication_pass = fabrication_pass and bool(fab["all_monotonic"])
        print(
            f"seed={seed} fabrication monotonic={fab['all_monotonic']} "
            f"failed_edges={fab['failing_edge_count']} "
            f"min_step={fab['minimum_normalized_code_step']:+.6e}",
            flush=True,
        )

        if not fab["all_monotonic"]:
            rows.append({
                "seed": seed,
                "fabrication": fab,
                "sense_gain": None,
                "improvement": None,
                "placement_gap": None,
                "initial_contrast": None,
                "final_exact": None,
                "final_shuffled": None,
                "final_win": False,
            })
            continue

        result, gain = run_order_contrast_training(
            task,
            cfg,
            iterations=30,
            step_size=0.20,
        )
        row = {
            "seed": seed,
            "fabrication": fab,
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
            f"  PGA={gain:g} DeltaC={row['improvement']:+.6f} "
            f"gap={row['placement_gap']:+.6f} C={row['final_exact']:+.6f} "
            f"Cshuffle={row['final_shuffled']:+.6f}",
            flush=True,
        )

    learned = [r for r in rows if r["improvement"] is not None]
    if len(learned) == len(SEEDS):
        imp = [float(r["improvement"]) for r in learned]
        gaps = [float(r["placement_gap"]) for r in learned]
        n10 = sum(v >= 0.10 for v in imp)
        wins = sum(bool(r["final_win"]) for r in learned)
        med_imp = float(statistics.median(imp))
        med_gap = float(statistics.median(gaps))
        min_imp = float(min(imp))
        min_gap = float(min(gaps))
    else:
        n10 = 0
        wins = 0
        med_imp = None
        med_gap = None
        min_imp = None
        min_gap = None

    qualified = bool(
        fabrication_pass
        and len(learned) == 10
        and n10 == 10
        and wins == 10
        and med_imp is not None
        and med_imp >= 0.30
        and med_gap is not None
        and med_gap >= 0.25
    )
    summary = {
        "qualified": qualified,
        "fabrication_pass": fabrication_pass,
        "fabricated_tiles_monotonic": sum(
            bool(r["fabrication"]["all_monotonic"]) for r in rows
        ),
        "fabricated_tiles_total": len(rows),
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "median_placement_gap": med_gap,
        "min_improvement": min_imp,
        "min_placement_gap": min_gap,
        "minimum_fabricated_code_step": float(
            min(r["fabrication"]["minimum_normalized_code_step"] for r in rows)
        ),
    }
    print("summary", summary, flush=True)

    Path("circuit-v05-segmented-mismatch-corner.json").write_text(
        json.dumps(
            {
                "experiment": "tw1a-v05-c0d-per-edge-segmented-mismatch-learning-gate",
                "preregistration": "docs/CIRCUIT_V05_SEGMENTED_MISMATCH_PREREG.md",
                "seeds": SEEDS,
                "unit_cap_sigma": 0.03,
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
