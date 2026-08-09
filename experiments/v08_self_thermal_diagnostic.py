"""Frozen spent-body diagnostic for local self-sampling kT/C in TW-1A v0.8."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_kick_calibrated_corner import config_for as qualified_config
from transientwave.circuit_emulator_v08_self_thermal import (
    TW1ACommonDiffSelfThermalConfig,
    TW1ACommonDiffSelfThermalTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2200, 2210))
CONDITIONS = (("self_b0", 0.0), ("self_b1e-5", 1e-5))


def config_for(seed: int, self_b: float) -> TW1ACommonDiffSelfThermalConfig:
    base = qualified_config(seed)
    kwargs = dict(base.__dict__)
    kwargs["self_ktc_base_fraction"] = float(self_b)
    return TW1ACommonDiffSelfThermalConfig(**kwargs)


def self_noise_audit(manifest, cfg):
    tile = TW1ACommonDiffSelfThermalTile(manifest, cfg, sense_gain=1.0)
    self_coeff, _, _ = tile.physical_components()
    sigma = tile.self_thermal_sigma_fraction(self_coeff)
    return {
        "max_abs_self_coeff": float(np.max(np.abs(self_coeff))),
        "max_self_thermal_rms_fraction": float(np.max(sigma)),
        "rms_self_thermal_fraction_across_nodes": float(np.sqrt(np.mean(sigma * sigma))),
    }


def summarize(rows):
    imp = [float(r["improvement"]) for r in rows]
    gaps = [float(r["placement_gap"]) for r in rows]
    n10 = sum(x >= 0.10 for x in imp)
    wins = sum(bool(r["final_win"]) for r in rows)
    med_imp = float(statistics.median(imp))
    med_gap = float(statistics.median(gaps))
    return {
        "formal_predicate": bool(n10 == 10 and wins == 10 and med_imp >= 0.30 and med_gap >= 0.25),
        "improve_ge_0p10": n10,
        "final_wins": wins,
        "median_improvement": med_imp,
        "minimum_improvement": float(min(imp)),
        "median_placement_gap": med_gap,
        "minimum_placement_gap": float(min(gaps)),
        "maximum_abs_self_coeff": float(max(r["self_noise"]["max_abs_self_coeff"] for r in rows)),
        "maximum_self_thermal_rms_fraction": float(max(r["self_noise"]["max_self_thermal_rms_fraction"] for r in rows)),
    }


def main() -> None:
    out = {
        "experiment": "tw1a-v08-self-sampling-thermal-diagnostic",
        "status": "diagnostic-only-spent-2200-2209",
        "preregistration": "docs/CIRCUIT_V08_SELF_THERMAL_DIAGNOSTIC_PREREG.md",
        "conditions": [],
    }

    for name, self_b in CONDITIONS:
        print(name, flush=True)
        rows = []
        for seed in SEEDS:
            task = compile_temporal_order_task(seed)
            cfg = config_for(seed, self_b)
            audit = self_noise_audit(task["target"], cfg)
            result, gain = run_order_contrast_training(
                task, cfg, iterations=30, step_size=0.20
            )
            row = {
                "seed": seed,
                "sense_gain": gain,
                "self_noise": audit,
                "improvement": result.exact_improvement,
                "placement_gap": result.placement_gap,
                "final_exact": result.exact_contrast[-1],
                "final_shuffled": result.shuffled_contrast[-1],
                "final_win": result.exact_contrast[-1] > result.shuffled_contrast[-1],
            }
            rows.append(row)
            print(
                f"  {seed}: DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} win={row['final_win']} "
                f"self|max|={audit['max_abs_self_coeff']:.4f} "
                f"self_sigma_max={audit['max_self_thermal_rms_fraction']:.3e}",
                flush=True,
            )
        s = summarize(rows)
        print("  summary", s, flush=True)
        out["conditions"].append(
            {
                "name": name,
                "self_ktc_base_fraction": self_b,
                "summary": s,
                "runs": rows,
            }
        )

    self_on = next(c for c in out["conditions"] if c["name"] == "self_b1e-5")
    out["decision"] = {
        "self_b1e-5_pass": bool(self_on["summary"]["formal_predicate"]),
        "fresh_seed_reservation_if_pass": list(range(2300, 2310)),
    }
    print("decision", out["decision"], flush=True)

    Path("v08-self-thermal-diagnostic.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
