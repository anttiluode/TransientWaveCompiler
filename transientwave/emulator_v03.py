"""TW-1A emulator v0.3: zero-preserving converters plus static sense PGA."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig, _rms
from .emulator_v02 import TW1APhysicalTile as _V02Tile, signed_midtread_quantize
from .order_contrast import (
    OrderContrastTrainingResult,
    _copy_static_chip_disorder,
    _sync_theta,
    contrast_gradient,
    contrast_from_energies,
)


Array = np.ndarray


class TW1APhysicalTile(_V02Tile):
    """v0.3 tile with a fixed analog sense gain ahead of the ADC."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1APhysicalTileConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        if sense_gain <= 0 or not np.isfinite(sense_gain):
            raise ValueError("sense_gain must be finite and positive")
        self.sense_gain = float(sense_gain)
        super().__init__(manifest, config)

    def quantize_adc(self, x: Array | float) -> Array:
        raw = np.asarray(x, dtype=float)
        amplified = raw * self.sense_gain
        q = signed_midtread_quantize(
            amplified, self.config.adc_bits, self.config.adc_full_scale
        )
        return q / self.sense_gain

    def clone(self, *, seed: int | None = None) -> "TW1APhysicalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APhysicalTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
            out._credit_offset_unit = self._credit_offset_unit.copy()
        return out


def _nominal_prediction_config(config: TW1APhysicalTileConfig) -> TW1APhysicalTileConfig:
    """Compiler-model conditions used only to select the static PGA gain."""
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.0,
        differential_pass_drift=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1APhysicalTileConfig) -> float:
    tile = TW1APhysicalTile(manifest, _nominal_prediction_config(config), sense_gain=1.0)
    interp = MicrocodeInterpreter(tile)
    tile.reset_state()
    interp._run_forward(tile.steps, stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    *,
    target_fraction: float = 0.25,
    max_gain: int = 16384,
) -> float:
    """Choose the frozen binary PGA gain from the compiler's initial model."""
    if not 0 < target_fraction < 1:
        raise ValueError("target_fraction must be in (0,1)")
    if max_gain < 1 or max_gain & (max_gain - 1):
        raise ValueError("max_gain must be a positive power of two")

    peak = max(
        _initial_raw_peak(task["target"], config),
        _initial_raw_peak(task["distractor"], config),
    )
    if peak <= 0:
        return float(max_gain)

    target = float(config.adc_full_scale) * float(target_fraction)
    gain = 1
    while gain * 2 <= max_gain and peak * (gain * 2) <= target:
        gain *= 2
    return float(gain)


def _make_pair(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1APhysicalTile, TW1APhysicalTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1APhysicalTile(task["target"], tc, sense_gain=sense_gain)
    d = TW1APhysicalTile(task["distractor"], dc, sense_gain=sense_gain)
    _copy_static_chip_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(
    ti: MicrocodeInterpreter, di: MicrocodeInterpreter
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    *,
    sense_gain: float | None = None,
    iterations: int = 40,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    """Run contrast learning through the v0.3 static-PGA tile."""
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)
    exact_t, exact_d = _make_pair(task, config, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, config, gain, seed_offset=100_003)

    # Same static physical chip for exact and shuffled arms; only credit placement differs.
    _copy_static_chip_disorder(exact_t, shuffle_t)
    _copy_static_chip_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = MicrocodeInterpreter(exact_t)
    edi = MicrocodeInterpreter(exact_d)
    sti = MicrocodeInterpreter(shuffle_t)
    sdi = MicrocodeInterpreter(shuffle_d)

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

    result = OrderContrastTrainingResult(
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
    )
    return result, gain
