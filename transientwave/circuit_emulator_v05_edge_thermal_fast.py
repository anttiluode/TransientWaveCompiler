"""Execution-optimized C0e edge-thermal interpreter.

This module is deliberately semantically identical to
``circuit_emulator_v05_edge_thermal``.  The selected physical edge code and its
thermal RMS are constant during one PARAM_HOLD traversal, so the expensive
site-specific codebook lookup is cached once per traversal instead of repeated
on every wave tick.  RNG calls and noise distributions are unchanged.
"""
from __future__ import annotations

import math

import numpy as np

from .circuit_emulator_v05_edge_thermal import (
    TW1AEdgeThermalConfig,
    EdgeThermalLockstepInterpreter,
    _make_pair,
    _eval_pair,
    recommend_sense_gain,
    copy_circuit_disorder,
)
from .emulator import _rms
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


def _draw_reciprocal_noise(tile, sigma_fraction: Array) -> Array:
    sigma = np.asarray(sigma_fraction, dtype=float) * float(tile.config.state_full_scale)
    eta = tile.rng.normal(0.0, sigma)
    out = np.zeros(tile.nodes, dtype=float)
    for k, (i, j) in enumerate(tile.backend.physical_edges()):
        q = float(eta[k])
        if q != 0.0:
            out[i] += q
            out[j] -= q
    return out


class CachedEdgeThermalLockstepInterpreter(EdgeThermalLockstepInterpreter):
    """Same C0e physics with one codebook lookup per PARAM_HOLD traversal."""

    def _run_forward(self, *, stochastic: bool):
        self._reset_lane_a()
        self_coeff, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)
        sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

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
                nxt = nxt + _draw_reciprocal_noise(self.tile, sigma_fraction)
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
        sigma_fraction = self.tile.edge_thermal_sigma_fraction(edge_amounts)

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

            next_a = (
                self_coeff * ax
                + edge_matrix_a @ ax
                - self.tile.prev_ratio_gain * ap
                + common
                + qa
                + inj_a
            )
            next_b = (
                self_coeff * bx
                + edge_matrix_b @ bx
                - self.tile.prev_ratio_gain * bp
                + common
                + qb
                + inj_b
            )
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                next_a = next_a + _draw_reciprocal_noise(self.tile, sigma_fraction)
                next_b = next_b + _draw_reciprocal_noise(self.tile, sigma_fraction)

            self.a_previous, self.a_current = ax, self._clip(next_a)
            self.b_previous, self.b_current = bx, self._clip(next_b)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def run_order_contrast_training(
    task,
    config: TW1AEdgeThermalConfig,
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

    eti = CachedEdgeThermalLockstepInterpreter(exact_t)
    edi = CachedEdgeThermalLockstepInterpreter(exact_d)
    sti = CachedEdgeThermalLockstepInterpreter(shuffle_t)
    sdi = CachedEdgeThermalLockstepInterpreter(shuffle_d)

    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    exact_contrast = [c0]
    shuffled_contrast = [sc0]
    exact_target_energy = [et0]
    exact_distractor_energy = [ed0]
    shuffled_target_energy = [st0]
    shuffled_distractor_energy = [sd0]
    measured_t = []
    measured_d = []
    credit_rms = []

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
