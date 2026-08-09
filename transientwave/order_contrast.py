"""Closed-loop temporal-order contrast learning on matched TW-1A programs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig, _rms
from .emulator_v02 import TW1APhysicalTile


Array = np.ndarray


def contrast_from_energies(target: float, distractor: float, eps: float = 1e-30) -> float:
    s = float(target) + float(distractor) + float(eps)
    return float((float(target) - float(distractor)) / s)


def contrast_gradient(
    target_energy: float,
    distractor_energy: float,
    target_credit: Array,
    distractor_credit: Array,
    eps: float = 1e-30,
) -> Array:
    """Exact chain rule for C=(Et-Ed)/(Et+Ed)."""
    et = float(target_energy)
    ed = float(distractor_energy)
    s = et + ed + float(eps)
    gt = np.asarray(target_credit, dtype=float)
    gd = np.asarray(distractor_credit, dtype=float)
    if gt.shape != gd.shape:
        raise ValueError("target/distractor credit shapes differ")
    return (2.0 * ed / (s * s)) * gt - (2.0 * et / (s * s)) * gd


def _copy_static_chip_disorder(src: TW1APhysicalTile, dst: TW1APhysicalTile) -> None:
    """Share physical constants while leaving traversal noise RNG independent."""
    dst.leakage_rates = src.leakage_rates.copy()
    dst.retention = src.retention.copy()
    dst._credit_offset_unit = src._credit_offset_unit.copy()


def _sync_theta(src: TW1APhysicalTile, dst: TW1APhysicalTile) -> None:
    dst.theta = src.theta.copy()
    dst._rebuild_programmed_Q()


def _make_pair(
    task: dict[str, Any], config: TW1APhysicalTileConfig, *, seed_offset: int = 0
) -> tuple[TW1APhysicalTile, TW1APhysicalTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1APhysicalTile(task["target"], tc)
    d = TW1APhysicalTile(task["distractor"], dc)
    _copy_static_chip_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _evaluate_pair(
    t_interp: MicrocodeInterpreter, d_interp: MicrocodeInterpreter
) -> tuple[float, float, float]:
    et = float(t_interp.deterministic_forward_loss())
    ed = float(d_interp.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


@dataclass
class OrderContrastTrainingResult:
    exact_contrast: list[float]
    shuffled_contrast: list[float]
    exact_target_energy: list[float]
    exact_distractor_energy: list[float]
    shuffled_target_energy: list[float]
    shuffled_distractor_energy: list[float]
    measured_target_energy: list[float]
    measured_distractor_energy: list[float]
    combined_credit_rms: list[float]
    final_theta: Array
    final_theta_shuffled: Array

    @property
    def exact_improvement(self) -> float:
        return float(self.exact_contrast[-1] - self.exact_contrast[0])

    @property
    def shuffled_improvement(self) -> float:
        return float(self.shuffled_contrast[-1] - self.shuffled_contrast[0])

    @property
    def placement_gap(self) -> float:
        return float(self.exact_improvement - self.shuffled_improvement)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig | None = None,
    *,
    iterations: int = 40,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> OrderContrastTrainingResult:
    """Maximize AB-vs-BA normalized output-energy contrast.

    Each iteration performs the existing four-pass physical energy-gradient
    measurement once for AB and once for BA.  The host combines those edge
    credits by the exact scalar chain rule and applies gradient ascent.
    """
    cfg = TW1APhysicalTileConfig() if config is None else config
    exact_t, exact_d = _make_pair(task, cfg, seed_offset=0)

    # Shuffled control is a deterministic copy of the same physical chip. It
    # never measures another reverse gradient; it receives the exact combined
    # credit values with edge placement permuted.
    shuffle_t, shuffle_d = _make_pair(task, cfg, seed_offset=100_003)
    _copy_static_chip_disorder(exact_t, shuffle_t)
    _copy_static_chip_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = MicrocodeInterpreter(exact_t)
    edi = MicrocodeInterpreter(exact_d)
    sti = MicrocodeInterpreter(shuffle_t)
    sdi = MicrocodeInterpreter(shuffle_d)

    et0, ed0, c0 = _evaluate_pair(eti, edi)
    st0, sd0, sc0 = _evaluate_pair(sti, sdi)

    exact_contrast = [c0]
    shuffled_contrast = [sc0]
    exact_target_energy = [et0]
    exact_distractor_energy = [ed0]
    shuffled_target_energy = [st0]
    shuffled_distractor_energy = [sd0]
    measured_target: list[float] = []
    measured_distractor: list[float] = []
    credit_rms: list[float] = []

    perm_rng = np.random.default_rng(shuffle_seed)
    perm = perm_rng.permutation(len(exact_t.theta))

    for _ in range(int(iterations)):
        rt = eti.execute(stochastic_forward=True)
        rd = edi.execute(stochastic_forward=True)
        et = float(rt["objective"])
        ed = float(rd["objective"])
        gt = np.asarray(rt["credits"], dtype=float)
        gd = np.asarray(rd["credits"], dtype=float)
        gc = contrast_gradient(et, ed, gt, gd, eps=eps)

        measured_target.append(et)
        measured_distractor.append(ed)
        credit_rms.append(_rms(gc))

        # apply_credits implements descent, so negate dC/dtheta to maximize C.
        exact_t.apply_credits(-gc, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(exact_t, exact_d)

        if include_shuffle:
            shuffle_t.apply_credits(
                -gc[perm], step_size=step_size, normalize_rms=normalize_rms
            )
            _sync_theta(shuffle_t, shuffle_d)

        etv, edv, cv = _evaluate_pair(eti, edi)
        stv, sdv, scv = _evaluate_pair(sti, sdi)
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
        measured_target_energy=measured_target,
        measured_distractor_energy=measured_distractor,
        combined_credit_rms=credit_rms,
        final_theta=exact_t.theta.copy(),
        final_theta_shuffled=shuffle_t.theta.copy(),
    )
