"""TW-1A v0.8 common/difference echo coordinates.

v0.7 stored the two reverse trajectories F+A and F-A.  The fresh v0.7 failure
and controlled pair split showed that terminal clone residual interacts strongly
with the +/- error injection mismatch.  v0.8 removes both devices from the
state evolution by storing the equivalent common/difference coordinates:

    C = (PLUS + MINUS)/2 = F
    D = (PLUS - MINUS)/2 = A.

At the forward terminal boundary C is already present and D starts at exact
zero. The error waveform is injected once into D with one polarity.  The old
PLUS/MINUS edge fields are reconstructed only at the local square sensor as
DeltaC+/-DeltaD, preserving the multiplication-free square-difference identity.

All other v0.7 physical nonidealities remain: active-summing capacitor
codebooks, A/B (now C/D) edge hold mismatch, switch-kick residuals, edge kT/C,
self calibration, state leakage, converter precision, LCC curvature and local
credit noise/offset/leakage.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator_v05_edge_thermal_fast import _draw_reciprocal_noise
from .circuit_emulator_v07_active_summing import (
    TW1AActiveSummingConfig,
    TW1AActiveSummingTile,
    copy_circuit_disorder,
    recommend_sense_gain,
)
from .circuit_emulator_v05_edge_thermal_fast import CachedEdgeThermalLockstepInterpreter
from .emulator import _rms
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


@dataclass(frozen=True)
class TW1ACommonDiffConfig(TW1AActiveSummingConfig):
    common_diff_reverse: bool = True
    single_signed_error_lane: bool = True

    def validate(self) -> None:
        super().validate()
        if not self.common_diff_reverse:
            raise ValueError("v0.8 requires common/difference reverse coordinates")
        if not self.single_signed_error_lane:
            raise ValueError("v0.8 requires one signed error injection into D")
        # terminal-clone and error-sign-asymmetry fields are intentionally not
        # rejected here.  They are retained in the inherited fabrication draw
        # for same-silicon diagnostics, but this interpreter never consumes
        # them.  A later clean contract can delete the obsolete fields entirely.


class TW1ACommonDiffTile(TW1AActiveSummingTile):
    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACommonDiffConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ACommonDiffConfig(
            prev_ratio_calibration=False
        ) if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACommonDiffConfig

    def clone(self, *, seed: int | None = None) -> "TW1ACommonDiffTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ACommonDiffTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


class CommonDiffLockstepInterpreter(CachedEdgeThermalLockstepInterpreter):
    """Interpret inherited A/B storage as common C / difference D storage."""

    tile: TW1ACommonDiffTile

    def _clone_and_mirror(self, error_schedule: Array, *, stochastic: bool) -> None:
        """Mirror C, initialize D=0, inject one terminal error sample into D.

        There is deliberately no use of terminal clone gains and no use of the
        inherited +/- error sign-asymmetry parameter.
        """
        # C contains the forward terminal state. Exact time mirror is the same
        # generation-role swap already used by v0.6 structural history.
        self.a_current, self.a_previous = self.a_previous.copy(), self.a_current.copy()

        # D is an independent state context whose exact mathematical boundary
        # condition is zero. No analog copy of C is required.
        self.b_current.fill(0.0)
        self.b_previous.fill(0.0)

        # One quantized error waveform, one polarity, one destination lane.
        qT = error_schedule[self.tile.steps]
        self.b_current = self._clip(self.b_current + qT)

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
        sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus_sum = np.zeros_like(acc)
        minus_sum = np.zeros_like(acc)
        credit_ret = math.exp(-self.tile.config.credit_accumulator_leakage)

        for j in range(1, self.tile.steps + 1):
            dc = self.tile.edge_difference_vector(self.a_current)
            dd = self.tile.edge_difference_vector(self.b_current)

            # Reconstruct the old PLUS/MINUS edge fields only at the local
            # square sensor. The wave-state capacitors never store C+/-D.
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
                next_c = next_c + _draw_reciprocal_noise(self.tile, sigma_fraction)
                next_d = next_d + _draw_reciprocal_noise(self.tile, sigma_fraction)

            self.a_previous, self.a_current = cx, self._clip(next_c)
            self.b_previous, self.b_current = dx, self._clip(next_d)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _make_pair(
    task: dict[str, Any],
    config: TW1ACommonDiffConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACommonDiffTile, TW1ACommonDiffTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ACommonDiffTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ACommonDiffTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def _eval_pair(
    ti: CommonDiffLockstepInterpreter,
    di: CommonDiffLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACommonDiffConfig,
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

    eti = CommonDiffLockstepInterpreter(exact_t)
    edi = CommonDiffLockstepInterpreter(exact_d)
    sti = CommonDiffLockstepInterpreter(shuffle_t)
    sdi = CommonDiffLockstepInterpreter(shuffle_d)

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
