"""TW-1A v0.5 C0d bridge: per-edge segmented capacitor mismatch codebooks.

Each physical reciprocal edge gets its own fabricated 127-unit capacitor bank.
The magnitude selection is the C0d-selected 4-bit binary + 3-bit thermometer
segmentation:

    lower: 1,2,4,8 unit groups
    upper: seven ordered 16-unit thermometer segments

The physical codebook is never sorted or repaired. Foreground calibration may
measure it and choose the nearest physical code, but a non-monotonic fabricated
cell remains a physical yield failure.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .circuit_emulator_v05 import (
    PhaseSymmetricLockstepInterpreter,
    TW1ACircuitTile as _V05Tile,
    TW1ACircuitV05Config,
    copy_circuit_disorder as _copy_v05_disorder,
)
from .emulator import _rms
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray
CODES = np.arange(128, dtype=int)
LOW_BITS = np.asarray(
    [[(code >> k) & 1 for k in range(4)] for code in CODES], dtype=float
)
HIGH_CODE = (CODES >> 4).astype(int)


@dataclass(frozen=True)
class TW1ASegmentedMismatchConfig(TW1ACircuitV05Config):
    """Add per-edge unit-cap mismatch to the qualified v0.5 background."""

    edge_unit_cap_sigma: float = 0.03
    edge_cunit_over_csum: float = 1e-3

    def validate(self) -> None:
        super().validate()
        sigma = float(self.edge_unit_cap_sigma)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise ValueError("edge_unit_cap_sigma must be finite and nonnegative")
        ratio = float(self.edge_cunit_over_csum)
        if not np.isfinite(ratio) or ratio <= 0.0:
            raise ValueError("edge_cunit_over_csum must be finite and positive")


def _group_sums(units: Array, widths: list[int]) -> Array:
    out = []
    start = 0
    for width in widths:
        stop = start + width
        out.append(np.sum(units[:, start:stop], axis=1))
        start = stop
    if start != units.shape[1]:
        raise ValueError("group widths do not consume the supplied units")
    return np.stack(out, axis=1)


def segmented_capacitance_codes(units: Array) -> Array:
    """Return selected capacitance for all 128 codes for every edge row."""
    u = np.asarray(units, dtype=float)
    if u.ndim != 2 or u.shape[1] != 127:
        raise ValueError("units must have shape (edges,127)")
    low = _group_sums(u[:, :15], [1, 2, 4, 8])
    high = _group_sums(u[:, 15:], [16] * 7)
    prefix = np.concatenate(
        [np.zeros((len(u), 1), dtype=float), np.cumsum(high, axis=1)], axis=1
    )
    return low @ LOW_BITS.T + prefix[:, HIGH_CODE]


def _transfer(c: Array, ratio: float) -> Array:
    return (c * ratio) / (1.0 + 2.0 * c * ratio)


class TW1ASegmentedMismatchTile(_V05Tile):
    """Phase-symmetric tile with a distinct measured C0d codebook per edge."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ASegmentedMismatchConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ASegmentedMismatchConfig() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ASegmentedMismatchConfig

        e = len(self.backend.physical_edges())
        sigma = float(self.config.edge_unit_cap_sigma)
        self.edge_cap_units = 1.0 + self.rng.normal(0.0, sigma, size=(e, 127))
        if np.any(self.edge_cap_units <= 0.0):
            raise ValueError("fabricated edge bank contains a nonpositive unit capacitor")

        caps = segmented_capacitance_codes(self.edge_cap_units)
        ratio = float(self.config.edge_cunit_over_csum)
        raw = _transfer(caps, ratio)
        nominal_full = float(_transfer(np.asarray(127.0), ratio))
        fs = max(abs(self.backend.q_edge_min), abs(self.backend.q_edge_max))
        self.edge_cap_levels = float(fs) * raw / nominal_full
        self.edge_codebook_steps = np.diff(self.edge_cap_levels, axis=1)
        self.edge_codebook_monotonic = np.all(self.edge_codebook_steps > 0.0, axis=1)

        # Parent initialization may have constructed cached programmed state
        # before this subclass-specific codebook existed. Refresh it now.
        self._rebuild_programmed_Q()

    @property
    def all_edge_codebooks_monotonic(self) -> bool:
        return bool(np.all(self.edge_codebook_monotonic))

    @property
    def minimum_codebook_step(self) -> float:
        return float(np.min(self.edge_codebook_steps))

    def _quantize_edge_values(self, x: Array) -> Array:
        a = np.asarray(x, dtype=float)
        if self.config.weight_bits is None:
            return a.copy()
        if int(self.config.weight_bits) != 8:
            raise ValueError("C0d bridge currently models the signed 8-bit edge path")

        # During base-class construction the per-edge fabricated codebook has
        # not yet been drawn. Use the parent quantizer only for that transient
        # initialization stage; the programmed state is rebuilt after draw.
        if not hasattr(self, "edge_cap_levels"):
            return super()._quantize_edge_values(a)

        e = len(self.backend.physical_edges())
        if a.shape != (e,):
            raise ValueError(
                f"C0d edge quantizer expects one coefficient for each of {e} physical edges"
            )

        out = np.zeros_like(a)
        for k in range(e):
            levels = self.edge_cap_levels[k]
            mag = min(abs(float(a[k])), float(np.max(levels)))
            # Brute-force nearest measured physical code. This remains valid
            # even for a rare non-monotonic fabricated cell; the yield flag is
            # reported separately and no level ordering is repaired.
            idx = int(np.argmin(np.abs(levels - mag)))
            out[k] = np.sign(a[k]) * float(levels[idx])
        return out

    def clone(self, *, seed: int | None = None) -> "TW1ASegmentedMismatchTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ASegmentedMismatchTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(
    src: TW1ASegmentedMismatchTile, dst: TW1ASegmentedMismatchTile
) -> None:
    """Make two manifests observe one calibrated fabricated C0d tile."""
    _copy_v05_disorder(src, dst)
    dst.edge_cap_units = src.edge_cap_units.copy()
    dst.edge_cap_levels = src.edge_cap_levels.copy()
    dst.edge_codebook_steps = src.edge_codebook_steps.copy()
    dst.edge_codebook_monotonic = src.edge_codebook_monotonic.copy()
    dst._rebuild_programmed_Q()


def _nominal_gain_config(config: TW1ASegmentedMismatchConfig) -> TW1ASegmentedMismatchConfig:
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
        edge_unit_cap_sigma=0.0,
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


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ASegmentedMismatchConfig) -> float:
    tile = TW1ASegmentedMismatchTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = PhaseSymmetricLockstepInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ASegmentedMismatchConfig,
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
    config: TW1ASegmentedMismatchConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ASegmentedMismatchTile, TW1ASegmentedMismatchTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ASegmentedMismatchTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ASegmentedMismatchTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def audit_fabricated_tile(
    manifest: dict[str, Any], config: TW1ASegmentedMismatchConfig
) -> dict[str, Any]:
    """Deterministically inspect the exact target-tile fabrication draw."""
    tile = TW1ASegmentedMismatchTile(manifest, config, sense_gain=1.0)
    failing = np.flatnonzero(~tile.edge_codebook_monotonic)
    return {
        "all_monotonic": tile.all_edge_codebooks_monotonic,
        "failing_edge_count": int(len(failing)),
        "failing_edge_indices": [int(x) for x in failing],
        "minimum_normalized_code_step": tile.minimum_codebook_step,
    }


def _eval_pair(
    ti: PhaseSymmetricLockstepInterpreter,
    di: PhaseSymmetricLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ASegmentedMismatchConfig,
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
