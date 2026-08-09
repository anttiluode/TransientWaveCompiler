"""Compiler-visible TW-1A mixed-signal hardware contract.

This module deliberately separates two kinds of statement:

1. analytic requirements that can be derived from a compiled manifest, such as
   signed converter code depth needed to represent a known temporal envelope;
2. empirical evidence earned by the noisy rank-one TW-1A emulator on the
   temporal-order benchmark.

The compiler may report both, but must not silently turn benchmark evidence into
an exact sufficiency theorem for arbitrary programs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

import numpy as np


CONTRACT_VERSION = "tw1a-hardware-contract-v0.1"


@dataclass(frozen=True)
class TW1AHardwareProfile:
    """Reference implementation profile for a practical TW-1A v0 tile.

    ``error_dac_bits`` is intentionally larger than the task-specific emulator
    floor.  It protects the architecture-wide damping-gauge promise at
    ``max_boundary_gain=8`` with a four-code weakest-envelope margin.
    """

    edge_bits: int = 8
    drive_dac_bits: int = 8
    error_dac_bits: int = 10
    sense_adc_bits: int = 8
    signed_code_margin: int = 4
    static_sense_pga: bool = True
    zero_preserving_quantizers: bool = True
    rank1_reciprocal_edge_cells: bool = True
    coherent_complete_gradient_evaluation: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def signed_midtread_positive_codes(bits: int) -> int:
    """Positive full-scale code count for the signed zero-preserving quantizer.

    Codes are ``-K..K`` with ``K=2^(B-1)-1``; the extra two's-complement
    endpoint is deliberately unused so zero/off is represented exactly.
    """
    bits = int(bits)
    if bits < 2:
        raise ValueError("signed mid-tread precision must be >=2 bits")
    return (1 << (bits - 1)) - 1


def required_signed_midtread_bits(span: float, *, min_codes: int = 4) -> int:
    """Minimum signed mid-tread bits for a relative amplitude span.

    If the largest magnitude uses full scale and the smallest relevant
    magnitude must occupy at least ``min_codes`` positive code steps, then

        K / span >= min_codes,
        K = 2^(B-1)-1.

    Therefore

        B >= 1 + ceil(log2(min_codes*span + 1)).
    """
    span = float(span)
    min_codes = int(min_codes)
    if not math.isfinite(span) or span < 1.0:
        raise ValueError("span must be finite and >=1")
    if min_codes < 1:
        raise ValueError("min_codes must be >=1")
    return 1 + int(math.ceil(math.log2(min_codes * span + 1.0)))


def magnitude_span(values: Iterable[float], *, zero_tolerance: float = 0.0) -> float:
    """Return max(nonzero |x|) / min(nonzero |x|), or 1 for <=1 nonzero value."""
    a = np.abs(np.asarray(list(values), dtype=float).ravel())
    if a.size == 0:
        return 1.0
    nz = a[a > float(zero_tolerance)]
    if nz.size <= 1:
        return 1.0
    return float(np.max(nz) / np.min(nz))


def schedule_kind(values: Iterable[float], *, zero_tolerance: float = 0.0) -> str:
    """Classify only what the compiler can know: silent, impulse, or broadband."""
    a = np.abs(np.asarray(list(values), dtype=float).ravel())
    count = int(np.sum(a > float(zero_tolerance)))
    if count == 0:
        return "silent"
    if count == 1:
        return "impulse"
    return "broadband"


def architecture_dynamic_range_budget(
    max_boundary_gain: float,
    *,
    min_codes: int = 4,
) -> dict[str, Any]:
    """Closed-form worst-case gauge-envelope converter budget.

    For broadband drive schedules the damping gauge can create an amplitude
    envelope spanning at most ``G``.  The quadratic objective/error multiplier
    carries the square of the state scaling and can therefore span ``G^2``.

    An impulse has only one nonzero time sample, so the temporal envelope itself
    has relative span one even if its absolute amplitude is rescaled.
    """
    g = float(max_boundary_gain)
    if not math.isfinite(g) or g < 1.0:
        raise ValueError("max_boundary_gain must be finite and >=1")
    drive_span = g
    error_span = g * g
    return {
        "max_boundary_gain": g,
        "amplitude_decay_compensation": g,
        "amplitude_dynamic_range_db": 20.0 * math.log10(g),
        "broadband_drive_envelope_span": drive_span,
        "broadband_drive_bits": required_signed_midtread_bits(
            drive_span, min_codes=min_codes
        ),
        "impulse_drive_envelope_span": 1.0,
        "impulse_drive_bits": required_signed_midtread_bits(
            1.0, min_codes=min_codes
        ),
        "quadratic_error_envelope_span": error_span,
        "quadratic_error_dynamic_range_db": 20.0 * math.log10(error_span),
        "quadratic_error_bits": required_signed_midtread_bits(
            error_span, min_codes=min_codes
        ),
        "minimum_weakest_signal_codes": int(min_codes),
        "derivation": "K/span >= margin, K=2^(B-1)-1",
    }


def _drive_requirements(manifest: dict[str, Any], *, min_codes: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in manifest.get("ports", []):
        if p.get("kind") != "drive":
            continue
        source = np.asarray(p.get("source_waveform", []), dtype=float)
        compiled = np.asarray(p.get("compiled_waveform", []), dtype=float)
        source_kind = schedule_kind(source)
        span = magnitude_span(compiled)
        out.append(
            {
                "port": str(p.get("name", "unnamed")),
                "source_schedule_kind": source_kind,
                "source_nonzero_samples": int(np.count_nonzero(source)),
                "compiled_nonzero_samples": int(np.count_nonzero(compiled)),
                "compiled_amplitude_span": span,
                "required_signed_bits_at_margin": required_signed_midtread_bits(
                    span, min_codes=min_codes
                ),
                "note": (
                    "impulse schedules have no across-time envelope-resolution burden"
                    if source_kind == "impulse"
                    else "bit count covers the compiled nonzero temporal amplitude span"
                ),
            }
        )
    return out


def manifest_dynamic_range_requirements(
    manifest: dict[str, Any],
    *,
    max_boundary_gain: float,
    min_codes: int = 4,
) -> dict[str, Any]:
    """Derive schedule-level and architecture-level converter requirements."""
    drives = _drive_requirements(manifest, min_codes=min_codes)
    obj = manifest.get("objective", {})
    error_mult = np.asarray(obj.get("compiled_error_multiplier", []), dtype=float)
    error_span = magnitude_span(error_mult)
    actual_drive_bits = max(
        (int(d["required_signed_bits_at_margin"]) for d in drives),
        default=required_signed_midtread_bits(1.0, min_codes=min_codes),
    )
    return {
        "quantizer_semantics": "signed_midtread_zero_preserving",
        "minimum_weakest_signal_codes": int(min_codes),
        "program": {
            "drive_ports": drives,
            "max_drive_bits_at_margin": actual_drive_bits,
            "compiled_objective_error_multiplier_span": error_span,
            "objective_error_bits_at_margin": required_signed_midtread_bits(
                error_span, min_codes=min_codes
            ),
            "objective_error_note": (
                "covers only the compiled multiplier envelope; measured output "
                "amplitude variation can add further task-dependent range"
            ),
        },
        "architecture_worst_case": architecture_dynamic_range_budget(
            max_boundary_gain, min_codes=min_codes
        ),
    }


def empirical_contract_evidence() -> dict[str, Any]:
    """Machine-readable summary of currently earned emulator evidence.

    These numbers are deliberately tagged as benchmark evidence rather than
    universal compiler proofs.
    """
    return {
        "benchmark": "tw1a_temporal_order_contrast_v01",
        "hardware_semantics": {
            "edge_parameterization": "one reciprocal rank1 edge cell per physical bond",
            "quantization": "one edge coefficient quantized once, then stamped as rank1 Q contribution",
            "zero_is_exact_code": True,
            "static_sense_pga": True,
        },
        "task_specific_precision_floor": {
            "edge_bits": 5,
            "drive_error_dac_bits_lowest_tested_pass": 4,
            "sense_adc_bits_with_static_pga": 5,
            "source": "docs/HARDWARE_ENVELOPE_ORDER_RESULT_V05.md",
        },
        "demonstrated_simultaneous_8bit_corner": {
            "qualified": True,
            "edge_bits": 8,
            "dac_bits": 8,
            "adc_bits": 8,
            "leakage_rate_per_tick": 0.0005,
            "leakage_cv": 0.50,
            "mirror_error": 0.15,
            "within_gradient_independent_phase_drift_rms": 1e-5,
            "credit_noise_fraction": 0.25,
            "credit_offset_fraction": 0.00015,
            "state_noise_fraction_of_full_scale": 5e-9,
            "source": "docs/HARDWARE_ENVELOPE_ORDER_RESULT_V08.md",
        },
        "operator_coherence": {
            "preferred_scope": "complete_physical_gradient_evaluation",
            "reason": (
                "all objective values and physical derivatives combined into one host gradient "
                "must refer to one reciprocal operator realization"
            ),
            "independent_small_n_averaging": "killed for N<=16 at 0.2% drift",
            "full_update_coherent_0p2pct": (
                "nearly qualified on fresh seeds but failed strict all-positive tail; "
                "not a confirmed tolerance"
            ),
            "absolute_coherent_drift_boundary": "unresolved",
            "sources": [
                "docs/DRIFT_AVERAGING_KILL_RESULT_V01.md",
                "docs/FULL_UPDATE_COHERENT_DRIFT_RESULT_V01.md",
                "docs/FULL_UPDATE_COHERENT_BOUNDARY_RESULT_V01.md",
            ],
        },
    }


def hardware_contract_for_manifest(
    manifest: dict[str, Any],
    *,
    max_boundary_gain: float,
    profile: TW1AHardwareProfile | None = None,
) -> dict[str, Any]:
    """Return the JSON-serializable contract block attached to TW-1A output."""
    p = TW1AHardwareProfile() if profile is None else profile
    dynamic = manifest_dynamic_range_requirements(
        manifest,
        max_boundary_gain=max_boundary_gain,
        min_codes=p.signed_code_margin,
    )
    worst = dynamic["architecture_worst_case"]
    program = dynamic["program"]
    checks = {
        "profile_edge_bits_meet_empirical_floor": p.edge_bits >= 5,
        "profile_drive_dac_meets_program_span": p.drive_dac_bits
        >= int(program["max_drive_bits_at_margin"]),
        "profile_error_dac_meets_program_multiplier_span": p.error_dac_bits
        >= int(program["objective_error_bits_at_margin"]),
        "profile_error_dac_meets_full_boundary_gain_promise": p.error_dac_bits
        >= int(worst["quadratic_error_bits"]),
        "profile_sense_adc_meets_empirical_floor_with_pga": (
            p.static_sense_pga and p.sense_adc_bits >= 5
        ),
        "rank1_edge_cell_semantics_required": p.rank1_reciprocal_edge_cells,
        "zero_preserving_codes_required": p.zero_preserving_quantizers,
        "complete_gradient_operator_coherence_recommended": (
            p.coherent_complete_gradient_evaluation
        ),
    }
    return {
        "version": CONTRACT_VERSION,
        "reference_profile": p.to_dict(),
        "dynamic_range": dynamic,
        "profile_checks": checks,
        "empirical_evidence": empirical_contract_evidence(),
        "policy": {
            "compile_action": "report_not_reject",
            "note": (
                "v0.1 reports hardware feasibility metadata without rejecting a mathematically "
                "valid program solely for empirical mixed-signal margins"
            ),
        },
    }
