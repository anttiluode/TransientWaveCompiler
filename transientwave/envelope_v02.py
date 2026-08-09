"""Corrected preregistered TW-1A v0.2 hardware-envelope experiment."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .benchmarks import compile_irregular_arbor
from .emulator import TW1APhysicalTileConfig
from .emulator_v02 import run_closed_loop_training


STAGE_A_SEEDS = (820, 821, 822, 823, 824)
STAGE_B_SEEDS = (830, 831, 832, 833, 834)
WEIGHT_BITS = (12, 10, 8, 7, 6)
CONVERTER_BITS = (12, 10, 9, 8, 7, 6)

LEAKAGE_RATE = (0.0, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2)
LEAKAGE_CV = (0.0, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0, 1.5)
MIRROR_ERROR = (0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0)
PASS_DRIFT = (0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)
CREDIT_NOISE = (0.0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0)
STATE_NOISE = (0.0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2)


def config_for(seed: int, weight_bits: int, converter_bits: int) -> TW1APhysicalTileConfig:
    return TW1APhysicalTileConfig(
        weight_bits=int(weight_bits),
        weight_quantizer="uniform",
        dac_bits=int(converter_bits),
        adc_bits=int(converter_bits),
        state_noise_std=0.0,
        state_full_scale=2.0,
        clip_state=True,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.05,
        differential_pass_drift=0.002,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.05,
        adc_full_scale=2.0,
        seed=30_000 + int(seed),
    )


def representation_ok(manifest: dict[str, Any], converter_bits: int, margin_codes: int = 4) -> tuple[bool, dict[str, float]]:
    """Task-specific signed error-envelope representation check."""
    G = float(manifest["gauge"]["max_input_gain"])
    k = (1 << (int(converter_bits) - 1)) - 1
    required = float(margin_codes) * G * G
    return bool(k + 1e-12 >= required), {
        "G": G,
        "G2": G * G,
        "signed_positive_codes": float(k),
        "required_codes": required,
        "margin_codes": float(margin_codes),
    }


def run_level(
    seeds: tuple[int, ...],
    config_fn: Callable[[int], TW1APhysicalTileConfig],
    *,
    require_representation: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    representation_rows = []
    for seed in seeds:
        manifest = compile_irregular_arbor(seed)
        cfg = config_fn(seed)
        rep_ok, rep = representation_ok(manifest, int(cfg.dac_bits or 64))
        representation_rows.append({"seed": seed, "ok": rep_ok, **rep})
        if require_representation and not rep_ok:
            rows.append({
                "seed": seed,
                "representation_fail": True,
                "exact_reduction": float("nan"),
                "shuffle_reduction": float("nan"),
                "initial_loss": float("nan"),
                "final_exact_loss": float("nan"),
                "final_shuffle_loss": float("nan"),
                "exact_better": False,
            })
            continue

        result = run_closed_loop_training(
            manifest,
            cfg,
            iterations=30,
            step_size=0.25,
            normalize_rms=True,
            include_shuffle=True,
            shuffle_seed=40_000 + seed,
        )
        rows.append({
            "seed": seed,
            "representation_fail": False,
            "exact_reduction": result.exact_reduction,
            "shuffle_reduction": result.shuffled_reduction,
            "initial_loss": result.exact_loss[0],
            "final_exact_loss": result.exact_loss[-1],
            "final_shuffle_loss": result.shuffled_loss[-1],
            "exact_better": bool(result.exact_loss[-1] < result.shuffled_loss[-1]),
            "final_credit_rms": result.credit_rms[-1] if result.credit_rms else 0.0,
        })

    all_rep = all(x["ok"] for x in representation_rows)
    valid = [r for r in rows if not r["representation_fail"]]
    if len(valid) != len(seeds):
        return {
            "usable": False,
            "representation_ok": False,
            "representation": representation_rows,
            "rows": rows,
            "n_reduction_ge_0p10": 0,
            "median_reduction": float("nan"),
            "median_shuffle_reduction": float("nan"),
            "median_reduction_gap": float("nan"),
            "exact_better_count": 0,
        }

    exact = np.asarray([r["exact_reduction"] for r in valid], dtype=float)
    shuffled = np.asarray([r["shuffle_reduction"] for r in valid], dtype=float)
    finite = bool(np.all(np.isfinite(exact)) and np.all(np.isfinite(shuffled)))
    n_r10 = int(np.sum(exact >= 0.10))
    exact_better = int(np.sum([r["exact_better"] for r in valid]))
    med = float(np.median(exact))
    med_shuffle = float(np.median(shuffled))
    med_gap = med - med_shuffle
    usable = bool(
        all_rep
        and finite
        and n_r10 >= 4
        and med >= 0.15
        and med_gap >= 0.08
        and exact_better >= 4
    )
    return {
        "usable": usable,
        "representation_ok": all_rep,
        "representation": representation_rows,
        "n_reduction_ge_0p10": n_r10,
        "median_reduction": med,
        "median_shuffle_reduction": med_shuffle,
        "median_reduction_gap": med_gap,
        "exact_better_count": exact_better,
        "rows": rows,
    }


def stable_corner(grid: dict[str, dict[str, Any]]) -> dict[str, int] | None:
    candidates: list[tuple[int, int]] = []
    for w in WEIGHT_BITS:
        for c in CONVERTER_BITS:
            key = f"w{w}_c{c}"
            if not grid[key]["usable"]:
                continue
            upper_ok = True
            for w2 in WEIGHT_BITS:
                for c2 in CONVERTER_BITS:
                    if w2 >= w and c2 >= c and not grid[f"w{w2}_c{c2}"]["usable"]:
                        upper_ok = False
                        break
                if not upper_ok:
                    break
            if upper_ok:
                candidates.append((w, c))
    if not candidates:
        return None
    candidates.sort(key=lambda wc: (wc[0] + wc[1], max(wc), wc[1], wc[0]))
    w, c = candidates[0]
    return {"weight_bits": int(w), "converter_bits": int(c)}


def run_stage_a() -> dict[str, Any]:
    grid: dict[str, dict[str, Any]] = {}
    for w in WEIGHT_BITS:
        for c in CONVERTER_BITS:
            print(f"STAGE_A w={w} c={c}", flush=True)
            result = run_level(
                STAGE_A_SEEDS,
                lambda seed, ww=w, cc=c: config_for(seed, ww, cc),
                require_representation=True,
            )
            grid[f"w{w}_c{c}"] = result
            print(
                f"  usable={result['usable']} rep={result['representation_ok']} "
                f"median={result['median_reduction']:+.4f} "
                f"shuffle={result['median_shuffle_reduction']:+.4f} "
                f"gap={result['median_reduction_gap']:+.4f} "
                f"R10={result['n_reduction_ge_0p10']}/5 better={result['exact_better_count']}/5",
                flush=True,
            )
    selected = stable_corner(grid)
    print("STAGE_A_SELECTED", selected, flush=True)
    return {
        "seeds": list(STAGE_A_SEEDS),
        "weight_bits": list(WEIGHT_BITS),
        "converter_bits": list(CONVERTER_BITS),
        "grid": grid,
        "selected": selected,
    }


def _axis_boundary(levels: list[dict[str, Any]]) -> dict[str, Any]:
    pattern = [bool(x["usable"]) for x in levels]
    # Monotone requirement: all values through maximum pass, then all fail.
    seen_fail = False
    monotone = True
    for p in pattern:
        if not p:
            seen_fail = True
        elif seen_fail:
            monotone = False
    passing = [x["value"] for x in levels if x["usable"]]
    return {
        "pass_pattern": pattern,
        "monotone_pass_then_fail": monotone,
        "maximum_passing": max(passing) if passing and monotone else None,
        "first_failing": next((x["value"] for x in levels if not x["usable"]), None),
        "passing_values": passing,
    }


def _sweep_axis(
    name: str,
    values: tuple[float, ...],
    base_cfg: Callable[[int], TW1APhysicalTileConfig],
    change: Callable[[TW1APhysicalTileConfig, float], TW1APhysicalTileConfig],
) -> dict[str, Any]:
    rows = []
    for value in values:
        print(f"STAGE_B {name}={value}", flush=True)
        result = run_level(
            STAGE_B_SEEDS,
            lambda seed, v=value: change(base_cfg(seed), v),
            require_representation=True,
        )
        rows.append({"value": value, **result})
        print(
            f"  usable={result['usable']} median={result['median_reduction']:+.4f} "
            f"gap={result['median_reduction_gap']:+.4f} "
            f"R10={result['n_reduction_ge_0p10']}/5 better={result['exact_better_count']}/5",
            flush=True,
        )
    return {"axis": name, "levels": rows, "boundary": _axis_boundary(rows)}


def run_stage_b(selected: dict[str, int]) -> dict[str, Any]:
    w = int(selected["weight_bits"])
    c = int(selected["converter_bits"])
    base = lambda seed: config_for(seed, w, c)

    baseline = run_level(STAGE_B_SEEDS, base, require_representation=True)
    print(
        "STAGE_B_BASELINE",
        f"usable={baseline['usable']} median={baseline['median_reduction']:+.4f} "
        f"gap={baseline['median_reduction_gap']:+.4f}",
        flush=True,
    )
    if not baseline["usable"]:
        return {
            "seeds": list(STAGE_B_SEEDS),
            "selected": selected,
            "baseline": baseline,
            "status": "PRECISION POINT DID NOT TRANSFER",
            "axes": {},
        }

    axes = {
        "leakage_rate": _sweep_axis(
            "leakage_rate", LEAKAGE_RATE, base,
            lambda cfg, v: replace(cfg, leakage_rate=float(v), leakage_cv=0.0),
        ),
        "leakage_cv": _sweep_axis(
            "leakage_cv", LEAKAGE_CV, base,
            lambda cfg, v: replace(cfg, leakage_rate=0.002, leakage_cv=float(v)),
        ),
        "mirror_error": _sweep_axis(
            "mirror_error", MIRROR_ERROR, base,
            lambda cfg, v: replace(cfg, mirror_error=float(v)),
        ),
        "pass_drift": _sweep_axis(
            "pass_drift", PASS_DRIFT, base,
            lambda cfg, v: replace(cfg, differential_pass_drift=float(v)),
        ),
        "credit_noise": _sweep_axis(
            "credit_noise", CREDIT_NOISE, base,
            lambda cfg, v: replace(cfg, credit_noise_fraction=float(v)),
        ),
        "state_noise": _sweep_axis(
            "state_noise", STATE_NOISE, base,
            lambda cfg, v: replace(cfg, state_noise_std=float(v)),
        ),
    }
    return {
        "seeds": list(STAGE_B_SEEDS),
        "selected": selected,
        "baseline": baseline,
        "status": "QUALIFIED",
        "axes": axes,
    }


def run_all() -> dict[str, Any]:
    stage_a = run_stage_a()
    selected = stage_a["selected"]
    if selected is None:
        return {
            "experiment": "tw1a_hardware_envelope_v02",
            "stage_a": stage_a,
            "stage_b": {"status": "NO QUALIFIED PRECISION POINT", "axes": {}},
        }
    stage_b = run_stage_b(selected)
    return {
        "experiment": "tw1a_hardware_envelope_v02",
        "stage_a": stage_a,
        "stage_b": stage_b,
    }


def main(out: str | Path = "runs/hardware_envelope_v02.json") -> None:
    result = run_all()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("\nV02 SUMMARY")
    print("selected", result["stage_a"].get("selected"))
    print("stage_b", result["stage_b"].get("status"))
    for name, axis in result["stage_b"].get("axes", {}).items():
        print(name, json.dumps(axis["boundary"], sort_keys=True))
    print("wrote", path)


if __name__ == "__main__":
    main()
