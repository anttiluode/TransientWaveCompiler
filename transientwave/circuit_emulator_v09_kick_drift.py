"""TW-1A v0.9 full kick-drift physical interpreter.

This module keeps the v0.8 common/difference echo and reciprocal edge hardware,
but reinterprets the two stored vectors per context as

    Z = z[n]
    P = z[n] - z[n-1]

and advances the exactly equivalent shears

    P <- P + (Q - 2 I) Z + source
    Z <- Z + P.

The large near-2 node-local self term therefore disappears from the
programmable sampled self path.  Edge and residual-self kT/C enter the P kick.
A separate ``drift_ktc_base_fraction`` models sampling noise on the unity
``Z <- Z + P`` transfer.  The same drift mechanism is charged once for the
terminal inverse-drift mirror ``Z <- Z - P``.

C1f established only deterministic topology.  This module is the first learning
model that assigns thermal noise to the surviving unity drift shear.  It does
not yet add a new drift-specific switch-kick residual.
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
class TW1AKickDriftConfig(TW1ACommonDiffSelfThermalConfig):
    kick_self_bits: int | None = 10
    kick_self_full_scale: float = 0.125
    drift_ktc_base_fraction: float = 0.0
    drift_ktc_seed_salt: int = 0xD21F7

    def validate(self) -> None:
        super().validate()
        if self.kick_self_bits is not None and int(self.kick_self_bits) < 2:
            raise ValueError("kick_self_bits must be >=2 or None")
        if not np.isfinite(self.kick_self_full_scale) or self.kick_self_full_scale <= 0.0:
            raise ValueError("kick_self_full_scale must be finite and positive")
        b = float(self.drift_ktc_base_fraction)
        if not np.isfinite(b) or b < 0.0:
            raise ValueError("drift_ktc_base_fraction must be finite and nonnegative")


class TW1AKickDriftTile(TW1ACommonDiffSelfThermalTile):
    """v0.8 fabricated tile with residual K=Q-2I node-local self."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1AKickDriftConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1AKickDriftConfig(prev_ratio_calibration=False) if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1AKickDriftConfig

        drift_seed = (
            int(cfg.seed) * 1_000_109 + int(cfg.drift_ktc_seed_salt)
        ) & 0xFFFFFFFFFFFFFFFF
        self.drift_thermal_rng = np.random.default_rng(drift_seed)

        self._last_kick_self_target = np.zeros(self.nodes, dtype=float)
        self._last_kick_self_programmed = np.zeros(self.nodes, dtype=float)
        self._last_kick_self_actual = np.zeros(self.nodes, dtype=float)
        self._last_kick_self_saturated = np.zeros(self.nodes, dtype=bool)

    def _quantize_kick_self(self, x: Array) -> Array:
        return signed_midtread_quantize(
            np.asarray(x, dtype=float),
            self.config.kick_self_bits,
            self.config.kick_self_full_scale,
        )

    def physical_components(self) -> tuple[Array, Array, Array]:
        # Parent realizes the exact same held reciprocal edge codebooks.  Its
        # wide old self result is discarded; the kick self is re-derived from
        # the logical decomposition before old self quantization.
        _, edge_matrix, edge_amounts = super().physical_components()
        onsite, _ = self._edge_cell_decomposition()
        target = np.asarray(onsite, dtype=float) - 2.0
        fs = float(self.config.kick_self_full_scale)
        saturated = np.abs(target) > fs + 1e-15
        programmed = self._quantize_kick_self(target)
        actual = programmed * self.self_gain

        self._last_kick_self_target = target.copy()
        self._last_kick_self_programmed = np.asarray(programmed, dtype=float).copy()
        self._last_kick_self_actual = np.asarray(actual, dtype=float).copy()
        self._last_kick_self_saturated = saturated.copy()
        return np.asarray(actual, dtype=float), edge_matrix, edge_amounts

    @property
    def kick_self_saturated(self) -> bool:
        self.physical_components()
        return bool(np.any(self._last_kick_self_saturated))

    @property
    def max_abs_kick_self_target(self) -> float:
        self.physical_components()
        return float(np.max(np.abs(self._last_kick_self_target)))

    @property
    def max_abs_kick_self_actual(self) -> float:
        self.physical_components()
        return float(np.max(np.abs(self._last_kick_self_actual)))

    def self_thermal_sigma_fraction(self, self_coeff: Array) -> Array:
        # ``self_coeff`` is now the sampled K residual, not the old d~2 path.
        coeff = np.asarray(self_coeff, dtype=float)
        return float(self.config.self_ktc_base_fraction) * np.sqrt(np.abs(coeff))

    def draw_drift_thermal_noise(self) -> Array:
        sigma = float(self.config.drift_ktc_base_fraction) * float(
            self.config.state_full_scale
        )
        if sigma <= 0.0:
            return np.zeros(self.nodes, dtype=float)
        return self.drift_thermal_rng.normal(0.0, sigma, size=self.nodes)

    def clone(self, *, seed: int | None = None) -> "TW1AKickDriftTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1AKickDriftTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1AKickDriftTile, dst: TW1AKickDriftTile) -> None:
    # Copy only static fabricated disorder.  Dynamic edge/self/drift thermal RNG
    # streams remain tied to each tile's own seed, matching the v0.8 protocol.
    _copy_v08_self_disorder(src, dst)
    dst._rebuild_programmed_Q()


