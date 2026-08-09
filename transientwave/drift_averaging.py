"""Repeated physical-credit averaging for TW-1A drift mitigation studies."""
from __future__ import annotations

from typing import Any

import numpy as np

from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig, _rms
from .emulator_v05 import _eval_pair, _make_pair, recommend_sense_gain
from .order_contrast import (
    OrderContrastTrainingResult,
    _copy_static_chip_disorder,
    _sync_theta,
    contrast_gradient,
)


Array = np.ndarray


def run_order_contrast_training_repeated(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    *,
    repeats: int,
    sense_gain: float | None = None,
    iterations: int = 40,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    """Average N independently corrupted physical contrast credits per update.

    Theta is held fixed throughout all repetitions.  Each repetition executes a
    complete AB and BA training microcode cycle, so PLUS/MINUS operator drift,
    state noise and readout noise receive fresh emulator draws.  The resulting
    *combined contrast gradient vectors* are averaged before one host update.
    """
    repeats = int(repeats)
    if repeats < 1:
        raise ValueError("repeats must be >=1")

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
        grads = []
        ets = []
        eds = []
        for _rep in range(repeats):
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
            grads.append(gc)
            ets.append(et)
            eds.append(ed)

        gc_mean = np.mean(np.asarray(grads, dtype=float), axis=0)
        measured_t.append(float(np.mean(ets)))
        measured_d.append(float(np.mean(eds)))
        credit_rms.append(_rms(gc_mean))

        exact_t.apply_credits(-gc_mean, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(exact_t, exact_d)
        if include_shuffle:
            shuffle_t.apply_credits(
                -gc_mean[perm], step_size=step_size, normalize_rms=normalize_rms
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
