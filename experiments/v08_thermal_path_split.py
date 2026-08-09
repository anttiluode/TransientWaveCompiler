"""Frozen edge-vs-self thermal path split on spent v0.8 bodies 2300..2309."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

from circuit_v08_self_thermal_corner import config_for as fresh_config
from transientwave.circuit_emulator_v08_self_thermal import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2300, 2310))
CONDITIONS = [
    ("reference", 1e-5, 1e-5),
    ("edge_2e-5_self_1e-5", 2e-5, 1e-5),
    ("edge_3e-5_self_1e-5", 3e-5, 1e-5),
    ("edge_5e-5_self_1e-5", 5e-5, 1e-5),
    ("edge_1e-5_self_2e-5", 1e-5, 2e-5),
    ("edge_1e-5_self_3e-5", 1e-5, 3e-5),
    ("edge_1e-5_self_5e-5", 1e-5, 5e-5),
]


def config_for(seed: int, edge_b: float, self_b: float):
    return replace(
        fresh_config(seed),
        edge_ktc_base_fraction=float(edge_b),
        self_ktc_base_fraction=float(self_b),
    )


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "clean": bool(n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25),
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": med_gap,
        "minimum_placement_gap": float(min(gaps)),
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v08-edge-self-thermal-path-split",
        "status": "diagnostic-only-spent-2300-2309",
        "preregistration": "docs/CIRCUIT_V08_THERMAL_PATH_SPLIT_PREREG.md",
        "seeds": SEEDS,
        "conditions": [],
    }

    for name, edge_b, self_b in CONDITIONS:
        print(f"{name}: edge_b={edge_b:g} self_b={self_b:g}", flush=True)
        rows = []
        for seed in SEEDS:
            task = compile_temporal_order_task(seed)
            result, gain = run_order_contrast_training(
                task,
                config_for(seed, edge_b, self_b),
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
                f"  {seed}: DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} win={row['final_win']}",
                flush=True,
            )
        summary = summarize(rows)
        print("  summary", summary, flush=True)
        out["conditions"].append(
            {
                "name": name,
                "edge_b": edge_b,
                "self_b": self_b,
                "summary": summary,
                "runs": rows,
            }
        )

    lookup = {c["name"]: c["summary"] for c in out["conditions"]}
    edge2 = bool(lookup["edge_2e-5_self_1e-5"]["clean"])
    self2 = bool(lookup["edge_1e-5_self_2e-5"]["clean"])
    if not edge2 and self2:
        diagnosis = "edge_sampling_bottleneck"
    elif edge2 and not self2:
        diagnosis = "self_sampling_bottleneck"
    elif not edge2 and not self2:
        diagnosis = "distributed_thermal_requirement"
    else:
        diagnosis = "combined_source_interaction"
    out["decision"] = {
        "edge_2e-5_clean": edge2,
        "self_2e-5_clean": self2,
        "diagnosis": diagnosis,
        "fresh_seed_authorized": False,
    }
    print("decision", out["decision"], flush=True)

    Path("v08-thermal-path-split.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
