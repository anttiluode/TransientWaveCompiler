"""TW-1A emulator v0.5: quantize physical edge cells, not Q entries.

The compiler declares trainable edges with rank-one parameterization

    Q += a_e (e_i-e_j)(e_i-e_j)^T,

where ``a_e = theta_e * compiled_credit_scale``.  v0.1--v0.4 instead
quantized the completed matrix entry-by-entry, allowing the diagonal and
off-diagonal pieces of one physical edge to snap independently.  v0.5 makes
the emulator match the declared hardware abstraction: each reciprocal edge
cell is quantized once, then its exact rank-one contribution is stamped into Q.
Residual onsite coefficients are quantized separately on the diagonal path.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .emulator import MicrocodeInterpreter, TW1APhysicalTileConfig, _rms
from .emulator_v02 import signed_midtread_mu_law_quantize, signed_midtread_quantize
from .emulator_v03 import TW1APhysicalTile as _V03Tile
from .order_contrast import (
    OrderContrastTrainingResult,
    _copy_static_chip_disorder,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


class TW1APhysicalTile(_V03Tile):
    """v0.5 tile with one programmable coefficient per reciprocal edge cell."""

    def _quantize_edge_values(self, x: Array) -> Array:
        fs = max(abs(self.backend.q_edge_min), abs(self.backend.q_edge_max))
        if self.config.weight_quantizer == "uniform":
            return signed_midtread_quantize(x, self.config.weight_bits, fs)
        return signed_midtread_mu_law_quantize(
            x, self.config.weight_bits, fs, self.config.weight_mu
        )

    def _quantize_onsite_values(self, x: Array) -> Array:
        fs = max(abs(self.backend.q_diag_min), abs(self.backend.q_diag_max))
        if self.config.weight_quantizer == "uniform":
            return signed_midtread_quantize(x, self.config.weight_bits, fs)
        return signed_midtread_mu_law_quantize(
            x, self.config.weight_bits, fs, self.config.weight_mu
        )

    def _edge_cell_decomposition(self) -> tuple[Array, dict[tuple[int, int], float]]:
        """Return residual onsite vector and physical rank-one edge amounts."""
        residual = self.fixed_Q.copy()
        edge_amounts: dict[tuple[int, int], float] = {}
        train_index = {pair: k for k, pair in enumerate(self._train_pairs)}

        for i, j in self.backend.physical_edges():
            pair = (i, j)
            if pair in train_index:
                # The trainable contribution was removed from fixed_Q in the
                # parent constructor. Any remaining off-diagonal must be zero.
                v = 0.5 * (float(residual[i, j]) + float(residual[j, i]))
                if abs(v) > 1e-10:
                    raise ValueError(
                        f"trainable edge {pair} retains fixed off-diagonal {v}; "
                        "v0.5 requires one unambiguous edge-cell coefficient"
                    )
                residual[i, j] = residual[j, i] = 0.0
                k = train_index[pair]
                edge_amounts[pair] = float(self.theta[k] * self._credit_scales[k])
            else:
                v = 0.5 * (float(residual[i, j]) + float(residual[j, i]))
                if abs(v) <= 1e-15:
                    residual[i, j] = residual[j, i] = 0.0
                    edge_amounts[pair] = 0.0
                    continue
                # rank-one amount a has off-diagonal -a.
                amount = -v
                edge_amounts[pair] = amount
                self._add_rank1(residual, i, j, -amount)
                residual[i, j] = residual[j, i] = 0.0

        off = residual - np.diag(np.diag(residual))
        if float(np.max(np.abs(off))) > 1e-10:
            raise ValueError("v0.5 residual contains nonlocal/non-edge Q coefficients")
        return np.diag(residual).copy(), edge_amounts

    def quantized_edge_amounts(self) -> dict[tuple[int, int], float]:
        """Expose the actually programmed edge-cell coefficients for audits."""
        _, edge_amounts = self._edge_cell_decomposition()
        pairs = self.backend.physical_edges()
        raw = np.asarray([edge_amounts[p] for p in pairs], dtype=float)
        quant = self._quantize_edge_values(raw)
        return {p: float(a) for p, a in zip(pairs, quant)}

    def quantized_Q(self) -> Array:
        """Quantize onsite cells and edge cells, then reconstruct reciprocal Q."""
        onsite, _ = self._edge_cell_decomposition()
        q = np.zeros((self.nodes, self.nodes), dtype=float)
        np.fill_diagonal(q, self._quantize_onsite_values(onsite))

        for (i, j), amount in self.quantized_edge_amounts().items():
            if amount != 0.0:
                self._add_rank1(q, i, j, float(amount))
        return q

    def clone(self, *, seed: int | None = None) -> "TW1APhysicalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APhysicalTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
            out._credit_offset_unit = self._credit_offset_unit.copy()
        return out


def _nominal_prediction_config(config: TW1APhysicalTileConfig) -> TW1APhysicalTileConfig:
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.0,
        differential_pass_drift=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1APhysicalTileConfig) -> float:
    tile = TW1APhysicalTile(manifest, _nominal_prediction_config(config), sense_gain=1.0)
    interp = MicrocodeInterpreter(tile)
    tile.reset_state()
    interp._run_forward(tile.steps, stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
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
    if peak <= 0:
        return float(max_gain)
    target = float(config.adc_full_scale) * float(target_fraction)
    gain = 1
    while gain * 2 <= max_gain and peak * (gain * 2) <= target:
        gain *= 2
    return float(gain)


def _make_pair(
    task: dict[str, Any],
    config: TW1APhysicalTileConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1APhysicalTile, TW1APhysicalTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1APhysicalTile(task["target"], tc, sense_gain=sense_gain)
    d = TW1APhysicalTile(task["distractor"], dc, sense_gain=sense_gain)
    _copy_static_chip_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(
    ti: MicrocodeInterpreter, di: MicrocodeInterpreter
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
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
    """Run contrast learning with edge-cell-quantized v0.5 hardware."""
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
