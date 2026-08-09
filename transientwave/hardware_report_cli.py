"""Human-readable TW-1A hardware-requirements report command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .compiler import CompileError
from .ir import program_from_dict
from .physical import compile_tw1a


def format_hardware_report(manifest: dict[str, Any]) -> str:
    h = manifest["hardware_contract"]
    d = h["dynamic_range"]
    prog = d["program"]
    worst = d["architecture_worst_case"]
    profile = h["reference_profile"]
    checks = h["profile_checks"]
    evidence = h["empirical_evidence"]
    corner = evidence["demonstrated_simultaneous_8bit_corner"]

    lines = [
        f"TW-1A hardware report: {manifest['program']}",
        "",
        "Physical programming model",
        "  edge cell       : one reciprocal rank-one coefficient per physical bond",
        "  edge stamp      : a_e * (e_i-e_j)(e_i-e_j)^T",
        "  zero/off        : exact zero-preserving code",
        "  sense range     : compiler-predicted static PGA",
        "  gradient scope  : keep one reciprocal operator realization coherent over the complete physical gradient evaluation",
        "",
        "Program-specific converter spans",
    ]

    if prog["drive_ports"]:
        for p in prog["drive_ports"]:
            lines.append(
                "  drive {port:<12} {kind:<9} span={span:.6g}x -> >= {bits} signed bits @ {margin}-code margin".format(
                    port=p["port"],
                    kind=p["source_schedule_kind"],
                    span=p["compiled_amplitude_span"],
                    bits=p["required_signed_bits_at_margin"],
                    margin=d["minimum_weakest_signal_codes"],
                )
            )
    else:
        lines.append("  drive            : no drive ports")

    lines += [
        "  objective/error : multiplier span={:.6g}x -> >= {} signed bits @ {}-code margin".format(
            prog["compiled_objective_error_multiplier_span"],
            prog["objective_error_bits_at_margin"],
            d["minimum_weakest_signal_codes"],
        ),
        "                    (measured output amplitude variation may add task-dependent range)",
        "",
        "Architecture-wide damping-gauge promise",
        f"  max boundary gain: {worst['max_boundary_gain']:.6g}x",
        f"  broadband drive : {worst['broadband_drive_envelope_span']:.6g}x -> >= {worst['broadband_drive_bits']} signed bits",
        f"  impulse drive   : {worst['impulse_drive_envelope_span']:.6g}x -> >= {worst['impulse_drive_bits']} signed bits",
        f"  quadratic error : {worst['quadratic_error_envelope_span']:.6g}x -> >= {worst['quadratic_error_bits']} signed bits",
        "",
        "Reference profile",
        f"  edge / drive DAC / error DAC / sense ADC : {profile['edge_bits']} / {profile['drive_dac_bits']} / {profile['error_dac_bits']} / {profile['sense_adc_bits']} bits",
        f"  static PGA       : {profile['static_sense_pga']}",
        f"  full-gradient coherence : {profile['coherent_complete_gradient_evaluation']}",
        "",
        "Profile checks",
    ]
    for name, ok in checks.items():
        lines.append(f"  {'PASS' if ok else 'WARN':4} {name}")

    lines += [
        "",
        "Empirical evidence (temporal-order benchmark; not a universal sufficiency theorem)",
        "  task-specific stable floors : edge >= {} bits, DAC >= {} tested bits, ADC+PGA >= {} bits".format(
            evidence["task_specific_precision_floor"]["edge_bits"],
            evidence["task_specific_precision_floor"]["drive_error_dac_bits_lowest_tested_pass"],
            evidence["task_specific_precision_floor"]["sense_adc_bits_with_static_pga"],
        ),
        "  demonstrated simultaneous 8-bit corner:",
        "    leakage/tick={:.6g}, CV={:.6g}, mirror={:.3g}, differential drift={:.6g}, credit noise={:.3g}, offset={:.6g}, state noise={:.6g} FS".format(
            corner["leakage_rate_per_tick"],
            corner["leakage_cv"],
            corner["mirror_error"],
            corner["within_gradient_independent_phase_drift_rms"],
            corner["credit_noise_fraction"],
            corner["credit_offset_fraction"],
            corner["state_noise_fraction_of_full_scale"],
        ),
        "  absolute coherent-Q drift tolerance : unresolved",
        "",
        "Policy",
        "  mixed-signal evidence is reported, not used as a universal hard compile rejection.",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="twc-hw",
        description="Compile a WaveProgram through TW-1A and print its hardware requirements",
    )
    ap.add_argument("input", help="WaveProgram JSON")
    ap.add_argument(
        "--json",
        action="store_true",
        help="print only the machine-readable hardware_contract block",
    )
    args = ap.parse_args()

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        manifest = compile_tw1a(program_from_dict(data))
    except (CompileError, ValueError, KeyError, json.JSONDecodeError) as exc:
        ap.error(str(exc))
        return

    if args.json:
        print(json.dumps(manifest["hardware_contract"], indent=2, allow_nan=False))
    else:
        print(format_hardware_report(manifest))


if __name__ == "__main__":
    main()
