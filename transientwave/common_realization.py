"""Common-realization PLUS/MINUS drift positive-control estimator.

This module changes only the *correlation* of reverse-operator drift: one full
reciprocal drift realization is sampled for a physical gradient measurement and
reused for both REVERSE_PLUS and REVERSE_MINUS.  The next gradient measurement
samples a new realization.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig, _rms
from .emulator_v05 import TW1APhysicalTile as _V05Tile, recommend_sense_gain
from .order_contrast import (
    OrderContrastTrainingResult,
    _copy_static_chip_disorder,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


class CommonPairDriftTile(_V05Tile):
    """v0.5 tile whose two reverse phase states share one drifted Q."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._common_reverse_q: np.ndarray | None = None
        self._common_reverse_uses = 0

    def effective_Q(self, *, reverse: bool = False) -> np.ndarray:
        if not reverse or self.config.differential_pass_drift == 0.0:
            return super().effective_Q(reverse=reverse)

        if self._common_reverse_q is None or self._common_reverse_uses >= 2:
            self._common_reverse_q = super().effective_Q(reverse=True)
            self._common_reverse_uses = 0
        self._common_reverse_uses += 1
        return self._common_reverse_q.copy()

    def clone(self, *, seed: int | None = None) -> "CommonPairDriftTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = CommonPairDriftTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
            out._credit_offset_unit = self._credit_offset_unit.copy()
        return out


def _make_pair(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[CommonPairDriftTile, CommonPairDriftTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = CommonPairDriftTile(task["target"], tc, sense_gain=sense_gain)
    d = CommonPairDriftTile(task["distractor"], dc, sense_gain=sense_gain)
    _copy_static_chip_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(ti: MicrocodeInterpreter, di: MicrocodeInterpreter):
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training_common_drift(
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
    """Run physical contrast learning with common PLUS/MINUS reverse drift."""
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)
    exact_t, exact_d = _make_pair(task, config, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, config, gain, seed_offset=100_003)
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
