"""TW-1A v0.9: measured fixed +2 inertial path plus small sampled residual self.

For the compiled second-order recurrence

    z[n+1] = Q z[n] - z[n-1] + u[n],

write the local self contribution as

    d_i = g_i + k_i,

where the nominal fixed inertial path has g_i ~= 2 and only k_i is implemented
by the programmable sampled-capacitor self path.  The compiler measures g_i and
programs k_i = d_i - g_i(measured).

This preserves the v0.8 state representation, common/difference echo and
structural -PREV.  It is algebraically motivated by the exact kick-drift split
K=Q-2I but does not assume a noiseless fixed path: an explicit additive
``inertial_noise_fraction`` is drawn independently on every node/tick/context.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator_v05_edge_thermal_fast import _draw_reciprocal_noise
from .circuit_emulator_v07_active_summing import recommend_sense_gain
from .circuit_emulator_v08_common_diff import _eval_pair
from .circuit_emulator_v08_self_thermal import (
    CommonDiffSelfThermalInterpreter,
    TW1ACommonDiffSelfThermalConfig,
    TW1ACommonDiffSelfThermalTile,
    copy_circuit_disorder as _copy_v08_self_disorder,
)
from .emulator import _rms
from .emulator_v02 import signed_midtread_quantize
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


@dataclass(frozen=True)
class TW1AInertialBaselineConfig(TW1ACommonDiffSelfThermalConfig):
    inertial_nominal_gain: float = 2.0
    inertial_raw_gain_std: float = 0.01
    inertial_measurement_error_std: float = 0.001
    inertial_noise_fraction: float = 0.0
    inertial_seed_salt: int = 0x1A37A
    inertial_noise_seed_salt: int = 0x1A37B

    residual_self_bits: int | None = 10
    residual_self_full_scale: float = 0.125

    def validate(self) -> None:
        super().validate()
        if not np.isfinite(self.inertial_nominal_gain):
            raise ValueError("inertial_nominal_gain must be finite")
        for name in (
            "inertial_raw_gain_std",
            "inertial_measurement_error_std",
            "inertial_noise_fraction",
        ):
            v = float(getattr(self, name))
            if not np.isfinite(v) or v < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.residual_self_bits is not None and int(self.residual_self_bits) < 2:
            raise ValueError("residual_self_bits must be >=2 or None")
        if not np.isfinite(self.residual_self_full_scale) or self.residual_self_full_scale <= 0.0:
            raise ValueError("residual_self_full_scale must be finite and positive")


class TW1AInertialBaselineTile(TW1ACommonDiffSelfThermalTile):
    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1AInertialBaselineConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1AInertialBaselineConfig(prev_ratio_calibration=False) if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1AInertialBaselineConfig

        n = self.nodes
        static_seed = (
            int(cfg.seed) * 1_000_081 + int(cfg.inertial_seed_salt)
        ) & 0xFFFFFFFFFFFFFFFF
        rng = np.random.default_rng(static_seed)
        raw_scale = 1.0 + rng.normal(0.0, float(cfg.inertial_raw_gain_std), size=n)
        self.inertial_gain_raw = float(cfg.inertial_nominal_gain) * raw_scale
        meas_frac = rng.normal(0.0, float(cfg.inertial_measurement_error_std), size=n)
        self.inertial_gain_measured = self.inertial_gain_raw * (1.0 + meas_frac)

        noise_seed = (
            int(cfg.seed) * 1_000_087 + int(cfg.inertial_noise_seed_salt)
        ) & 0xFFFFFFFFFFFFFFFF
        self.inertial_noise_rng = np.random.default_rng(noise_seed)

        self._last_residual_target = np.zeros(n, dtype=float)
        self._last_residual_programmed = np.zeros(n, dtype=float)
        self._last_residual_actual = np.zeros(n, dtype=float)
        self._last_residual_saturated = np.zeros(n, dtype=bool)

    def _quantize_residual_self(self, x: Array) -> Array:
        return signed_midtread_quantize(
            np.asarray(x, dtype=float),
            self.config.residual_self_bits,
            self.config.residual_self_full_scale,
        )

    def physical_components(self) -> tuple[Array, Array, Array]:
        # Keep the entire v0.8 measured reciprocal-edge realization unchanged.
        _, edge_matrix, edge_amounts = super().physical_components()

        # ``onsite`` is the logical self coefficient after rank-one edge
        # decomposition and before the old full-range self quantizer.
        onsite, _ = self._edge_cell_decomposition()
        target = np.asarray(onsite, dtype=float) - self.inertial_gain_measured
        fs = float(self.config.residual_self_full_scale)
        saturated = np.abs(target) > fs + 1e-15
        programmed = self._quantize_residual_self(target)
        actual = programmed * self.self_gain
        total_self = self.inertial_gain_raw + actual

        self._last_residual_target = target.copy()
        self._last_residual_programmed = np.asarray(programmed, dtype=float).copy()
        self._last_residual_actual = np.asarray(actual, dtype=float).copy()
        self._last_residual_saturated = saturated.copy()
        return np.asarray(total_self, dtype=float), edge_matrix, edge_amounts

    @property
    def residual_self_saturated(self) -> bool:
        # Refresh against the current programmed operator before reporting.
        self.physical_components()
        return bool(np.any(self._last_residual_saturated))

    @property
    def max_abs_residual_target(self) -> float:
        self.physical_components()
        return float(np.max(np.abs(self._last_residual_target)))

    @property
    def max_abs_residual_actual(self) -> float:
        self.physical_components()
        return float(np.max(np.abs(self._last_residual_actual)))

    def self_thermal_sigma_fraction(self, self_coeff: Array) -> Array:
        # The sampled capacitor path now carries only k_residual, not g+k.
        _ = self_coeff
        return float(self.config.self_ktc_base_fraction) * np.sqrt(
            np.abs(self._last_residual_actual)
        )

    def draw_inertial_noise(self) -> Array:
        sigma = float(self.config.inertial_noise_fraction) * float(self.config.state_full_scale)
        if sigma <= 0.0:
            return np.zeros(self.nodes, dtype=float)
        return self.inertial_noise_rng.normal(0.0, sigma, size=self.nodes)

    def clone(self, *, seed: int | None = None) -> "TW1AInertialBaselineTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1AInertialBaselineTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1AInertialBaselineTile, dst: TW1AInertialBaselineTile) -> None:
    # Parent copy preserves all v0.8 static disorder but intentionally leaves
    # dynamic thermal RNG streams independent.
    _copy_v08_self_disorder(src, dst)
    dst.inertial_gain_raw = src.inertial_gain_raw.copy()
    dst.inertial_gain_measured = src.inertial_gain_measured.copy()
    dst._rebuild_programmed_Q()


class InertialBaselineInterpreter(CommonDiffSelfThermalInterpreter):
    tile: TW1AInertialBaselineTile

    def _run_forward(self, *, stochastic: bool):
        self._reset_lane_a()
        self_coeff, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)
        edge_sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

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
                nxt = nxt + _draw_reciprocal_noise(self.tile, edge_sigma_fraction)
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                nxt = nxt + self.tile.draw_self_thermal_noise(self_coeff)
            if stochastic and self.tile.config.inertial_noise_fraction > 0.0:
                nxt = nxt + self.tile.draw_inertial_noise()
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
        inj_c = self.tile.edge_injection_node_vector("A", edge_amounts)
        inj_d = self.tile.edge_injection_node_vector("B", edge_amounts)
        edge_matrix_c, edge_matrix_d = self.tile.lane_edge_matrices(edge_amounts)
        edge_sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus_sum = np.zeros_like(acc)
        minus_sum = np.zeros_like(acc)
        credit_ret = math.exp(-self.tile.config.credit_accumulator_leakage)

        for j in range(1, self.tile.steps + 1):
            dc = self.tile.edge_difference_vector(self.a_current)
            dd = self.tile.edge_difference_vector(self.b_current)
            dplus = dc + dd
            dminus = dc - dd
            pplus = self._lcc_square(dplus)
            pminus = self._lcc_square(dminus)
            plus_sum += pplus
            minus_sum += pminus
            acc = credit_ret * acc + 0.25 * (pplus - pminus)

            if j == self.tile.steps:
                continue

            source_index = self.tile.steps - j
            common_source = src_fwd[source_index]
            diff_error = qerr[source_index]

            cx = self.tile.retention * self.a_current
            cp = self.tile.retention * self.a_previous
            dx = self.tile.retention * self.b_current
            dp = self.tile.retention * self.b_previous

            next_c = (
                self_coeff * cx
                + edge_matrix_c @ cx
                - self.tile.prev_ratio_gain * cp
                + common_source
                + inj_c
            )
            next_d = (
                self_coeff * dx
                + edge_matrix_d @ dx
                - self.tile.prev_ratio_gain * dp
                + diff_error
                + inj_d
            )

            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                next_c = next_c + _draw_reciprocal_noise(self.tile, edge_sigma_fraction)
                next_d = next_d + _draw_reciprocal_noise(self.tile, edge_sigma_fraction)
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                next_c = next_c + self.tile.draw_self_thermal_noise(self_coeff)
                next_d = next_d + self.tile.draw_self_thermal_noise(self_coeff)
            if stochastic and self.tile.config.inertial_noise_fraction > 0.0:
                next_c = next_c + self.tile.draw_inertial_noise()
                next_d = next_d + self.tile.draw_inertial_noise()

            self.a_previous, self.a_current = cx, self._clip(next_c)
            self.b_previous, self.b_current = dx, self._clip(next_d)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _make_pair(task, config, sense_gain, *, seed_offset):
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1AInertialBaselineTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1AInertialBaselineTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def run_order_contrast_training(
    task,
    config: TW1AInertialBaselineConfig,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
):
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, config, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, config, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = InertialBaselineInterpreter(exact_t)
    edi = InertialBaselineInterpreter(exact_d)
    sti = InertialBaselineInterpreter(shuffle_t)
    sdi = InertialBaselineInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    ec=[c0]; sc=[sc0]; ete=[et0]; ede=[ed0]; ste=[st0]; sde=[sd0]; mt=[]; md=[]; cr=[]
    perm=np.random.default_rng(shuffle_seed).permutation(len(exact_t.theta))

    for _ in range(int(iterations)):
        rt, rd = eti.execute(stochastic_forward=True), edi.execute(stochastic_forward=True)
        et, ed = float(rt["objective"]), float(rd["objective"])
        gc = contrast_gradient(
            et, ed, np.asarray(rt["credits"]), np.asarray(rd["credits"]), eps=eps
        )
        mt.append(et); md.append(ed); cr.append(_rms(gc))
        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(exact_t, exact_d)
        if include_shuffle:
            shuffle_t.apply_credits(-gc[perm], step_size=step_size, normalize_rms=normalize_rms)
            _sync_theta(shuffle_t, shuffle_d)
        etv, edv, cv = _eval_pair(eti, edi)
        stv, sdv, scv = _eval_pair(sti, sdi)
        ete.append(etv); ede.append(edv); ec.append(cv); ste.append(stv); sde.append(sdv); sc.append(scv)

    return OrderContrastTrainingResult(
        exact_contrast=ec,
        shuffled_contrast=sc,
        exact_target_energy=ete,
        exact_distractor_energy=ede,
        shuffled_target_energy=ste,
        shuffled_distractor_energy=sde,
        measured_target_energy=mt,
        measured_distractor_energy=md,
        combined_credit_rms=cr,
        final_theta=exact_t.theta.copy(),
        final_theta_shuffled=shuffle_t.theta.copy(),
    ), gain
