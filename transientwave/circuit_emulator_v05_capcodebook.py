"""Bridge the C0c capacitor-array transfer codebook into TW-1A v0.5.

C0c establishes an explicit 7-bit magnitude capacitor array whose charge-sharing
transfer is monotonic but not uniformly spaced in digital code.  The circuit
emulator historically used an ideal signed uniform 8-bit edge quantizer.  This
module replaces only that edge quantizer with the C0c static codebook while
retaining the already-qualified v0.5 phase-symmetric/background error model.

For an equivalent selected capacitance ``C = m*Cunit`` feeding two endpoint sum
capacitors, the signed differential packet magnitude is proportional to

    f(m) = m*r / (1 + 2*m*r),     r = Cunit/Csum.

The codebook is normalized so magnitude 127 still maps to the backend physical
edge full scale.  Foreground edge calibration then chooses the nearest physical
codebook level instead of assuming an equally spaced ladder.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .circuit_emulator_v05 import (
    PhaseSymmetricLockstepInterpreter,
    TW1ACircuitTile as _V05Tile,
    TW1ACircuitV05Config,
    copy_circuit_disorder,
)
from .emulator import _rms
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


def capacitor_magnitude_levels(
    full_scale: float,
    *,
    cunit_over_csum: float = 1e-3,
) -> Array:
    """Return C0c magnitude levels 0..127 normalized to ``full_scale``."""
    r = float(cunit_over_csum)
    if not np.isfinite(r) or r <= 0.0:
        raise ValueError("cunit_over_csum must be finite and positive")
    m = np.arange(128, dtype=float)
    raw = (m * r) / (1.0 + 2.0 * m * r)
    if raw[-1] <= 0.0:
        raise ValueError("invalid capacitor codebook full scale")
    return float(full_scale) * raw / raw[-1]


def nearest_signed_codebook(x: Array, levels: Array) -> Array:
    """Quantize signed values to nearest exact-zero symmetric codebook level."""
    a = np.asarray(x, dtype=float)
    lev = np.asarray(levels, dtype=float)
    if lev.ndim != 1 or len(lev) != 128 or lev[0] != 0.0:
        raise ValueError("levels must be a 128-entry magnitude codebook starting at zero")
    if np.any(np.diff(lev) <= 0.0):
        raise ValueError("magnitude codebook must be strictly monotonic")

    mag = np.clip(np.abs(a), 0.0, float(lev[-1]))
    # Search insertion point then compare the two neighboring physical levels.
    hi = np.searchsorted(lev, mag, side="left")
    hi = np.clip(hi, 0, len(lev) - 1)
    lo = np.clip(hi - 1, 0, len(lev) - 1)
    choose_hi = np.abs(lev[hi] - mag) < np.abs(mag - lev[lo])
    idx = np.where(choose_hi, hi, lo)
    qmag = lev[idx]
    return np.sign(a) * qmag


class TW1ACapCodebookTile(_V05Tile):
    """v0.5 phase-symmetric tile using the measured C0c edge code spacing."""

    cunit_over_csum: float = 1e-3

    def _quantize_edge_values(self, x: Array) -> Array:
        # Ideal-precision audits remain ideal.
        if self.config.weight_bits is None:
            return np.asarray(x, dtype=float).copy()
        if int(self.config.weight_bits) != 8:
            raise ValueError("C0c codebook bridge currently models the signed 8-bit edge path")
        fs = max(abs(self.backend.q_edge_min), abs(self.backend.q_edge_max))
        levels = capacitor_magnitude_levels(fs, cunit_over_csum=self.cunit_over_csum)
        return nearest_signed_codebook(np.asarray(x, dtype=float), levels)


def _nominal_gain_config(config: TW1ACircuitV05Config) -> TW1ACircuitV05Config:
    """Compiler-model conditions used only to choose the frozen sense PGA."""
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        edge_gain_cv=0.0,
        edge_calibration_error_std=0.0,
        edge_common_settling_loss=0.0,
        edge_lane_match_std=0.0,
        self_gain_cv=0.0,
        self_calibration_error_std=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        terminal_clone_calibration_error_std=0.0,
        edge_settling_error=0.0,
        ab_edge_memory=0.0,
        edge_charge_injection_std=0.0,
        edge_charge_injection_common_std=0.0,
        edge_charge_injection_differential_std=0.0,
        edge_charge_raw_common_std=0.0,
        edge_charge_raw_differential_std=0.0,
        edge_charge_cancellation_error_std=0.0,
        edge_charge_residual_common_floor_std=0.0,
        edge_charge_residual_differential_floor_std=0.0,
        prev_ratio_error_std=0.0,
        prev_ratio_calibration_error_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ACircuitV05Config) -> float:
    tile = TW1ACapCodebookTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = PhaseSymmetricLockstepInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ACircuitV05Config,
    *,
    target_fraction: float = 0.25,
    max_gain: int = 16384,
) -> float:
    peak = max(
        _initial_raw_peak(task["target"], config),
        _initial_raw_peak(task["distractor"], config),
    )
    if peak <= 0.0:
        return float(max_gain)
    target = float(config.adc_full_scale) * float(target_fraction)
    gain = 1
    while gain * 2 <= max_gain and peak * (gain * 2) <= target:
        gain *= 2
    return float(gain)


def _make_pair(
    task: dict[str, Any],
    config: TW1ACircuitV05Config,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACapCodebookTile, TW1ACapCodebookTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ACapCodebookTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ACapCodebookTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def _eval_pair(
    ti: PhaseSymmetricLockstepInterpreter,
    di: PhaseSymmetricLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACircuitV05Config,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, config, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, config, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = PhaseSymmetricLockstepInterpreter(exact_t)
    edi = PhaseSymmetricLockstepInterpreter(exact_d)
    sti = PhaseSymmetricLockstepInterpreter(shuffle_t)
    sdi = PhaseSymmetricLockstepInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    exact_contrast = [c0]
    shuffled_contrast = [sc0]
    exact_target_energy = [et0]
    exact_distractor_energy = [ed0]
    shuffled_target_energy = [st0]
    shuffled_distractor_energy = [sd0]
    measured_t: list[float] = []
    measured_d: list[float] = []
    credit_rms: list[float] = []

    perm = np.random.default_rng(shuffle_seed).permutation(len(exact_t.theta))
    for _ in range(int(iterations)):
        rt = eti.execute(stochastic_forward=True)
        rd = edi.execute(stochastic_forward=True)
        et = float(rt["objective"])
        ed = float(rd["objective"])
        gc = contrast_gradient(
            et,
            ed,
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
            eps=eps,
        )
        measured_t.append(et)
        measured_d.append(ed)
        credit_rms.append(_rms(gc))

        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(exact_t, exact_d)
        if include_shuffle:
            shuffle_t.apply_credits(
                -gc[perm], step_size=step_size, normalize_rms=normalize_rms
            )
            _sync_theta(shuffle_t, shuffle_d)

        etv, edv, cv = _eval_pair(eti, edi)
        stv, sdv, scv = _eval_pair(sti, sdi)
        exact_target_energy.append(etv)
        exact_distractor_energy.append(edv)
        exact_contrast.append(cv)
        shuffled_target_energy.append(stv)
        shuffled_distractor_energy.append(sdv)
        shuffled_contrast.append(scv)

    return OrderContrastTrainingResult(
        exact_contrast=exact_contrast,
        shuffled_contrast=shuffled_contrast,
        exact_target_energy=exact_target_energy,
        exact_distractor_energy=exact_distractor_energy,
        shuffled_target_energy=shuffled_target_energy,
        shuffled_distractor_energy=shuffled_distractor_energy,
        measured_target_energy=measured_t,
        measured_distractor_energy=measured_d,
        combined_credit_rms=credit_rms,
        final_theta=exact_t.theta.copy(),
        final_theta_shuffled=shuffle_t.theta.copy(),
    ), gain
