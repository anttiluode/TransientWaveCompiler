"""Execute the preregistered exact-design TW-1A v0.4 hardware envelope."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any

from .hardware_envelope_order_v03 import (
    DAMAGE_GRIDS,
    LEAKAGE_CV_GRID,
    base_config,
    damage_boundary,
    run_point,
)


PRIMARY_SEEDS = tuple(range(880, 886))
TOLERANCE_SEEDS = tuple(range(890, 896))
CONFIRM_SEEDS = tuple(range(900, 910))
PRIMARY_BITS = {"weight_bits": 9, "dac_bits": 5, "adc_bits": 7}


def primary_config():
    return replace(base_config(), **PRIMARY_BITS)


def nominal_config():
    return replace(
        base_config(),
        weight_bits=8,
        dac_bits=8,
        adc_bits=8,
        mirror_error=0.05,
        differential_pass_drift=0.002,
        credit_noise_fraction=0.05,
    )


def main() -> None:
    out: dict[str, Any] = {
        "experiment": "tw1a_hardware_envelope_order_v04",
        "prereg": "docs/HARDWARE_ENVELOPE_ORDER_PREREG_V04.md",
        "primary_bits": dict(PRIMARY_BITS),
        "stage_a": {},
        "stage_b": {},
        "stage_c": None,
    }

    primary = run_point(PRIMARY_SEEDS, primary_config(), label="A primary Q9/DAC5/ADC7")
    nominal = run_point(PRIMARY_SEEDS, nominal_config(), label="A nominal 8/8/8 + errors")
    out["stage_a"]["primary"] = primary
    out["stage_a"]["nominal_baseline"] = nominal

    if not primary["summary"]["qualified"]:
        out["stop_reason"] = "PRIMARY_EXACT_PRECISION_POINT_FAILED"
        out["final_envelope_earned"] = False
        _write(out)
        return

    design_cfg = primary_config()
    boundaries: dict[str, Any] = {}

    for axis, values in DAMAGE_GRIDS.items():
        points = []
        for value in values:
            cfg = replace(design_cfg, **{axis: float(value)})
            points.append(run_point(TOLERANCE_SEEDS, cfg, label=f"B {axis}={value}"))
        b = damage_boundary(values, points)
        boundaries[axis] = b
        out["stage_b"][axis] = {"points": points, "boundary": b}
        print(f"B {axis}: {json.dumps(b, sort_keys=True)}", flush=True)

    rec_leak = boundaries["leakage_rate"]["recommended"]
    if rec_leak is None or float(rec_leak) == 0.0:
        boundaries["leakage_cv"] = {
            "boundary": None,
            "recommended": None,
            "first_failing": None,
            "pass_prefix": [],
        }
        out["stage_b"]["leakage_cv"] = {
            "resolved": False,
            "reason": "recommended leakage rate is zero",
        }
    else:
        points = []
        for value in LEAKAGE_CV_GRID:
            cfg = replace(
                design_cfg,
                leakage_rate=float(rec_leak),
                leakage_cv=float(value),
            )
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

    rec = {k: v.get("recommended") for k, v in boundaries.items()}
    combined_cfg = replace(
        design_cfg,
        leakage_rate=float(rec["leakage_rate"] or 0.0),
        leakage_cv=float(rec["leakage_cv"] or 0.0),
        mirror_error=float(rec["mirror_error"] or 0.0),
        differential_pass_drift=float(rec["differential_pass_drift"] or 0.0),
        state_noise_std=float(rec["state_noise_std"] or 0.0),
        credit_noise_fraction=float(rec["credit_noise_fraction"] or 0.0),
        credit_offset_fraction=float(rec["credit_offset_fraction"] or 0.0),
    )
    combined = run_point(
        CONFIRM_SEEDS,
        combined_cfg,
        label="C combined conservative Q9/DAC5/ADC7",
        final=True,
    )
    out["stage_c"] = {
        "recommended_damage": rec,
        "config": combined_cfg.__dict__,
        "result": combined,
    }
    out["final_envelope_earned"] = bool(combined["summary"]["qualified"])
    _write(out)


def _write(out: dict[str, Any]) -> None:
    path = Path("runs/hardware_envelope_order_v04.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "\nFINAL",
        json.dumps(
            {
                "stop_reason": out.get("stop_reason"),
                "primary_qualified": out.get("stage_a", {}).get("primary", {}).get("summary", {}).get("qualified"),
                "nominal_qualified": out.get("stage_a", {}).get("nominal_baseline", {}).get("summary", {}).get("qualified"),
                "final_envelope_earned": out.get("final_envelope_earned", False),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