class KickDriftInterpreter(CommonDiffSelfThermalInterpreter):
    """Interpret inherited A/B storage as C/D, and current/previous as Z/P."""

    tile: TW1AKickDriftTile

    def _clip_p(self, x: Array) -> Array:
        # The trained range audit found max |P| ~=0.00324 of the existing state
        # FS, so the first diagnostic deliberately uses the same conservative
        # rail as Z rather than inventing a new range.
        return self._clip(x)

    def _run_forward(self, *, stochastic: bool):
        self._reset_lane_a()
        kick_self, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_c = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)
        edge_sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

        # a_current = Z, a_previous = P.
        for k in range(self.tile.steps):
            z = self.tile.retention * self.a_current
            p = self.tile.retention * self.a_previous
            p_next = p + kick_self * z + edge_matrix @ z + src[k] + inj_c
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                p_next = p_next + _draw_reciprocal_noise(
                    self.tile, edge_sigma_fraction
                )
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                p_next = p_next + self.tile.draw_self_thermal_noise(kick_self)
            p_next = self._clip_p(p_next)

            z_next = z + p_next
            if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
                z_next = z_next + self.tile.draw_drift_thermal_noise()
            self.a_previous, self.a_current = p_next, self._clip(z_next)
            trace[k] = self._sense(self.a_current)

        self.forward_trace = trace
        return kick_self, edge_matrix, edge_amounts, inj_c

    def _clone_and_mirror(self, error_schedule: Array, *, stochastic: bool) -> None:
        # Exact image of CUR<->PREV under P=CUR-PREV:
        #   Zm = Z-P, Pm = -P.
        z = self.a_current.copy()
        p = self.a_previous.copy()
        z_mirror = z - p
        if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
            # The inverse drift pays one sample of the same unity-shear thermal
            # mechanism as an ordinary Z<-Z+P update.
            z_mirror = z_mirror + self.tile.draw_drift_thermal_noise()
        self.a_current = self._clip(z_mirror)
        self.a_previous = self._clip_p(-p)

        # v0.8 D boundary in position/history is current=e_T, previous=0.
        # Therefore kick coordinates are exactly Z=e_T, P=e_T.
        qT = np.asarray(error_schedule[self.tile.steps], dtype=float)
        self.b_current = self._clip(qT.copy())
        self.b_previous = self._clip_p(qT.copy())

    def _run_lockstep_reverse(
        self,
        kick_self: Array,
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
            # Local sensor observes current Z fields, exactly matching the old
            # current-state v0.8 credit identity.
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

            cz = self.tile.retention * self.a_current
            cp = self.tile.retention * self.a_previous
            dz = self.tile.retention * self.b_current
            dp = self.tile.retention * self.b_previous

            cp_next = cp + kick_self * cz + edge_matrix_c @ cz + common_source + inj_c
            dp_next = dp + kick_self * dz + edge_matrix_d @ dz + diff_error + inj_d

            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                cp_next = cp_next + _draw_reciprocal_noise(
                    self.tile, edge_sigma_fraction
                )
                dp_next = dp_next + _draw_reciprocal_noise(
                    self.tile, edge_sigma_fraction
                )
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                cp_next = cp_next + self.tile.draw_self_thermal_noise(kick_self)
                dp_next = dp_next + self.tile.draw_self_thermal_noise(kick_self)

            cp_next = self._clip_p(cp_next)
            dp_next = self._clip_p(dp_next)
            cz_next = cz + cp_next
            dz_next = dz + dp_next
            if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
                cz_next = cz_next + self.tile.draw_drift_thermal_noise()
                dz_next = dz_next + self.tile.draw_drift_thermal_noise()

            self.a_previous, self.a_current = cp_next, self._clip(cz_next)
            self.b_previous, self.b_current = dp_next, self._clip(dz_next)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _make_pair(task, config, sense_gain, *, seed_offset):
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1AKickDriftTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1AKickDriftTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def run_order_contrast_training(
    task,
    config: TW1AKickDriftConfig,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
):
    # The deterministic external input/output dynamics are the same recurrence,
    # so the existing compiler-model PGA recommender remains valid.
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, config, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, config, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = KickDriftInterpreter(exact_t)
    edi = KickDriftInterpreter(exact_d)
    sti = KickDriftInterpreter(shuffle_t)
    sdi = KickDriftInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    ec=[c0]; sc=[sc0]; ete=[et0]; ede=[ed0]; ste=[st0]; sde=[sd0]
    mt=[]; md=[]; cr=[]
    perm=np.random.default_rng(shuffle_seed).permutation(len(exact_t.theta))

    for _ in range(int(iterations)):
        rt=eti.execute(stochastic_forward=True)
        rd=edi.execute(stochastic_forward=True)
        et=float(rt["objective"]); ed=float(rd["objective"])
        gc=contrast_gradient(
            et, ed,
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
            eps=eps,
        )
        mt.append(et); md.append(ed); cr.append(_rms(gc))
        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(exact_t, exact_d)
        if include_shuffle:
            shuffle_t.apply_credits(-gc[perm], step_size=step_size, normalize_rms=normalize_rms)
            _sync_theta(shuffle_t, shuffle_d)

        etv,edv,cv=_eval_pair(eti,edi)
        stv,sdv,scv=_eval_pair(sti,sdi)
        ete.append(etv); ede.append(edv); ec.append(cv)
        ste.append(stv); sde.append(sdv); sc.append(scv)

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
