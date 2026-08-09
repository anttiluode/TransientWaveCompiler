"""TW-1A v0.5 C0e: circuit-native sampled-edge thermal noise.

The legacy emulator stress term ``state_noise_std`` adds an independent random
state disturbance to every node on every update.  That model is intentionally
forbidden here.  The proposed switched-cap edge cell instead samples a physical
edge capacitor and transfers its noisy charge equal/opposite to the two endpoint
state capacitors.

For selected physical edge capacitance ratio

    alpha = Cedge / Cstate,

a sampled edge-cap voltage noise sqrt(kT/Cedge) gives one endpoint after charge
redistribution approximately

    sigma_edge / VFS
      = base_ktc_fraction * sqrt(alpha) / (1 + 2 alpha),

where

    base_ktc_fraction = sqrt(kT/Cstate) / VFS.

Noise is resampled independently for each physical edge use and for forward,
reverse-A and reverse-B contexts, while preserving the reciprocal spatial
structure (+eta at one endpoint, -eta at the other).  Magnitude code zero has
alpha=0 and injects no edge-sampling thermal packet.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator_v05 import PhaseSymmetricLockstepInterpreter
from .circuit_emulator_v05_segmented_mismatch import (
    TW1ASegmentedMismatchConfig,
    TW1ASegmentedMismatchTile as _C0DTile,
    copy_circuit_disorder as _copy_c0d_disorder,
    segmented_capacitance_codes,
)
from .emulator import _rms
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


@dataclass(frozen=True)
class TW1AEdgeThermalConfig(TW1ASegmentedMismatchConfig):
    """C0e edge-sampling thermal-noise parameterization."""

    edge_ktc_base_fraction: float = 0.0

    def validate(self) -> None:
        super().validate()
        if self.state_noise_std != 0.0:
            raise ValueError(
                "C0e edge-thermal model requires legacy independent state_noise_std=0"
            )
        value = float(self.edge_ktc_base_fraction)
        if not np.isfinite(value) or value < 0.0:
            raise ValueError("edge_ktc_base_fraction must be finite and nonnegative")


class TW1AEdgeThermalTile(_C0DTile):
    """C0d fabricated tile plus selected-capacitance thermal-noise metadata."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1AEdgeThermalConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1AEdgeThermalConfig() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1AEdgeThermalConfig
        self.edge_selected_capacitance_codes = segmented_capacitance_codes(
            self.edge_cap_units
        )

    def edge_selected_code_indices(self, edge_amounts: Array) -> Array:
        """Recover the physical magnitude code used by each programmed edge."""
        amounts = np.asarray(edge_amounts, dtype=float)
        e = len(self.backend.physical_edges())
        if amounts.shape != (e,):
            raise ValueError("edge amount vector shape mismatch")

        # physical_components() returns codebook level * true calibrated common
        # transfer gain. Divide that common transfer back out to identify the
        # selected raw capacitor-codebook level.
        raw_level = np.abs(amounts / self.edge_effective_gain_raw)
        idx = np.zeros(e, dtype=int)
        for k in range(e):
            idx[k] = int(np.argmin(np.abs(self.edge_cap_levels[k] - raw_level[k])))
        return idx

    def edge_selected_cap_ratios(self, edge_amounts: Array) -> Array:
        idx = self.edge_selected_code_indices(edge_amounts)
        selected_units = self.edge_selected_capacitance_codes[
            np.arange(len(idx)), idx
        ]
        return selected_units * float(self.config.edge_cunit_over_csum)

    def edge_thermal_sigma_fraction(self, edge_amounts: Array) -> Array:
        """One-endpoint RMS packet noise as fraction of state full scale."""
        alpha = self.edge_selected_cap_ratios(edge_amounts)
        base = float(self.config.edge_ktc_base_fraction)
        return base * np.sqrt(alpha) / (1.0 + 2.0 * alpha)

    def edge_thermal_node_noise(self, edge_amounts: Array) -> Array:
        """Draw one reciprocal equal/opposite thermal packet per active edge."""
        sigma = (
            self.edge_thermal_sigma_fraction(edge_amounts)
            * float(self.config.state_full_scale)
        )
        eta = self.rng.normal(0.0, sigma)
        out = np.zeros(self.nodes, dtype=float)
        for k, (i, j) in enumerate(self.backend.physical_edges()):
            q = float(eta[k])
            if q == 0.0:
                continue
            out[i] += q
            out[j] -= q
        return out

    def clone(self, *, seed: int | None = None) -> "TW1AEdgeThermalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1AEdgeThermalTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1AEdgeThermalTile, dst: TW1AEdgeThermalTile) -> None:
    _copy_c0d_disorder(src, dst)
    dst.edge_selected_capacitance_codes = src.edge_selected_capacitance_codes.copy()


