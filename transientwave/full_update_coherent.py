"""Full AB+BA gradient-cycle coherent drift positive control.

One reciprocal drifted Q realization is frozen across every forward and reverse
traversal needed to evaluate one temporal-order contrast gradient.  The drifted
operator is discarded after the optimizer update and redrawn next iteration.
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


class FullUpdateCoherentTile(_V05Tile):
    """Tile that can temporarily freeze one Q for forward and reverse calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coherent_q: np.ndarray | None = None

    def sample_drifted_Q(self) -> np.ndarray:
        """Draw one reciprocal drifted Q with the standard v0.5 drift model."""
        return super().effective_Q(reverse=True)

    def set_coherent_Q(self, q: np.ndarray) -> None:
        q = np.asarray(q, dtype=float)
        if q.shape != (self.nodes, self.nodes):
            raise ValueError("coherent Q has wrong shape")
        self._coherent_q = q.copy()

    def clear_coherent_Q(self) -> None:
        self._coherent_q = None

    def effective_Q(self, *, reverse: bool = False) -> np.ndarray:
        if self._coherent_q is not None:
            return self._coherent_q.copy()
        return super().effective_Q(reverse=reverse)

    def clone(self, *, seed: int | None = None) -> "FullUpdateCoherentTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = FullUpdateCoherentTile(self.manifest, cfg, sense_gain=self.sense_gain)
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
) -> tuple[FullUpdateCoherentTile, FullUpdateCoherentTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = FullUpdateCoherentTile(task["target"], tc, sense_gain=sense_gain)
    d = FullUpdateCoherentTile(task["distractor"], dc, sense_gain=sense_gain)
    _copy_static_chip_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(ti: MicrocodeInterpreter, di: MicrocodeInterpreter):
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training_full_coherent(
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
    """Run contrast learning with one drifted Q frozen over AB+BA measurement."""
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
        # One physical Q realization for the complete contrast-gradient cycle.
        q_cycle = exact_t.sample_drifted_Q()
        exact_t.set_coherent_Q(q_cycle)
        exact_d.set_coherent_Q(q_cycle)
        try:
            rt = eti.execute(stochastic_forward=True)
            rd = edi.execute(stochastic_forward=True)
        finally:
            exact_t.clear_coherent_Q()
            exact_d.clear_coherent_Q()

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

        # Evaluation remains on the programmed nominal quantized Q.
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
