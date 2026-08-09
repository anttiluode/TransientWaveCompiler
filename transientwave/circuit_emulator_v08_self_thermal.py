"""TW-1A v0.8 with local self-sampling kT/C noise.

C1e2/C1e3 establish a two-slice reusable self sample bank.  For a physical
self coefficient magnitude |d|, two equal slices each use capacitor ratio
alpha=|d|/2.  Each fresh sample has voltage noise sqrt(kT/Cslice), and transfer
through the active charge integrator multiplies it by alpha.  The two
independent slice variances therefore add to

    2 * [alpha * sqrt(kT/(alpha*Cstate))]^2
      = |d| * kT/Cstate.

Thus the total per-tick self-sampling noise law is independent of the number of
equal slices:

    sigma_self / VFS = b_self * sqrt(|d|),
    b_self = sqrt(kT/Cstate)/VFS.

This module adds that missing node-local thermal packet without perturbing the
existing edge-thermal or credit RNG streams.  A dedicated RNG is derived from
the tile seed.  The law is applied independently in forward, common reverse and
difference reverse contexts because the self bank is resampled between uses.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator_v05_edge_thermal_fast import _draw_reciprocal_noise
from .circuit_emulator_v07_active_summing import recommend_sense_gain
from .circuit_emulator_v08_common_diff import (
    CommonDiffLockstepInterpreter,
    _eval_pair,
)
from .circuit_emulator_v08_site_ratio import (
    TW1ACommonDiffSiteConfig,
    TW1ACommonDiffSiteTile,
    copy_circuit_disorder as _copy_site_disorder,
)
from .emulator import _rms
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


@dataclass(frozen=True)
class TW1ACommonDiffSelfThermalConfig(TW1ACommonDiffSiteConfig):
    self_ktc_base_fraction: float = 0.0
    self_ktc_seed_salt: int = 0x5E1F7

    def validate(self) -> None:
        super().validate()
        b = float(self.self_ktc_base_fraction)
        if not np.isfinite(b) or b < 0.0:
            raise ValueError("self_ktc_base_fraction must be finite and nonnegative")


class TW1ACommonDiffSelfThermalTile(TW1ACommonDiffSiteTile):
    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACommonDiffSelfThermalConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = (
            TW1ACommonDiffSelfThermalConfig(prev_ratio_calibration=False)
            if config is None
            else config
        )
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACommonDiffSelfThermalConfig
        noise_seed = (
            int(cfg.seed) * 1_000_033 + int(cfg.self_ktc_seed_salt)
        ) & 0xFFFFFFFFFFFFFFFF
        self.self_thermal_rng = np.random.default_rng(noise_seed)

    def self_thermal_sigma_fraction(self, self_coeff: Array) -> Array:
        coeff = np.asarray(self_coeff, dtype=float)
        return float(self.config.self_ktc_base_fraction) * np.sqrt(np.abs(coeff))

    def draw_self_thermal_noise(self, self_coeff: Array) -> Array:
        sigma = self.self_thermal_sigma_fraction(self_coeff) * float(
            self.config.state_full_scale
        )
        return self.self_thermal_rng.normal(0.0, sigma, size=self.nodes)

    def clone(self, *, seed: int | None = None) -> "TW1ACommonDiffSelfThermalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ACommonDiffSelfThermalTile(
            self.manifest, cfg, sense_gain=self.sense_gain
        )
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(
    src: TW1ACommonDiffSelfThermalTile,
    dst: TW1ACommonDiffSelfThermalTile,
) -> None:
    # Dynamic thermal RNG streams deliberately remain tied to each tile's own
    # seed. Only static fabricated disorder is copied.
    _copy_site_disorder(src, dst)


class CommonDiffSelfThermalInterpreter(CommonDiffLockstepInterpreter):
    tile: TW1ACommonDiffSelfThermalTile

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
                next_c = next_c + _draw_reciprocal_noise(
                    self.tile, edge_sigma_fraction
                )
                next_d = next_d + _draw_reciprocal_noise(
                    self.tile, edge_sigma_fraction
                )
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                next_c = next_c + self.tile.draw_self_thermal_noise(self_coeff)
                next_d = next_d + self.tile.draw_self_thermal_noise(self_coeff)

            self.a_previous, self.a_current = cx, self._clip(next_c)
            self.b_previous, self.b_current = dx, self._clip(next_d)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _make_pair(
    task: dict[str, Any],
    config: TW1ACommonDiffSelfThermalConfig,
    sense_gain: float,
    *,
    seed_offset: int,
):
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ACommonDiffSelfThermalTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ACommonDiffSelfThermalTile(
        task["distractor"], dc, sense_gain=sense_gain
    )
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def run_order_contrast_training(
    task,
    config: TW1ACommonDiffSelfThermalConfig,
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
    _sync_theta(exact_t, shuffle_t); _sync_theta(exact_t, shuffle_d)

    eti = CommonDiffSelfThermalInterpreter(exact_t)
    edi = CommonDiffSelfThermalInterpreter(exact_d)
    sti = CommonDiffSelfThermalInterpreter(shuffle_t)
    sdi = CommonDiffSelfThermalInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    ec=[c0]; sc=[sc0]; ete=[et0]; ede=[ed0]; ste=[st0]; sde=[sd0]; mt=[]; md=[]; cr=[]
    perm=np.random.default_rng(shuffle_seed).permutation(len(exact_t.theta))
    for _ in range(int(iterations)):
        rt, rd = eti.execute(stochastic_forward=True), edi.execute(stochastic_forward=True)
        et, ed = float(rt["objective"]), float(rd["objective"])
        gc=contrast_gradient(et,ed,np.asarray(rt["credits"]),np.asarray(rd["credits"]),eps=eps)
        mt.append(et); md.append(ed); cr.append(_rms(gc))
        exact_t.apply_credits(-gc,step_size=step_size,normalize_rms=normalize_rms); _sync_theta(exact_t,exact_d)
        if include_shuffle:
            shuffle_t.apply_credits(-gc[perm],step_size=step_size,normalize_rms=normalize_rms); _sync_theta(shuffle_t,shuffle_d)
        etv,edv,cv=_eval_pair(eti,edi); stv,sdv,scv=_eval_pair(sti,sdi)
        ete.append(etv); ede.append(edv); ec.append(cv); ste.append(stv); sde.append(sdv); sc.append(scv)
    return OrderContrastTrainingResult(exact_contrast=ec,shuffled_contrast=sc,exact_target_energy=ete,exact_distractor_energy=ede,shuffled_target_energy=ste,shuffled_distractor_energy=sde,measured_target_energy=mt,measured_distractor_energy=md,combined_credit_rms=cr,final_theta=exact_t.theta.copy(),final_theta_shuffled=shuffle_t.theta.copy()), gain