class EdgeThermalLockstepInterpreter(PhaseSymmetricLockstepInterpreter):
    """Phase-symmetric interpreter with edge-local kT/C packet noise."""

    tile: TW1AEdgeThermalTile

    def _run_forward(self, *, stochastic: bool) -> tuple[Array, Array, Array, Array]:
        self._reset_lane_a()
        self_coeff, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)

        for k in range(self.tile.steps):
            x = self.tile.retention * self.a_current
            xm1 = self.tile.retention * self.a_previous
            nxt = (
                self_coeff * x
                + edge_matrix @ x
                - self.tile.prev_ratio_gain * xm1
                + src[k]
                + inj_a
            )
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                nxt = nxt + self.tile.edge_thermal_node_noise(edge_amounts)
            self.a_previous, self.a_current = x, self._clip(nxt)
            trace[k] = self._sense(self.a_current)

        self.forward_trace = trace
        return self_coeff, edge_matrix, edge_amounts, inj_a

    def _run_lockstep_reverse(
        self,
        self_coeff: Array,
        edge_matrix: Array,
        edge_amounts: Array,
        *,
        stochastic: bool,
    ) -> Array:
        if self.error_schedule is None:
            raise RuntimeError("reverse requires error schedule")
        src_fwd = self._forward_source_schedule()
        qerr = self.error_schedule
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        inj_b = self.tile.edge_injection_node_vector("B", edge_amounts)
        edge_matrix_a, edge_matrix_b = self.tile.lane_edge_matrices(edge_amounts)

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus_sum = np.zeros_like(acc)
        minus_sum = np.zeros_like(acc)
        credit_ret = math.exp(-self.tile.config.credit_accumulator_leakage)

        asym = self.tile.config.error_dac_sign_asymmetry
        plus_gain = 1.0 + 0.5 * asym
        minus_gain = 1.0 - 0.5 * asym

        for j in range(1, self.tile.steps + 1):
            da = self.tile.edge_difference_vector(self.a_current)
            db = self.tile.edge_difference_vector(self.b_current)
            pa = self._lcc_square(da)
            pb = self._lcc_square(db)
            plus_sum += pa
            minus_sum += pb
            acc = credit_ret * acc + 0.25 * (pa - pb)

            if j == self.tile.steps:
                continue

            source_index = self.tile.steps - j
            common = src_fwd[source_index]
            qa = plus_gain * qerr[source_index]
            qb = -minus_gain * qerr[source_index]

            ax = self.tile.retention * self.a_current
            ap = self.tile.retention * self.a_previous
            bx = self.tile.retention * self.b_current
            bp = self.tile.retention * self.b_previous

            edge_a = edge_matrix_a @ ax
            edge_b = edge_matrix_b @ bx

            next_a = (
                self_coeff * ax
                + edge_a
                - self.tile.prev_ratio_gain * ap
                + common
                + qa
                + inj_a
            )
            next_b = (
                self_coeff * bx
                + edge_b
                - self.tile.prev_ratio_gain * bp
                + common
                + qb
                + inj_b
            )
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                # A and B sample different physical state differences and thus
                # acquire independent kT/C packets, but each packet remains
                # reciprocal/equal-opposite in space.
                next_a = next_a + self.tile.edge_thermal_node_noise(edge_amounts)
                next_b = next_b + self.tile.edge_thermal_node_noise(edge_amounts)

            self.a_previous, self.a_current = ax, self._clip(next_a)
            self.b_previous, self.b_current = bx, self._clip(next_b)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _nominal_gain_config(config: TW1AEdgeThermalConfig) -> TW1AEdgeThermalConfig:
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        edge_ktc_base_fraction=0.0,
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


def _initial_raw_peak(manifest: dict[str, Any], config: TW1AEdgeThermalConfig) -> float:
    tile = TW1AEdgeThermalTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = EdgeThermalLockstepInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1AEdgeThermalConfig,
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
    config: TW1AEdgeThermalConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1AEdgeThermalTile, TW1AEdgeThermalTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1AEdgeThermalTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1AEdgeThermalTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def _eval_pair(
    ti: EdgeThermalLockstepInterpreter,
    di: EdgeThermalLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1AEdgeThermalConfig,
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

    eti = EdgeThermalLockstepInterpreter(exact_t)
    edi = EdgeThermalLockstepInterpreter(exact_d)
    sti = EdgeThermalLockstepInterpreter(shuffle_t)
    sdi = EdgeThermalLockstepInterpreter(shuffle_d)

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
