"""TW-1A physical emulator v0.2: zero-preserving converter semantics.

v0.1 used an endpoint quantizer whose central zero fell between codes. That
turned disabled edges and nominally zero DAC samples into nonzero signals.
This module preserves v0.1 for provenance and changes that hardware semantic:
signed weight, DAC and ADC paths use a mid-tread zero code. The shuffled-credit
control also shares the exact learner's fixed chip disorder so only credit
placement differs.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .emulator import (
    MicrocodeInterpreter,
    TrainingResult,
    TW1APhysicalTile as _V01Tile,
    TW1APhysicalTileConfig,
    _rms,
)


Array = np.ndarray


def signed_midtread_quantize(x: Array, bits: int | None, full_scale: float) -> Array:
    """Symmetric signed quantizer with an exact central zero code.

    Uses integer codes ``-K..K`` where ``K=2^(B-1)-1``. One two's-complement
    endpoint is intentionally unused; exact zero/off semantics are more useful
    for a sparse programmable wave mesh than one extra asymmetric code.
    """
    x = np.asarray(x, dtype=float)
    if bits is None:
        return x.copy()
    k = (1 << (int(bits) - 1)) - 1
    if k <= 0:
        return np.zeros_like(x)
    fs = float(abs(full_scale))
    if fs <= 0:
        return np.zeros_like(x)
    step = fs / float(k)
    code = np.clip(np.rint(x / step), -k, k)
    out = code * step
    return np.where(x == 0.0, 0.0, out)


def signed_midtread_mu_law_quantize(
    x: Array, bits: int | None, full_scale: float, mu: float
) -> Array:
    x = np.asarray(x, dtype=float)
    if bits is None:
        return x.copy()
    fs = float(abs(full_scale))
    if fs <= 0:
        return np.zeros_like(x)
    y = np.clip(x / fs, -1.0, 1.0)
    c = np.sign(y) * np.log1p(mu * np.abs(y)) / np.log1p(mu)
    cq = signed_midtread_quantize(c, bits, 1.0)
    out = np.sign(cq) * np.expm1(np.abs(cq) * np.log1p(mu)) / mu
    out = fs * out
    return np.where(x == 0.0, 0.0, out)


class TW1APhysicalTile(_V01Tile):
    """v0.2 tile: v0.1 physics with zero-preserving quantized I/O and Q."""

    def _quantize_weight_values(self, x: Array, full_scale: float) -> Array:
        if self.config.weight_quantizer == "uniform":
            return signed_midtread_quantize(x, self.config.weight_bits, full_scale)
        return signed_midtread_mu_law_quantize(
            x, self.config.weight_bits, full_scale, self.config.weight_mu
        )

    def quantize_dac_schedule(self, x: Array) -> Array:
        x = np.asarray(x, dtype=float)
        if self.config.dac_bits is None:
            return x.copy()
        fs = float(np.max(np.abs(x))) if x.size else 0.0
        if fs <= 0:
            return np.zeros_like(x)
        return signed_midtread_quantize(x, self.config.dac_bits, fs)

    def quantize_adc(self, x: Array | float) -> Array:
        return signed_midtread_quantize(
            np.asarray(x, dtype=float), self.config.adc_bits, self.config.adc_full_scale
        )

    def clone(self, *, seed: int | None = None) -> "TW1APhysicalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APhysicalTile(self.manifest, cfg)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
        return out


def run_closed_loop_training(
    manifest: dict[str, Any],
    config: TW1APhysicalTileConfig | None = None,
    *,
    iterations: int = 30,
    step_size: float = 0.25,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
) -> TrainingResult:
    """Run the v0.2 four-pass echo learner and norm-matched shuffle control."""
    cfg = TW1APhysicalTileConfig() if config is None else config
    exact_tile = TW1APhysicalTile(manifest, cfg)

    # Same programmed coefficients and same fixed spatial disorder. The shuffle
    # arm never executes a noisy reverse experiment; it only receives the exact
    # arm's measured credits permuted in location, so sharing this seed makes
    # the control differ only in credit placement.
    shuffle_tile = exact_tile.clone(seed=cfg.seed)

    exact_interp = MicrocodeInterpreter(exact_tile)
    shuffle_interp = MicrocodeInterpreter(shuffle_tile)

    exact_loss = [exact_interp.deterministic_forward_loss()]
    shuffled_loss = [shuffle_interp.deterministic_forward_loss()]
    measured: list[float] = []
    credit_rms: list[float] = []

    perm_rng = np.random.default_rng(shuffle_seed)
    perm = perm_rng.permutation(len(exact_tile.theta))

    for _ in range(int(iterations)):
        result = exact_interp.execute(stochastic_forward=True)
        g = np.asarray(result["credits"], dtype=float)
        measured.append(float(result["objective"]))
        credit_rms.append(_rms(g))

        exact_tile.apply_credits(g, step_size=step_size, normalize_rms=normalize_rms)
        if include_shuffle:
            shuffle_tile.apply_credits(g[perm], step_size=step_size, normalize_rms=normalize_rms)

        exact_loss.append(exact_interp.deterministic_forward_loss())
        shuffled_loss.append(shuffle_interp.deterministic_forward_loss())

    return TrainingResult(
        exact_loss=exact_loss,
        shuffled_loss=shuffled_loss,
        measured_objective=measured,
        credit_rms=credit_rms,
        final_theta=exact_tile.theta.copy(),
        final_theta_shuffled=shuffle_tile.theta.copy(),
    )
