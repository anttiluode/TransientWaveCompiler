"""Physical-unit interpretation helpers for normalized filter parameters."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def frequency_from_normalized_omega(omega: float, mapping: Mapping[str, Any]) -> float | None:
    """Invert a recorded Touchstone Omega mapping back to physical hertz.

    Returns ``None`` for unknown mapping modes. The supported mappings are the
    same ones emitted by ``touchstone.py``.
    """
    mode = str(mapping.get("mode", ""))
    omega = float(omega)
    if not np.isfinite(omega):
        raise ValueError("omega must be finite")

    if mode == "linear":
        center_hz = float(mapping["center_hz"])
        scale_hz = float(mapping["scale_hz"])
        if not np.isfinite(center_hz) or not np.isfinite(scale_hz) or scale_hz == 0.0:
            raise ValueError("invalid linear Omega mapping")
        return float(center_hz + omega * scale_hz)

    if mode == "bandpass":
        center_hz = float(mapping["center_hz"])
        bandwidth_hz = float(mapping["bandwidth_hz"])
        omega_sign = float(mapping.get("omega_sign", 1.0))
        if not np.isfinite(center_hz) or center_hz <= 0.0:
            raise ValueError("invalid bandpass center_hz")
        if not np.isfinite(bandwidth_hz) or bandwidth_hz <= 0.0:
            raise ValueError("invalid bandpass bandwidth_hz")
        if omega_sign not in {-1.0, 1.0}:
            raise ValueError("invalid bandpass omega_sign")

        # Omega = s*(f0/BW)*(x - 1/x), x=f/f0.
        # Let y=(Omega/s)*(BW/f0). Then x^2-y*x-1=0 and the
        # physically valid positive-frequency root is below.
        y = (omega / omega_sign) * (bandwidth_hz / center_hz)
        x = 0.5 * (y + np.sqrt(y * y + 4.0))
        return float(center_hz * x)

    return None


def resonator_frequency_from_diagonal(diagonal_value: float, mapping: Mapping[str, Any]) -> float | None:
    """Map a diagonal coupling-matrix detuning to its uncoupled resonance Hz.

    In ``A = M + Omega*U - j*q``, an isolated resonator with diagonal ``d``
    resonates when ``Omega + d = 0``. Therefore ``Omega_res = -d``.
    """
    return frequency_from_normalized_omega(-float(diagonal_value), mapping)


def resonator_frequency_diagnosis(
    nominal_diagonal: float,
    fitted_diagonal: float,
    mapping: Mapping[str, Any] | None,
) -> dict[str, float | None]:
    """Return nominal/fitted resonance frequencies and their physical shift."""
    if mapping is None:
        return {
            "nominal_resonance_hz": None,
            "fitted_resonance_hz": None,
            "resonance_deviation_hz": None,
        }
    nominal_hz = resonator_frequency_from_diagonal(float(nominal_diagonal), mapping)
    fitted_hz = resonator_frequency_from_diagonal(float(fitted_diagonal), mapping)
    if nominal_hz is None or fitted_hz is None:
        return {
            "nominal_resonance_hz": None,
            "fitted_resonance_hz": None,
            "resonance_deviation_hz": None,
        }
    return {
        "nominal_resonance_hz": float(nominal_hz),
        "fitted_resonance_hz": float(fitted_hz),
        "resonance_deviation_hz": float(fitted_hz - nominal_hz),
    }
