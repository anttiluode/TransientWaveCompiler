"""Execute the preregistered TW-1A v0.3 hardware requirements envelope."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import numpy as np

from .emulator import TW1APhysicalTileConfig
from .emulator_v03 import run_order_contrast_training
from .order_benchmarks import compile_temporal_order_task


BIT_GRID = [4, 5, 6, 7, 8, 9, 10, 12]
PRECISION_SEEDS = tuple(range(850, 856))
JOINT_SEEDS = tuple(range(856, 862))
TOLERANCE_SEEDS = tuple(range(862, 868))
CONFIRM_SEEDS = tuple(range(870, 880))

DAMAGE_GRIDS: dict[str, list[float]] = {
    "leakage_rate": [0, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05],
    "mirror_error": [0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00],
    "differential_pass_drift": [0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10],
    "state_noise_std": [0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2],
    "credit_noise_fraction": [0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00],
    "credit_offset_fraction": [0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50],
}
LEAKAGE_CV_GRID = [0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00, 1.50]

_TASK_CACHE: dict[int, dict[str, Any]] = {}


def task(seed: int) -> dict[str, Any]:
    if seed not in _TASK_CACHE:
        _TASK_CACHE[seed] = compile_temporal_order_task(seed)
    return _TASK_CACHE[seed]


def base_config() -> TW1APhysicalTileConfig:
    return TW1APhysicalTileConfig(
        weight_bits=None,
        weight_quantizer="uniform",
        dac_bits=None,
        adc_bits=None,
        state_noise_std=0.0,
        state_full_scale=20.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.0,
        differential_pass_drift=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        adc_full_scale=2.0,
        seed=0,
    )


def qualify(rows: list[dict[str, Any]], *, final: bool = False) -> dict[str, Any]:
    exact = np.asarray([r["exact_improvement"] for r in rows], dtype=float)
    shuffled = np.asarray([r["shuffled_improvement"] for r in rows], dtype=float)
    ef = np.asarray([r["final_exact_contrast"] for r in rows], dtype=float)
    sf = np.asarray([r["final_shuffled_contrast"] for r in rows], dtype=float)
    needed = 8 if final else 5
    summary = {
        "all_positive": bool(np.all(exact > 0.0)),
        "count_exact_ge_0p10": int(np.sum(exact >= 0.10)),
        "median_exact_improvement": float(np.median(exact)),
        "exact_final_beats_shuffle_count": int(np.sum(ef > sf)),
        "median_placement_gap": float(np.median(exact - shuffled)),
        "all_finite": bool(all(bool(r["finite"]) for r in rows)),
    }
    summary["qualified"] = bool(
        summary["all_positive"]
        and summary["count_exact_ge_0p10"] >= needed
        and summary["median_exact_improvement"] >= 0.15
        and summary["exact_final_beats_shuffle_count"] >= needed
        and summary["median_placement_gap"] >= 0.10
        and summary["all_finite"]
    )
    return summary


def run_point(
    seeds: tuple[int, ...],
    config: TW1APhysicalTileConfig,
    *,
    label: str,
    final: bool = False,
) -> dict[str, Any]:
    rows = []
    for seed in seeds:
        cfg = replace(config, seed=300_000 + seed)
        result, gain = run_order_contrast_training(
            task(seed),
            cfg,
            iterations=40,
            step_size=0.20,
            normalize_rms=True,
            include_shuffle=True,
            shuffle_seed=400_000 + seed,
        )
        row = {
            "seed": seed,
            "sense_gain": gain,
            "initial_contrast": result.exact_contrast[0],
            "final_exact_contrast": result.exact_contrast[-1],
            "final_shuffled_contrast": result.shuffled_contrast[-1],
            "exact_improvement": result.exact_improvement,
            "shuffled_improvement": result.shuffled_improvement,
            "placement_gap": result.placement_gap,
            "finite": bool(
                np.all(np.isfinite(result.exact_contrast))
                and np.all(np.isfinite(result.shuffled_contrast))
                and np.all(np.isfinite(result.final_theta))
                and np.all(np.isfinite(result.final_theta_shuffled))
                and np.all(np.isfinite(result.combined_credit_rms))
            ),
        }
        rows.append(row)
    q = qualify(rows, final=final)
    print(
        f"{label}: qualified={q['qualified']} median={q['median_exact_improvement']:+.4f} "
        f"gap={q['median_placement_gap']:+.4f} R10={q['count_exact_ge_0p10']}/{len(seeds)} "
        f"better={q['exact_final_beats_shuffle_count']}/{len(seeds)}",
        flush=True,
    )
    return {"label": label, "config": config.__dict__, "rows": rows, "summary": q}


def stable_minimum(points: list[dict[str, Any]]) -> int | None:
    passed = [bool(p["summary"]["qualified"]) for p in points]
    for i, bit in enumerate(BIT_GRID):
        if all(passed[i:]):
            return int(bit)
    return None


def next_bit(bit: int) -> int:
    i = BIT_GRID.index(bit)
    return int(BIT_GRID[min(i + 1, len(BIT_GRID) - 1)])


def damage_boundary(values: list[float], points: list[dict[str, Any]]) -> dict[str, Any]:
    flags = [bool(p["summary"]["qualified"]) for p in points]
    prefix = []
    for v, ok in zip(values, flags):
        if not ok:
            break
        prefix.append(float(v))
    if not prefix:
        return {
            "pass_prefix": [],
            "boundary": None,
            "recommended": None,
            "first_failing": float(values[0]),
        }
    boundary = prefix[-1]
    first_fail = None if len(prefix) == len(values) else float(values[len(prefix)])
    if len(prefix) == len(values):
        recommended = float(values[-2]) if len(values) > 1 else float(values[-1])
    elif len(prefix) <= 1:
        recommended = float(prefix[0])
    else:
        recommended = float(prefix[-2])
    return {
        "pass_prefix": prefix,
        "boundary": float(boundary),
        "recommended": recommended,
        "first_failing": first_fail,
    }


def main() -> None:
    out: dict[str, Any] = {
        "experiment": "tw1a_hardware_envelope_order_v03",
        "prereg": "docs/HARDWARE_ENVELOPE_ORDER_PREREG_V03.md",
        "stage_a": {},
        "stage_b": {},
        "stage_c": None,
    }

    # Stage A: isolate each precision path with the other precision paths ideal.
    precision_specs = {
        "weight_bits": ("weight_bits", None, None),
        "dac_bits": (None, "dac_bits", None),
        "adc_bits": (None, None, "adc_bits"),
    }
    minima: dict[str, int | None] = {}
    design: dict[str, int | None] = {}

    for axis, selectors in precision_specs.items():
        points = []
        for bit in BIT_GRID:
            cfg = base_config()
            kwargs = {
                "weight_bits": bit if selectors[0] else None,
                "dac_bits": bit if selectors[1] else None,
                "adc_bits": bit if selectors[2] else None,
            }
            cfg = replace(cfg, **kwargs)
            points.append(run_point(PRECISION_SEEDS, cfg, label=f"A {axis}={bit}"))
        minimum = stable_minimum(points)
        minima[axis] = minimum
        design[axis] = None if minimum is None else next_bit(minimum)
        out["stage_a"][axis] = {
            "points": points,
            "stable_minimum": minimum,
            "design_bits": design[axis],
        }
        print(f"A {axis}: stable_min={minimum} design={design[axis]}", flush=True)

    if any(v is None for v in minima.values()):
        out["stop_reason"] = "NO_STABLE_PRECISION_MINIMUM"
        _write(out)
        return

    joint_cfg = replace(
        base_config(),
        weight_bits=int(design["weight_bits"]),
        dac_bits=int(design["dac_bits"]),
        adc_bits=int(design["adc_bits"]),
    )
    joint = run_point(JOINT_SEEDS, joint_cfg, label="A4 joint precision")
    out["stage_a"]["joint_confirmation"] = joint
    out["stage_a"]["design_precision"] = dict(design)
    if not joint["summary"]["qualified"]:
        out["stop_reason"] = "JOINT_PRECISION_CONFIRMATION_FAILED"
        _write(out)
        return

    # Stage B: independent physical damage sweeps.
    boundaries: dict[str, Any] = {}
    for axis, values in DAMAGE_GRIDS.items():
        points = []
        for value in values:
            cfg = replace(joint_cfg, **{axis: float(value)})
            points.append(run_point(TOLERANCE_SEEDS, cfg, label=f"B {axis}={value}"))
        b = damage_boundary(values, points)
        boundaries[axis] = b
        out["stage_b"][axis] = {"points": points, "boundary": b}
        print(f"B {axis}: {json.dumps(b, sort_keys=True)}", flush=True)

    rec_leak = boundaries["leakage_rate"]["recommended"]
    if rec_leak is None or float(rec_leak) == 0.0:
        out["stage_b"]["leakage_cv"] = {
            "resolved": False,
            "reason": "recommended leakage rate is zero",
        }
        boundaries["leakage_cv"] = {
            "boundary": None,
            "recommended": None,
            "first_failing": None,
            "pass_prefix": [],
        }
    else:
        points = []
        for value in LEAKAGE_CV_GRID:
            cfg = replace(joint_cfg, leakage_rate=float(rec_leak), leakage_cv=float(value))
            points.append(run_point(TOLERANCE_SEEDS, cfg, label=f"B leakage_cv={value}"))
        b = damage_boundary(LEAKAGE_CV_GRID, points)
        boundaries["leakage_cv"] = b
        out["stage_b"]["leakage_cv"] = {
            "resolved": True,
            "fixed_leakage_rate": rec_leak,
            "points": points,
            "boundary": b,
        }
        print(f"B leakage_cv: {json.dumps(b, sort_keys=True)}", flush=True)

    # Stage C: conservative one-step-inside corner.
    rec = {k: v.get("recommended") for k, v in boundaries.items()}
    combined_cfg = replace(
        joint_cfg,
        leakage_rate=float(rec["leakage_rate"] or 0.0),
        leakage_cv=float(rec["leakage_cv"] or 0.0),
        mirror_error=float(rec["mirror_error"] or 0.0),
        differential_pass_drift=float(rec["differential_pass_drift"] or 0.0),
        state_noise_std=float(rec["state_noise_std"] or 0.0),
        credit_noise_fraction=float(rec["credit_noise_fraction"] or 0.0),
        credit_offset_fraction=float(rec["credit_offset_fraction"] or 0.0),
    )
    combined = run_point(CONFIRM_SEEDS, combined_cfg, label="C combined conservative", final=True)
    out["stage_c"] = {
        "recommended_damage": rec,
        "config": combined_cfg.__dict__,
        "result": combined,
    }

    # Descriptive inside/outside comparison for the originally proposed nominal point.
    nominal = {
        "weight_bits": 8,
        "dac_bits": 8,
        "adc_bits": 8,
        "mirror_error": 0.05,
        "differential_pass_drift": 0.002,
        "credit_noise_fraction": 0.05,
    }
    precision_inside = all(
        nominal[k] >= int(minima[k]) for k in ("weight_bits", "dac_bits", "adc_bits")
    )
    damage_inside = (
        boundaries["mirror_error"]["boundary"] is not None
        and nominal["mirror_error"] <= boundaries["mirror_error"]["boundary"]
        and boundaries["differential_pass_drift"]["boundary"] is not None
        and nominal["differential_pass_drift"] <= boundaries["differential_pass_drift"]["boundary"]
        and boundaries["credit_noise_fraction"]["boundary"] is not None
        and nominal["credit_noise_fraction"] <= boundaries["credit_noise_fraction"]["boundary"]
    )
    out["nominal_baseline_comparison"] = {
        "nominal": nominal,
        "precision_inside_independent_boundaries": bool(precision_inside),
        "named_damage_inside_independent_boundaries": bool(damage_inside),
        "inside_independent_envelope": bool(precision_inside and damage_inside),
        "note": "descriptive only; combined buildability is determined by Stage C",
    }
    out["final_envelope_earned"] = bool(combined["summary"]["qualified"])
    _write(out)


def _write(out: dict[str, Any]) -> None:
    path = Path("runs/hardware_envelope_order_v03.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\nFINAL", json.dumps({
        "stop_reason": out.get("stop_reason"),
        "final_envelope_earned": out.get("final_envelope_earned", False),
    }, sort_keys=True), flush=True)
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
