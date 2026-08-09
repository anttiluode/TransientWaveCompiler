"""TW-1A v0.4 circuit emulator: calibration-first physical abstraction.

v0.3 showed that the clean quantized machine learns reliably while a simultaneous
raw-error corner can still fail through interactions.  v0.4 therefore models the
bring-up sequence the circuit actually intends to use:

    raw mismatch -> foreground measurement -> inverse programming / trim
                 -> small residual -> PARAM_HOLD -> physical gradient

Calibratable fixed errors are no longer interpreted as unavoidable gradient
errors.  Edge/self MDAC gain, the -PREV ratio and terminal copy gain each have a
raw mismatch and a post-measurement residual.  Edge switch charge is treated as
a raw packet followed by autozero/cancellation, leaving only the cancellation
residual and a floor.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .circuit_emulator import LockstepCircuitInterpreter
from .circuit_emulator_v03 import TW1ACircuitV03Config, TW1ACircuitTile as _V03Tile
from .emulator import _rms
from .emulator_v02 import signed_midtread_quantize
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


def _positive_measurement(true_gain: Array, sigma: float, rng: np.random.Generator) -> Array:
    true_gain = np.asarray(true_gain, dtype=float)
    if sigma == 0.0:
        return true_gain.copy()
    err = rng.normal(0.0, sigma, size=true_gain.shape)
    return np.maximum(true_gain * (1.0 + err), 1e-9)


def _trim_about_unity(command: Array, bits: int | None, span: float) -> Array:
    """Quantize a multiplicative trim command around exactly one."""
    command = np.asarray(command, dtype=float)
    delta = command - 1.0
    if bits is None:
        return 1.0 + np.clip(delta, -span, span)
    return 1.0 + signed_midtread_quantize(delta, bits, span)


@dataclass(frozen=True)
class TW1ACircuitV04Config(TW1ACircuitV03Config):
    """Calibration-first v0.4 error model.

    The inherited gain-CV fields describe raw fabricated mismatch.  New
    ``*_calibration_error_std`` fields describe fractional measurement error.
    Programmable edge/self paths are inverse-programmed through the measured
    map.  Fixed unity/copy paths use a centered trim element.

    v0.3's charge-injection fields are kept at zero in v0.4.  Raw switching
    packets are instead specified separately and are cancelled once during
    foreground bring-up.  The recurrence sees only the post-cancellation
    packet.
    """

    edge_calibration: bool = True
    edge_calibration_error_std: float = 0.0

    prev_ratio_calibration: bool = True
    prev_ratio_calibration_error_std: float = 0.0
    prev_trim_bits: int | None = 12
    prev_trim_range: float = 0.125

    terminal_clone_calibration: bool = True
    terminal_clone_calibration_error_std: float = 0.0
    terminal_clone_trim_bits: int | None = 12
    terminal_clone_trim_range: float = 0.125

    edge_charge_autozero: bool = True
    edge_charge_raw_common_std: float = 0.0
    edge_charge_raw_differential_std: float = 0.0
    edge_charge_cancellation_error_std: float = 0.0
    edge_charge_residual_common_floor_std: float = 0.0
    edge_charge_residual_differential_floor_std: float = 0.0

    def validate(self) -> None:
        super().validate()
        # Avoid silently mixing v0.2/v0.3 residual packet models with v0.4 raw
        # packet + cancellation semantics.
        if self.edge_charge_injection_std != 0.0:
            raise ValueError("v0.4 requires legacy edge_charge_injection_std=0")
        if self.edge_charge_injection_common_std != 0.0:
            raise ValueError("v0.4 requires v0.3 edge_charge_injection_common_std=0")
        if self.edge_charge_injection_differential_std != 0.0:
            raise ValueError("v0.4 requires v0.3 edge_charge_injection_differential_std=0")

        nonnegative = (
            "edge_calibration_error_std",
            "prev_ratio_calibration_error_std",
            "terminal_clone_calibration_error_std",
            "edge_charge_raw_common_std",
            "edge_charge_raw_differential_std",
            "edge_charge_cancellation_error_std",
            "edge_charge_residual_common_floor_std",
            "edge_charge_residual_differential_floor_std",
        )
        for name in nonnegative:
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")

        for name, bits in (
            ("prev_trim_bits", self.prev_trim_bits),
            ("terminal_clone_trim_bits", self.terminal_clone_trim_bits),
        ):
            if bits is not None and int(bits) < 2:
                raise ValueError(f"{name} must be >=2 or None")
        for name in ("prev_trim_range", "terminal_clone_trim_range"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0 or value >= 1.0:
                raise ValueError(f"{name} must lie in (0,1)")


class TW1ACircuitTile(_V03Tile):
    """v0.4 tile with measured inverse maps, trim and charge autozero."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACircuitV04Config | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ACircuitV04Config() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACircuitV04Config

        e = len(self.backend.physical_edges())
        n = self.nodes

        # Edge MDAC: raw gain is fabricated once; foreground measurement drives
        # inverse digital programming.  Quantization still occurs in the actual
        # edge code after pre-distortion.
        self.edge_gain_measured = _positive_measurement(
            self.edge_gain, self.config.edge_calibration_error_std, self.rng
        )

        # -PREV: preserve the fabricated ratio for audit, then replace the gain
        # seen by the recurrence with the trimmed effective ratio.
        self.prev_ratio_gain_raw = self.prev_ratio_gain.copy()
        self.prev_ratio_gain_measured = _positive_measurement(
            self.prev_ratio_gain_raw,
            self.config.prev_ratio_calibration_error_std,
            self.rng,
        )
        if self.config.prev_ratio_calibration:
            cmd = 1.0 / self.prev_ratio_gain_measured
            trim = _trim_about_unity(
                cmd, self.config.prev_trim_bits, self.config.prev_trim_range
            )
            self.prev_ratio_trim = trim
            self.prev_ratio_gain = self.prev_ratio_gain_raw * trim
        else:
            self.prev_ratio_trim = np.ones(n, dtype=float)
            self.prev_ratio_gain = self.prev_ratio_gain_raw.copy()

        # Terminal clone: current and previous banks have independent raw copy
        # gains and independent measured trim commands.
        self.clone_gain_current_raw = self.clone_gain_current.copy()
        self.clone_gain_previous_raw = self.clone_gain_previous.copy()
        self.clone_gain_current_measured = _positive_measurement(
            self.clone_gain_current_raw,
            self.config.terminal_clone_calibration_error_std,
            self.rng,
        )
        self.clone_gain_previous_measured = _positive_measurement(
            self.clone_gain_previous_raw,
            self.config.terminal_clone_calibration_error_std,
            self.rng,
        )
        if self.config.terminal_clone_calibration:
            self.clone_trim_current = _trim_about_unity(
                1.0 / self.clone_gain_current_measured,
                self.config.terminal_clone_trim_bits,
                self.config.terminal_clone_trim_range,
            )
            self.clone_trim_previous = _trim_about_unity(
                1.0 / self.clone_gain_previous_measured,
                self.config.terminal_clone_trim_bits,
                self.config.terminal_clone_trim_range,
            )
            self.clone_gain_current = self.clone_gain_current_raw * self.clone_trim_current
            self.clone_gain_previous = self.clone_gain_previous_raw * self.clone_trim_previous
        else:
            self.clone_trim_current = np.ones(n, dtype=float)
            self.clone_trim_previous = np.ones(n, dtype=float)
            self.clone_gain_current = self.clone_gain_current_raw.copy()
            self.clone_gain_previous = self.clone_gain_previous_raw.copy()

        # Near-zero-net-charge sampler.  Raw edge packets can be much larger
        # than the allowed residual.  Foreground autozero measures each fixed
        # packet and injects its opposite.  Measurement error leaves a fraction
        # of raw packet; a separate floor represents cancellation noise/layout
        # asymmetry that does not scale with raw packet magnitude.
        fs = float(self.config.state_full_scale)
        raw_common_sigma = self.config.edge_charge_raw_common_std * fs
        raw_diff_sigma = self.config.edge_charge_raw_differential_std * fs
        self.edge_injection_raw_common = (
            np.zeros(e, dtype=float)
            if raw_common_sigma == 0.0
            else self.rng.normal(0.0, raw_common_sigma, size=e)
        )
        self.edge_injection_raw_diff = (
            np.zeros(e, dtype=float)
            if raw_diff_sigma == 0.0
            else self.rng.normal(0.0, raw_diff_sigma, size=e)
        )

        if self.config.edge_charge_autozero:
            if self.config.edge_charge_cancellation_error_std == 0.0:
                common_measured = self.edge_injection_raw_common.copy()
                diff_measured = self.edge_injection_raw_diff.copy()
            else:
                ec = self.rng.normal(
                    0.0, self.config.edge_charge_cancellation_error_std, size=e
                )
                ed = self.rng.normal(
                    0.0, self.config.edge_charge_cancellation_error_std, size=e
                )
                common_measured = self.edge_injection_raw_common * (1.0 + ec)
                diff_measured = self.edge_injection_raw_diff * (1.0 + ed)
            common_residual = self.edge_injection_raw_common - common_measured
            diff_residual = self.edge_injection_raw_diff - diff_measured
        else:
            common_measured = np.zeros(e, dtype=float)
            diff_measured = np.zeros(e, dtype=float)
            common_residual = self.edge_injection_raw_common.copy()
            diff_residual = self.edge_injection_raw_diff.copy()

        self.edge_injection_common_measured = common_measured
        self.edge_injection_diff_measured = diff_measured

        sc = self.config.edge_charge_residual_common_floor_std * fs
        sd = self.config.edge_charge_residual_differential_floor_std * fs
        if sc > 0.0:
            common_residual = common_residual + self.rng.normal(0.0, sc, size=e)
        if sd > 0.0:
            diff_residual = diff_residual + self.rng.normal(0.0, sd, size=e)

        self.edge_injection_common = np.asarray(common_residual, dtype=float)
        self.edge_injection_diff = np.asarray(diff_residual, dtype=float)
        self.edge_injection_a = self.edge_injection_common + self.edge_injection_diff
        self.edge_injection_b = self.edge_injection_common - self.edge_injection_diff

    def physical_components(self) -> tuple[Array, Array, Array]:
        onsite, raw_edges = self._edge_cell_decomposition()

        # Self path calibration is inherited from v0.3.
        qself = self._quantize_onsite_values(onsite) * self.self_gain

        pairs = self.backend.physical_edges()
        desired = np.asarray([raw_edges[p] for p in pairs], dtype=float)
        if self.config.edge_calibration:
            command = desired / self.edge_gain_measured
        else:
            command = desired
        qedge = self._quantize_edge_values(command) * self.edge_gain

        edge_matrix = np.zeros((self.nodes, self.nodes), dtype=float)
        for (i, j), amount in zip(pairs, qedge):
            if amount != 0.0:
                self._add_rank1(edge_matrix, i, j, float(amount))
        return np.asarray(qself, dtype=float), edge_matrix, np.asarray(qedge, dtype=float)

    def clone(self, *, seed: int | None = None) -> "TW1ACircuitTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ACircuitTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1ACircuitTile, dst: TW1ACircuitTile) -> None:
    """Make two manifests observe one calibrated physical tile."""
    dst.leakage_rates = src.leakage_rates.copy()
    dst.retention = src.retention.copy()
    dst._credit_offset_unit = src._credit_offset_unit.copy()

    dst.edge_gain = src.edge_gain.copy()
    dst.edge_gain_measured = src.edge_gain_measured.copy()
    dst.self_gain = src.self_gain.copy()
    dst.self_gain_measured = src.self_gain_measured.copy()

    dst.prev_ratio_gain_raw = src.prev_ratio_gain_raw.copy()
    dst.prev_ratio_gain_measured = src.prev_ratio_gain_measured.copy()
    dst.prev_ratio_trim = src.prev_ratio_trim.copy()
    dst.prev_ratio_gain = src.prev_ratio_gain.copy()

    dst.clone_gain_current_raw = src.clone_gain_current_raw.copy()
    dst.clone_gain_previous_raw = src.clone_gain_previous_raw.copy()
    dst.clone_gain_current_measured = src.clone_gain_current_measured.copy()
    dst.clone_gain_previous_measured = src.clone_gain_previous_measured.copy()
    dst.clone_trim_current = src.clone_trim_current.copy()
    dst.clone_trim_previous = src.clone_trim_previous.copy()
    dst.clone_gain_current = src.clone_gain_current.copy()
    dst.clone_gain_previous = src.clone_gain_previous.copy()

    dst.edge_injection_raw_common = src.edge_injection_raw_common.copy()
    dst.edge_injection_raw_diff = src.edge_injection_raw_diff.copy()
    dst.edge_injection_common_measured = src.edge_injection_common_measured.copy()
    dst.edge_injection_diff_measured = src.edge_injection_diff_measured.copy()
    dst.edge_injection_common = src.edge_injection_common.copy()
    dst.edge_injection_diff = src.edge_injection_diff.copy()
    dst.edge_injection_a = src.edge_injection_a.copy()
    dst.edge_injection_b = src.edge_injection_b.copy()


def _nominal_gain_config(config: TW1ACircuitV04Config) -> TW1ACircuitV04Config:
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


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ACircuitV04Config) -> float:
    tile = TW1ACircuitTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = LockstepCircuitInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ACircuitV04Config,
    *,
    target_fraction: float = 0.25,
    max_gain: int = 16384,
) -> float:
    if not 0 < target_fraction < 1:
        raise ValueError("target_fraction must be in (0,1)")
    if max_gain < 1 or max_gain & (max_gain - 1):
        raise ValueError("max_gain must be a positive power of two")
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
    config: TW1ACircuitV04Config,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACircuitTile, TW1ACircuitTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ACircuitTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ACircuitTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def _eval_pair(
    ti: LockstepCircuitInterpreter, di: LockstepCircuitInterpreter
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACircuitV04Config | None = None,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    cfg = TW1ACircuitV04Config() if config is None else config
    gain = recommend_sense_gain(task, cfg) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = LockstepCircuitInterpreter(exact_t)
    edi = LockstepCircuitInterpreter(exact_d)
    sti = LockstepCircuitInterpreter(shuffle_t)
    sdi = LockstepCircuitInterpreter(shuffle_d)

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
