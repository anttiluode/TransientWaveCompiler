"""Frozen spent-body diagnostic for TW-1A v0.8 common/difference reverse."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v07_active_summing_corner import config_for as v07_formal_config
from transientwave.circuit_emulator_v08_common_diff import (
    TW1ACommonDiffConfig,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2000, 2010))
CONDITIONS = (
    ("common_diff_b0", 0.0),
    ("common_diff_b1e-5", 1e-5),
)
TAIL = {2006, 2007, 2008}


def config_for(seed: int, b: float) -> TW1ACommonDiffConfig:
    base = v07_formal_config(seed)
    kwargs = dict(base.__dict__)
    kwargs["edge_ktc_base_fraction"] = float(b)
    return TW1ACommonDiffConfig(**kwargs)


def summarize(rows):
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


def main() -> None:
    out = {
        "experiment": "tw1a-v08-common-diff-spent-body-diagnostic",
        "status": "diagnostic-only-spent-2000-2009",
        "preregistration": "docs/CIRCUIT_V08_COMMON_DIFF_DIAGNOSTIC_PREREG.md",
        "conditions": [],
    }
    for name, b in CONDITIONS:
        print(name, flush=True)
        rows = []
        for seed in SEEDS:
            result, gain = run_order_contrast_training(
                compile_temporal_order_task(seed),
                config_for(seed, b),
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
        s = summarize(rows)
        print("  summary", s, flush=True)
        out["conditions"].append(
            {"name": name, "edge_ktc_base_fraction": b, "summary": s, "runs": rows}
        )

    Path("v08-common-diff-diagnostic.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
