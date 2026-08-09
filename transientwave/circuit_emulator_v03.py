"""TW-1A v0.3 circuit emulator: charge-balanced edges + calibrated self path.

v0.2 established that lockstep F+A/F-A propagation removes the old long-pass
10-ppm coherence requirement.  Its first simultaneous corner then exposed two
implementation interactions:

1. independent lane-select edge charge injection accumulated as a repeated
   differential forcing term;
2. the large +/-3 self MDAC was treated as an uncalibrated analog gain.

v0.3 changes the physical abstraction rather than merely tightening numbers:

* edge switch injection is decomposed into common and residual differential
  components: q_A=q_common+q_diff, q_B=q_common-q_diff;
* the self MDAC is foreground calibrated.  A measured per-node gain is used to
  pre-distort the digital code, leaving only calibration residual + quantization.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .circuit_emulator import (
    LockstepCircuitInterpreter,
    TW1ACircuitEmulatorConfig,
    TW1ACircuitTile as _V02Tile,
)
from .emulator import _rms
from .emulator_v02 import signed_midtread_quantize
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


@dataclass(frozen=True)
class TW1ACircuitV03Config(TW1ACircuitEmulatorConfig):
    """Circuit-native v0.3 error model.

    ``self_gain_cv`` is raw uncalibrated silicon mismatch.  When
    ``self_calibration`` is enabled, the programmed code is divided by a
    measured gain. ``self_calibration_error_std`` is the RMS fractional error
    of that gain estimate, not the raw device mismatch.

    ``edge_charge_injection_common_std`` is repeated coherently in forward and
    both reverse lanes. ``edge_charge_injection_differential_std`` is the
    residual A/B imbalance after complementary/dummy/bottom-plate cancellation.
    """

    self_calibration: bool = True
    self_calibration_error_std: float = 0.0

    charge_balanced_edge_sampling: bool = True
    edge_charge_injection_common_std: float = 0.0
    edge_charge_injection_differential_std: float = 0.0

    def validate(self) -> None:
        super().validate()
        if self.charge_balanced_edge_sampling and self.edge_charge_injection_std != 0.0:
            raise ValueError(
                "v0.3 charge-balanced mode requires legacy independent "
                "edge_charge_injection_std=0"
            )
        for name in (
            "self_calibration_error_std",
            "edge_charge_injection_common_std",
            "edge_charge_injection_differential_std",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")


class TW1ACircuitTile(_V02Tile):
    """v0.3 physical tile with foreground self calibration and balanced switching."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACircuitV03Config | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ACircuitV03Config() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACircuitV03Config

        e = len(self.backend.physical_edges())
        n = self.nodes

        # The true raw self gain was already drawn by v0.2.  Calibration sees
        # it through a noisy measurement.  Clip only pathological negative
        # measurement gains; realistic residuals are far from that regime.
        if self.config.self_calibration_error_std == 0.0:
            cal_err = np.zeros(n, dtype=float)
        else:
            cal_err = self.rng.normal(
                0.0, self.config.self_calibration_error_std, size=n
            )
        self.self_gain_measured = np.maximum(
            self.self_gain * (1.0 + cal_err), 1e-9
        )

        fs = self.config.state_full_scale
        sc = self.config.edge_charge_injection_common_std * fs
        sd = self.config.edge_charge_injection_differential_std * fs
        self.edge_injection_common = (
            np.zeros(e, dtype=float)
            if sc == 0.0
            else self.rng.normal(0.0, sc, size=e)
        )
        self.edge_injection_diff = (
            np.zeros(e, dtype=float)
            if sd == 0.0
            else self.rng.normal(0.0, sd, size=e)
        )

        # Replace the v0.2 independent lane packets.  Forward uses lane A;
        # reverse A reuses that exact packet, while reverse B differs only by
        # the residual balanced-switch component.
        self.edge_injection_a = self.edge_injection_common + self.edge_injection_diff
        self.edge_injection_b = self.edge_injection_common - self.edge_injection_diff

    def _quantize_onsite_values(self, x: Array) -> Array:
        desired = np.asarray(x, dtype=float)
        if self.config.self_calibration:
            command = desired / self.self_gain_measured
        else:
            command = desired
        return signed_midtread_quantize(
            command,
            self.config.self_bits,
            self.config.self_full_scale,
        )

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
    """Make target/distractor manifests observe one physical calibrated chip."""
    dst.leakage_rates = src.leakage_rates.copy()
    dst.retention = src.retention.copy()
    dst._credit_offset_unit = src._credit_offset_unit.copy()
    dst.edge_gain = src.edge_gain.copy()
    dst.self_gain = src.self_gain.copy()
    dst.self_gain_measured = src.self_gain_measured.copy()
    dst.prev_ratio_gain = src.prev_ratio_gain.copy()
    dst.clone_gain_current = src.clone_gain_current.copy()
    dst.clone_gain_previous = src.clone_gain_previous.copy()
    dst.edge_injection_common = src.edge_injection_common.copy()
    dst.edge_injection_diff = src.edge_injection_diff.copy()
    dst.edge_injection_a = src.edge_injection_a.copy()
    dst.edge_injection_b = src.edge_injection_b.copy()


def _nominal_gain_config(config: TW1ACircuitV03Config) -> TW1ACircuitV03Config:
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        edge_gain_cv=0.0,
        self_gain_cv=0.0,
        self_calibration_error_std=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        edge_settling_error=0.0,
        ab_edge_memory=0.0,
        edge_charge_injection_std=0.0,
        edge_charge_injection_common_std=0.0,
        edge_charge_injection_differential_std=0.0,
        prev_ratio_error_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ACircuitV03Config) -> float:
    tile = TW1ACircuitTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = LockstepCircuitInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ACircuitV03Config,
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
    config: TW1ACircuitV03Config,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACircuitTile, TW1ACircuitTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1ACircuitTile(task["target"], tc, sense_gain=sense_gain)
    d = TW1ACircuitTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(
    ti: LockstepCircuitInterpreter, di: LockstepCircuitInterpreter
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACircuitV03Config | None = None,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    cfg = TW1ACircuitV03Config() if config is None else config
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
            shuffle_t.apply_credits(-gc[perm], step_size=step_size, normalize_rms=normalize_rms)
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
