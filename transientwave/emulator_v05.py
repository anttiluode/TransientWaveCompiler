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

from .emulator import TW1APhysicalTileConfig
from .emulator_v02 import signed_midtread_mu_law_quantize, signed_midtread_quantize
from .emulator_v03 import TW1APhysicalTile as _V03Tile


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
        """Return residual onsite vector and physical rank-one edge amounts.

        ``fixed_Q`` already has all trainable-edge contributions removed by the
        base emulator.  Any remaining legal off-diagonal coefficient is treated
        as a fixed physical edge cell and removed from the residual by the same
        rank-one stamp.  Trainable edge amounts are then inserted from theta.
        """
        residual = self.fixed_Q.copy()
        edge_amounts: dict[tuple[int, int], float] = {}
        train_index = {pair: k for k, pair in enumerate(self._train_pairs)}

        for i, j in self.backend.physical_edges():
            pair = (i, j)
            if pair in train_index:
                # The trainable contribution was removed from fixed_Q in the
                # parent constructor. Any numerical residue is ignored only if
                # it is at roundoff scale; otherwise the manifest is ambiguous.
                v = 0.5 * (float(residual[i, j]) + float(residual[j, i]))
                if abs(v) > 1e-10:
                    raise ValueError(
                        f"trainable edge {pair} retains fixed off-diagonal {v}; "
                        "v0.5 requires one unambiguous edge-cell coefficient"
                    )
                residual[i, j] = residual[j, i] = 0.0
                k = train_index[pair]
                amount = float(self.theta[k] * self._credit_scales[k])
                edge_amounts[pair] = amount
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

        # Strict backend guarantees no nonlocal off-diagonal coefficients.
        off = residual - np.diag(np.diag(residual))
        if float(np.max(np.abs(off))) > 1e-10:
            raise ValueError("v0.5 residual contains nonlocal/non-edge Q coefficients")
        return np.diag(residual).copy(), edge_amounts

    def quantized_Q(self) -> Array:
        """Quantize onsite cells and edge cells, then reconstruct reciprocal Q."""
        onsite, edge_amounts = self._edge_cell_decomposition()
        q = np.zeros((self.nodes, self.nodes), dtype=float)
        np.fill_diagonal(q, self._quantize_onsite_values(onsite))

        pairs = self.backend.physical_edges()
        raw = np.asarray([edge_amounts[p] for p in pairs], dtype=float)
        quant = self._quantize_edge_values(raw)
        for (i, j), amount in zip(pairs, quant):
            if amount != 0.0:
                self._add_rank1(q, i, j, float(amount))
        return q

    def clone(self, *, seed: int | None = None) -> "TW1APhysicalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APhysicalTile(
            self.manifest,
            cfg,
            sense_gain=self.sense_gain,
        )
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
            out._credit_offset_unit = self._credit_offset_unit.copy()
        return out
