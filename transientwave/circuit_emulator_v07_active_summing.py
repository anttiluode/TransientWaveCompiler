"""TW-1A v0.7: active charge summing with ratio-defined reciprocal edges.

C1b rejected passive destination charge sharing because an identical edge packet
changed a precharged destination by a different amount than an empty one.  v0.7
therefore treats the edge path as a sampled capacitor feeding an active virtual
summing node / charge integrator.

That changes two pieces of the v0.5/C0e abstraction:

* edge coefficient magnitude is the measured capacitor ratio directly,

      a_e = C_selected / C_state,

  not the passive-sharing curve alpha/(1+2 alpha);
* sampled-edge kT/C noise delivered to one endpoint is

      sigma_edge / VFS = b * sqrt(alpha),
      b = sqrt(kT/C_state) / VFS.

The old independent ``edge_gain_cv`` and ``edge_common_settling_loss`` fields are
forbidden here.  In this architecture the fabricated edge element *is* the
capacitor bank; its static site-to-site error is already represented by the
3%-unit-cap codebook.  Finite active-integrator gain and settling are budgeted
separately rather than multiplied into every edge as a second phantom device.

The -PREV coefficient is also structural.  The PREV physical bank becomes the
NEXT destination with a flipped logical orientation, so the emulator requires an
exact history coefficient and forbids the old ratio/trim error path.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .circuit_emulator_v05_edge_thermal import (
    TW1AEdgeThermalConfig,
    TW1AEdgeThermalTile as _C0ETile,
    copy_circuit_disorder as _copy_c0e_disorder,
)
from .circuit_emulator_v05_edge_thermal_fast import (
    CachedEdgeThermalLockstepInterpreter,
    _draw_reciprocal_noise,
)
from .circuit_emulator_v05_segmented_mismatch import segmented_capacitance_codes
from .emulator import _rms
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


@dataclass(frozen=True)
class TW1AActiveSummingConfig(TW1AEdgeThermalConfig):
    """v0.7 active-summing physical contract.

    ``edge_cunit_over_csum`` is retained for compatibility with the C0d/C0e
    code, but in v0.7 its meaning is explicitly Cunit/Cstate.
    """

    active_virtual_sum: bool = True
    structural_prev: bool = True

    def validate(self) -> None:
        super().validate()
        if not self.active_virtual_sum:
            raise ValueError("v0.7 requires an active virtual summing node")
        if not self.structural_prev:
            raise ValueError("v0.7 requires structural -PREV bank-role inversion")
        if self.edge_gain_cv != 0.0:
            raise ValueError(
                "v0.7 ratio-defined edge bank replaces legacy edge_gain_cv; it must be zero"
            )
        if self.edge_common_settling_loss != 0.0:
            raise ValueError(
                "v0.7 active integrator replaces legacy common edge-settling gain; it must be zero"
            )
        if self.prev_ratio_error_std != 0.0:
            raise ValueError("v0.7 structural -PREV requires prev_ratio_error_std=0")
        if self.prev_ratio_calibration_error_std != 0.0:
            raise ValueError(
                "v0.7 structural -PREV has no analog calibration path; "
                "prev_ratio_calibration_error_std must be zero"
            )
        if self.prev_ratio_calibration:
            raise ValueError(
                "v0.7 structural -PREV has no ratio trim; prev_ratio_calibration must be false"
            )


class TW1AActiveSummingTile(_C0ETile):
    """C0e fabricated tile with an active-integrator capacitor-ratio codebook."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1AActiveSummingConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1AActiveSummingConfig() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1AActiveSummingConfig

        # Replace C0d/C0e passive-sharing levels by the physical ratio itself.
        caps = segmented_capacitance_codes(self.edge_cap_units)
        ratio = float(self.config.edge_cunit_over_csum)  # Cunit/Cstate in v0.7
        self.edge_selected_capacitance_codes = caps
        self.edge_cap_levels = caps * ratio
        self.edge_codebook_steps = np.diff(self.edge_cap_levels, axis=1)
        self.edge_codebook_monotonic = np.all(self.edge_codebook_steps > 0.0, axis=1)
        self._rebuild_programmed_Q()

        # v0.7 history coefficient is a topology invariant, not a calibrated
        # analog ratio.  Keep explicit arrays because the inherited interpreter
        # consumes them semantically.
        self.prev_ratio_gain_raw = np.ones(self.nodes, dtype=float)
        self.prev_ratio_gain_measured = np.ones(self.nodes, dtype=float)
        self.prev_ratio_trim = np.ones(self.nodes, dtype=float)
        self.prev_ratio_gain = np.ones(self.nodes, dtype=float)

    @property
    def nominal_edge_full_scale(self) -> float:
        return 127.0 * float(self.config.edge_cunit_over_csum)

    @property
    def minimum_edge_full_scale(self) -> float:
        return float(np.min(self.edge_cap_levels[:, -1]))

    def edge_thermal_sigma_fraction(self, edge_amounts: Array) -> Array:
        """Active-integrator sampled-edge RMS packet as fraction of state FS."""
        alpha = self.edge_selected_cap_ratios(edge_amounts)
        return float(self.config.edge_ktc_base_fraction) * np.sqrt(alpha)

    def clone(self, *, seed: int | None = None) -> "TW1AActiveSummingTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1AActiveSummingTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1AActiveSummingTile, dst: TW1AActiveSummingTile) -> None:
    _copy_c0e_disorder(src, dst)
    dst.prev_ratio_gain_raw = np.ones(dst.nodes, dtype=float)
    dst.prev_ratio_gain_measured = np.ones(dst.nodes, dtype=float)
    dst.prev_ratio_trim = np.ones(dst.nodes, dtype=float)
    dst.prev_ratio_gain = np.ones(dst.nodes, dtype=float)
    dst._rebuild_programmed_Q()


class ActiveSummingLockstepInterpreter(CachedEdgeThermalLockstepInterpreter):
    """Cached C0e execution with v0.7 active-ratio thermal metadata."""

    tile: TW1AActiveSummingTile


# ---- training helpers -----------------------------------------------------

def _nominal_gain_config(config: TW1AActiveSummingConfig) -> TW1AActiveSummingConfig:
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        edge_ktc_base_fraction=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        edge_calibration_error_std=0.0,
        edge_lane_match_std=0.0,
        edge_unit_cap_sigma=0.0,
        self_gain_cv=0.0,
        self_calibration_error_std=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        terminal_clone_calibration_error_std=0.0,
        edge_charge_raw_common_std=0.0,
        edge_charge_raw_differential_std=0.0,
        edge_charge_cancellation_error_std=0.0,
        edge_charge_residual_common_floor_std=0.0,
        edge_charge_residual_differential_floor_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1AActiveSummingConfig) -> float:
    tile = TW1AActiveSummingTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = ActiveSummingLockstepInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1AActiveSummingConfig,
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
    config: TW1AActiveSummingConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1AActiveSummingTile, TW1AActiveSummingTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1AActiveSummingTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1AActiveSummingTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def _eval_pair(
    ti: ActiveSummingLockstepInterpreter,
    di: ActiveSummingLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1AActiveSummingConfig,
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

    eti = ActiveSummingLockstepInterpreter(exact_t)
    edi = ActiveSummingLockstepInterpreter(exact_d)
    sti = ActiveSummingLockstepInterpreter(shuffle_t)
    sdi = ActiveSummingLockstepInterpreter(shuffle_d)

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
