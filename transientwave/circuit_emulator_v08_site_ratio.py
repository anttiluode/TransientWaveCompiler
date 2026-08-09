"""TW-1A v0.8 with explicit site-common Cunit/Cstate ratio variation.

Independent unit-cap mismatch averages down strongly at code 127.  A real edge
site can also have a common local ratio error between its whole edge bank and
the destination state capacitor.  This module adds that missing fabrication
axis without perturbing the RNG stream of any previously modeled block.

The site-scale draw uses a dedicated deterministic RNG derived from the tile
seed.  The measured physical codebook includes the scale exactly; learning may
therefore compensate static ratio error as long as the site retains sufficient
physical range and monotonicity.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .circuit_emulator_v08_common_diff import (
    CommonDiffLockstepInterpreter,
    TW1ACommonDiffConfig,
    TW1ACommonDiffTile,
    _eval_pair,
)
from .circuit_emulator_v07_active_summing import recommend_sense_gain
from .emulator import _rms
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


@dataclass(frozen=True)
class TW1ACommonDiffSiteConfig(TW1ACommonDiffConfig):
    edge_site_ratio_sigma: float = 0.0
    edge_site_ratio_seed_salt: int = 0x51A7E

    def validate(self) -> None:
        super().validate()
        sigma = float(self.edge_site_ratio_sigma)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise ValueError("edge_site_ratio_sigma must be finite and nonnegative")


class TW1ACommonDiffSiteTile(TW1ACommonDiffTile):
    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACommonDiffSiteConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = (
            TW1ACommonDiffSiteConfig(prev_ratio_calibration=False)
            if config is None
            else config
        )
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACommonDiffSiteConfig

        e = len(self.backend.physical_edges())
        # Dedicated stream: adding this fabrication axis cannot redraw leakage,
        # clone remnants, switch kick, credit offsets, etc.
        site_seed = (int(cfg.seed) * 1_000_003 + int(cfg.edge_site_ratio_seed_salt)) & 0xFFFFFFFFFFFFFFFF
        rng = np.random.default_rng(site_seed)
        self.edge_site_ratio_scale = 1.0 + rng.normal(
            0.0, float(cfg.edge_site_ratio_sigma), size=e
        )

        # In active-summing v0.8 edge_cap_levels are already Cselected/Cstate.
        self.edge_cap_levels = self.edge_cap_levels * self.edge_site_ratio_scale[:, None]
        self.edge_codebook_steps = np.diff(self.edge_cap_levels, axis=1)
        self.edge_codebook_monotonic = np.all(self.edge_codebook_steps > 0.0, axis=1)
        self.edge_site_ratio_valid = bool(np.all(self.edge_site_ratio_scale > 0.0))
        self._rebuild_programmed_Q()

    @property
    def minimum_edge_full_scale(self) -> float:
        return float(np.min(self.edge_cap_levels[:, -1]))

    def edge_selected_cap_ratios(self, edge_amounts: Array) -> Array:
        idx = self.edge_selected_code_indices(edge_amounts)
        return self.edge_cap_levels[np.arange(len(idx)), idx]

    def clone(self, *, seed: int | None = None) -> "TW1ACommonDiffSiteTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ACommonDiffSiteTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(
    src: TW1ACommonDiffSiteTile, dst: TW1ACommonDiffSiteTile
) -> None:
    # Reuse the parent hierarchy's disorder copier through the v0.8 module.
    from .circuit_emulator_v08_common_diff import copy_circuit_disorder as _copy

    _copy(src, dst)
    dst.edge_site_ratio_scale = src.edge_site_ratio_scale.copy()
    dst.edge_cap_levels = src.edge_cap_levels.copy()
    dst.edge_codebook_steps = src.edge_codebook_steps.copy()
    dst.edge_codebook_monotonic = src.edge_codebook_monotonic.copy()
    dst.edge_site_ratio_valid = bool(src.edge_site_ratio_valid)
    dst._rebuild_programmed_Q()


def _make_pair(
    task: dict[str, Any],
    config: TW1ACommonDiffSiteConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACommonDiffSiteTile, TW1ACommonDiffSiteTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    target = TW1ACommonDiffSiteTile(task["target"], tc, sense_gain=sense_gain)
    distractor = TW1ACommonDiffSiteTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(target, distractor)
    _sync_theta(target, distractor)
    return target, distractor


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACommonDiffSiteConfig,
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
