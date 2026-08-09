"""Frozen combined edge+self thermal sweep on spent fresh-qualified v0.8 bodies."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for as fresh_config
from transientwave.active_summing_budget import state_capacitance_for_ktc
from transientwave.circuit_emulator_v08_self_thermal import run_order_contrast_training
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2300, 2310))
VALUES = [1e-5, 2e-5, 3e-5, 5e-5]
KNOWN_CAP_FACTOR = 256.0 + 112.0 * 0.265 + 64.0 * 1.5
VFS_VALUES = [0.5, 1.0, 2.0]
MIM_DENSITY_FF_PER_UM2 = 1.0  # illustrative only


def config_for(seed: int, b: float):
    return replace(
        fresh_config(seed),
        edge_ktc_base_fraction=float(b),
        self_ktc_base_fraction=float(b),
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


def thermal_cost(b: float):
    rows = []
    for vfs in VFS_VALUES:
        cstate = state_capacitance_for_ktc(b, vfs, temperature_k=300.0)
        total_cap = KNOWN_CAP_FACTOR * cstate
        area_mm2 = (total_cap / 1e-15) / MIM_DENSITY_FF_PER_UM2 / 1e6
        rows.append(
            {
                "effective_vfs_v": vfs,
                "cstate_f": cstate,
                "known_cap_total_f": total_cap,
                "known_cap_area_mm2_at_1ff_per_um2": area_mm2,
            }
        )
    return rows


def main() -> None:
    out = {
        "experiment": "tw1a-v08-combined-edge-self-thermal-budget-sweep",
        "status": "diagnostic-only-spent-2300-2309",
        "preregistration": "docs/CIRCUIT_V08_COMBINED_THERMAL_SWEEP_PREREG.md",
        "seeds": SEEDS,
        "known_cap_factor_times_cstate": KNOWN_CAP_FACTOR,
        "conditions": [],
    }

    for b in VALUES:
        print(f"combined_b={b:g}", flush=True)
        rows = []
        for seed in SEEDS:
            task = compile_temporal_order_task(seed)
            result, gain = run_order_contrast_training(
                task,
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
                f"  {seed}: DeltaC={row['improvement']:+.6f} "
                f"gap={row['placement_gap']:+.6f} win={row['final_win']}",
                flush=True,
            )
        s = summarize(rows)
        print("  summary", s, flush=True)
        costs = thermal_cost(b)
        for c in costs:
            print(
                f"    VFS={c['effective_vfs_v']:g}V Cstate={c['cstate_f']*1e12:.4f}pF "
                f"known-cap-area={c['known_cap_area_mm2_at_1ff_per_um2']:.4f}mm2",
                flush=True,
            )
        out["conditions"].append(
            {
                "b": b,
                "summary": s,
                "thermal_cost": costs,
                "runs": rows,
            }
        )

    clean = {float(c["b"]): bool(c["summary"]["clean"]) for c in out["conditions"]}
    if clean.get(5e-5, False):
        candidate = 3e-5
    elif clean.get(3e-5, False):
        candidate = 2e-5
    elif clean.get(2e-5, False):
        candidate = 1e-5
    else:
        candidate = None
    out["decision"] = {
        "clean_points": [b for b in VALUES if clean.get(b, False)],
        "fresh_candidate_b": candidate,
        "note": (
            "candidate is an already-tested inward point under the preregistered rule; "
            "no fresh seeds are automatically spent by this diagnostic"
        ),
    }
    print("decision", out["decision"], flush=True)

    Path("v08-combined-thermal-sweep.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
