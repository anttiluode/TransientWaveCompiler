"""TW-1A v0.5: phase-symmetric edge sampling on top of calibration-first v0.4.

The v0.4 failed-corner diagnosis isolated a single dominant residual: the B
reverse subphase was modeled as consuming a less-settled shared edge MDAC than
A.  Removing only that B-specific settling loss rescued all ten spent bodies.

v0.5 changes the circuit abstraction rather than tightening that tolerance:

* the calibrated reciprocal edge transfer is pre-settled before either reverse
  lane evaluates;
* matched A/B local holds capture that settled coefficient;
* raw finite settling is common to forward/A/B and is therefore included in
  the foreground edge transfer calibration;
* the only reverse-specific edge error is the residual mismatch between the two
  local holds;
* there is no A->B state-dependent edge memory path because neither lane is
  sampled from the other lane's just-used edge node.

This is a phase-symmetry change: A is no longer the privileged first consumer
and B is no longer the less-settled second consumer.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator import LockstepCircuitInterpreter as _V02Interpreter
from .circuit_emulator_v04 import (
    TW1ACircuitV04Config,
    TW1ACircuitTile as _V04Tile,
    _positive_measurement,
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
class TW1ACircuitV05Config(TW1ACircuitV04Config):
    """Phase-symmetric v0.5 error model.

    ``edge_common_settling_loss`` is raw finite-settling loss of the shared edge
    transfer before the matched A/B holds.  It is part of the measured edge map
    and can therefore be large as long as headroom remains.

    ``edge_lane_match_std`` is the fractional RMS mismatch between the two
    post-settling local holds.  This, not the raw common settling loss, is the
    residual that can corrupt F+A versus F-A lockstep symmetry.
    """

    # Legacy A-first/B-second errors are structurally absent in v0.5.
    edge_settling_error: float = 0.0
    ab_edge_memory: float = 0.0

    phase_symmetric_edge_sampling: bool = True
    edge_common_settling_loss: float = 0.0
    edge_lane_match_std: float = 0.0

    def validate(self) -> None:
        super().validate()
        if self.edge_settling_error != 0.0:
            raise ValueError(
                "v0.5 phase-symmetric sampling requires legacy B-only "
                "edge_settling_error=0"
            )
        if self.ab_edge_memory != 0.0:
            raise ValueError(
                "v0.5 phase-symmetric sampling has no A->B edge memory; "
                "ab_edge_memory must be zero"
            )
        loss = float(self.edge_common_settling_loss)
        if not np.isfinite(loss) or loss < 0.0 or loss >= 1.0:
            raise ValueError("edge_common_settling_loss must lie in [0,1)")
        match = float(self.edge_lane_match_std)
        if not np.isfinite(match) or match < 0.0:
            raise ValueError("edge_lane_match_std must be finite and nonnegative")


class TW1ACircuitTile(_V04Tile):
    """v0.5 tile with calibrated common settling and matched A/B edge holds."""

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACircuitV05Config | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ACircuitV05Config() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACircuitV05Config

        e = len(self.backend.physical_edges())

        # The raw shared transfer now includes the finite-settling factor.  The
        # edge calibration measures the combined transfer rather than device
        # gain and settling separately.
        settle_gain = 1.0 - float(self.config.edge_common_settling_loss)
        self.edge_common_settling_gain = np.full(e, settle_gain, dtype=float)
        self.edge_effective_gain_raw = self.edge_gain * self.edge_common_settling_gain
        self.edge_effective_gain_measured = _positive_measurement(
            self.edge_effective_gain_raw,
            self.config.edge_calibration_error_std,
            self.rng,
        )

        # Two local post-settling coefficient holds.  Split the residual
        # mismatch symmetrically so their average is exactly the calibrated
        # common transfer.
        if self.config.edge_lane_match_std == 0.0:
            delta = np.zeros(e, dtype=float)
        else:
            delta = self.rng.normal(0.0, self.config.edge_lane_match_std, size=e)
        self.edge_lane_mismatch = delta
        self.edge_lane_gain_a = 1.0 + 0.5 * delta
        self.edge_lane_gain_b = 1.0 - 0.5 * delta

    def physical_components(self) -> tuple[Array, Array, Array]:
        onsite, raw_edges = self._edge_cell_decomposition()

        # Self path remains calibration-first from v0.4/v0.3.
        qself = self._quantize_onsite_values(onsite) * self.self_gain

        pairs = self.backend.physical_edges()
        desired = np.asarray([raw_edges[p] for p in pairs], dtype=float)
        if self.config.edge_calibration:
            command = desired / self.edge_effective_gain_measured
        else:
            command = desired
        qedge = self._quantize_edge_values(command) * self.edge_effective_gain_raw

        edge_matrix = np.zeros((self.nodes, self.nodes), dtype=float)
        for (i, j), amount in zip(pairs, qedge):
            if amount != 0.0:
                self._add_rank1(edge_matrix, i, j, float(amount))
        return np.asarray(qself, dtype=float), edge_matrix, np.asarray(qedge, dtype=float)

    def lane_edge_matrices(self, edge_amounts: Array) -> tuple[Array, Array]:
        """Reconstruct the two matched post-settling reverse edge operators."""
        qa = np.zeros((self.nodes, self.nodes), dtype=float)
        qb = np.zeros((self.nodes, self.nodes), dtype=float)
        for k, ((i, j), amount) in enumerate(
            zip(self.backend.physical_edges(), np.asarray(edge_amounts, dtype=float))
        ):
            if amount == 0.0:
                continue
            self._add_rank1(qa, i, j, float(amount * self.edge_lane_gain_a[k]))
            self._add_rank1(qb, i, j, float(amount * self.edge_lane_gain_b[k]))
        return qa, qb

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
    """Make two manifests observe one calibrated phase-symmetric tile."""
    dst.leakage_rates = src.leakage_rates.copy()
    dst.retention = src.retention.copy()
    dst._credit_offset_unit = src._credit_offset_unit.copy()

    dst.edge_gain = src.edge_gain.copy()
    dst.edge_gain_measured = src.edge_gain_measured.copy()
    dst.edge_common_settling_gain = src.edge_common_settling_gain.copy()
    dst.edge_effective_gain_raw = src.edge_effective_gain_raw.copy()
    dst.edge_effective_gain_measured = src.edge_effective_gain_measured.copy()
    dst.edge_lane_mismatch = src.edge_lane_mismatch.copy()
    dst.edge_lane_gain_a = src.edge_lane_gain_a.copy()
    dst.edge_lane_gain_b = src.edge_lane_gain_b.copy()

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


class PhaseSymmetricLockstepInterpreter(_V02Interpreter):
    """Lockstep reverse interpreter with matched pre-settled A/B edge holds."""

    tile: TW1ACircuitTile

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

            # Both operators were sampled before either lane was evaluated.
            # There is no B-specific settling loss and no A->B edge residue.
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
            if stochastic:
                next_a = next_a + self._state_noise()
                next_b = next_b + self._state_noise()
            self.a_previous, self.a_current = ax, self._clip(next_a)
            self.b_previous, self.b_current = bx, self._clip(next_b)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def _nominal_gain_config(config: TW1ACircuitV05Config) -> TW1ACircuitV05Config:
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


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ACircuitV05Config) -> float:
    tile = TW1ACircuitTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = PhaseSymmetricLockstepInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ACircuitV05Config,
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
    config: TW1ACircuitV05Config,
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
    ti: PhaseSymmetricLockstepInterpreter,
    di: PhaseSymmetricLockstepInterpreter,
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACircuitV05Config | None = None,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    cfg = TW1ACircuitV05Config() if config is None else config
    gain = recommend_sense_gain(task, cfg) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
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
