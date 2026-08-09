"""TW-1A v0.9R: same physical model, partitioned dynamic-noise RNG streams.

Historical v0.9 experiments derived several stochastic mechanisms from the same
configuration seed.  Static silicon was copied correctly, but edge kT/C and
credit readout noise both consumed the generic ``tile.rng`` stream.  Turning
one source off in a surgical diagnostic could therefore shift samples seen by
another source.

This module changes **only experimental stochastic bookkeeping**:

- edge thermal,
- self thermal,
- drift thermal,
- credit readout

receive independent RNG streams.  Static fabrication, tolerances, equations,
quantizers, switch residuals and learning rules are unchanged.

``reseed_dynamic_streams(seed)`` is intentionally explicit so task generation,
fabrication and dynamic-noise replication can be varied independently.
"""
from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from .circuit_emulator_v07_active_summing import recommend_sense_gain
from .circuit_emulator_v08_common_diff import _eval_pair
from .circuit_emulator_v09_drift_kick import (
    TW1ADriftKickConfig,
    TW1ADriftKickTile,
    copy_circuit_disorder as _copy_drift_kick_disorder,
)
from .circuit_emulator_v09_kick_drift import KickDriftInterpreter
from .emulator import _rms
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


class TW1APartitionedRNGTile(TW1ADriftKickTile):
    """Identical v0.9 drift-kick tile with independent dynamic RNG streams."""

    def __init__(self, manifest, config: TW1ADriftKickConfig, *, sense_gain: float = 1.0):
        super().__init__(manifest, config, sense_gain=sense_gain)
        # Default streams remain deterministic functions of the fabrication
        # config seed, but they no longer consume one another's samples.
        self.reseed_dynamic_streams(int(config.seed) * 1_000_151 + 0x9A17)

    def reseed_dynamic_streams(self, base_seed: int) -> None:
        b = int(base_seed) & 0xFFFFFFFFFFFFFFFF
        # Distinct odd multipliers/salts avoid accidental identical streams.
        self.edge_thermal_rng = np.random.default_rng((b * 1_000_003 + 11) & 0xFFFFFFFFFFFFFFFF)
        self.self_thermal_rng = np.random.default_rng((b * 1_000_033 + 23) & 0xFFFFFFFFFFFFFFFF)
        self.drift_thermal_rng = np.random.default_rng((b * 1_000_037 + 37) & 0xFFFFFFFFFFFFFFFF)
        self.credit_noise_rng = np.random.default_rng((b * 1_000_081 + 53) & 0xFFFFFFFFFFFFFFFF)
        # Keep the inherited generic RNG deterministic too in case a future
        # inherited stochastic path still references it.
        self.rng = np.random.default_rng((b * 1_000_099 + 71) & 0xFFFFFFFFFFFFFFFF)

    def draw_edge_thermal_noise(self, sigma_fraction: Array) -> Array:
        sigma = np.asarray(sigma_fraction, dtype=float) * float(self.config.state_full_scale)
        eta = self.edge_thermal_rng.normal(0.0, sigma)
        out = np.zeros(self.nodes, dtype=float)
        for k, (i, j) in enumerate(self.backend.physical_edges()):
            q = float(eta[k])
            if q != 0.0:
                out[i] += q
                out[j] -= q
        return out

    def clone(self, *, seed: int | None = None) -> "TW1APartitionedRNGTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APartitionedRNGTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out


def copy_circuit_disorder(src: TW1APartitionedRNGTile, dst: TW1APartitionedRNGTile) -> None:
    """Copy only static fabricated disorder; dynamic streams remain independent."""
    _copy_drift_kick_disorder(src, dst)
    dst._rebuild_programmed_Q()


class PartitionedRNGInterpreter(KickDriftInterpreter):
    tile: TW1APartitionedRNGTile

    def _run_forward(self, *, stochastic: bool):
        self._reset_lane_a()
        kself, edge_matrix, edge_amounts = self.tile.physical_components()
        inj = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)
        esig = self.tile.edge_thermal_sigma_fraction(edge_amounts)
        qdrift = self.tile.drift_kick_node_vector("C")

        for k in range(self.tile.steps):
            z = self.tile.retention * self.a_current
            p = self.tile.retention * self.a_previous
            pn = p + kself * z + edge_matrix @ z + src[k] + inj
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                pn = pn + self.tile.draw_edge_thermal_noise(esig)
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                pn = pn + self.tile.draw_self_thermal_noise(kself)
            pn = self._clip_p(pn)
            zn = z + pn + qdrift
            if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
                zn = zn + self.tile.draw_drift_thermal_noise()
            self.a_previous, self.a_current = pn, self._clip(zn)
            trace[k] = self._sense(self.a_current)

        self.forward_trace = trace
        return kself, edge_matrix, edge_amounts, inj

    def _clone_and_mirror(self, error_schedule: Array, *, stochastic: bool) -> None:
        z = self.a_current.copy()
        p = self.a_previous.copy()
        zm = z - p + self.tile.drift_kick_node_vector("C")
        if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
            zm = zm + self.tile.draw_drift_thermal_noise()
        self.a_current = self._clip(zm)
        self.a_previous = self._clip_p(-p)
        qT = np.asarray(error_schedule[self.tile.steps], dtype=float)
        self.b_current = self._clip(qT.copy())
        self.b_previous = self._clip_p(qT.copy())

    def _run_lockstep_reverse(self, kself, edge_matrix, edge_amounts, *, stochastic: bool):
        if self.error_schedule is None:
            raise RuntimeError("reverse requires error schedule")
        src = self._forward_source_schedule()
        qerr = self.error_schedule
        injc = self.tile.edge_injection_node_vector("A", edge_amounts)
        injd = self.tile.edge_injection_node_vector("B", edge_amounts)
        emc, emd = self.tile.lane_edge_matrices(edge_amounts)
        esig = self.tile.edge_thermal_sigma_fraction(edge_amounts)
        qc = self.tile.drift_kick_node_vector("C")
        qd = self.tile.drift_kick_node_vector("D")

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus = np.zeros_like(acc)
        minus = np.zeros_like(acc)
        cret = math.exp(-self.tile.config.credit_accumulator_leakage)

        for j in range(1, self.tile.steps + 1):
            dc = self.tile.edge_difference_vector(self.a_current)
            dd = self.tile.edge_difference_vector(self.b_current)
            pp = self._lcc_square(dc + dd)
            pm = self._lcc_square(dc - dd)
            plus += pp
            minus += pm
            acc = cret * acc + 0.25 * (pp - pm)
            if j == self.tile.steps:
                continue

            idx = self.tile.steps - j
            cz = self.tile.retention * self.a_current
            cp = self.tile.retention * self.a_previous
            dz = self.tile.retention * self.b_current
            dp = self.tile.retention * self.b_previous
            cpn = cp + kself * cz + emc @ cz + src[idx] + injc
            dpn = dp + kself * dz + emd @ dz + qerr[idx] + injd
            if stochastic and self.tile.config.edge_ktc_base_fraction > 0.0:
                cpn = cpn + self.tile.draw_edge_thermal_noise(esig)
                dpn = dpn + self.tile.draw_edge_thermal_noise(esig)
            if stochastic and self.tile.config.self_ktc_base_fraction > 0.0:
                cpn = cpn + self.tile.draw_self_thermal_noise(kself)
                dpn = dpn + self.tile.draw_self_thermal_noise(kself)
            cpn = self._clip_p(cpn)
            dpn = self._clip_p(dpn)
            czn = cz + cpn + qc
            dzn = dz + dpn + qd
            if stochastic and self.tile.config.drift_ktc_base_fraction > 0.0:
                czn = czn + self.tile.draw_drift_thermal_noise()
                dzn = dzn + self.tile.draw_drift_thermal_noise()
            self.a_previous, self.a_current = cpn, self._clip(czn)
            self.b_previous, self.b_current = dpn, self._clip(dzn)

        self.plus_energy = plus
        self.minus_energy = minus
        return acc

    def _finalize_credit(self, raw_overlap: Array) -> Array:
        """Same v0.9 credit model, but credit readout has its own RNG stream."""
        g = self.tile._credit_scales * np.asarray(raw_overlap, dtype=float)
        if len(g):
            scale = _rms(g) + 1e-30
            if self.tile.config.credit_offset_fraction > 0.0:
                g = g + (
                    self.tile.config.credit_offset_fraction
                    * scale
                    * self.tile._credit_offset_unit[: len(g)]
                )
            if self.tile.config.credit_noise_fraction > 0.0:
                sigma = self.tile.config.credit_noise_fraction * scale
                g = g + self.tile.credit_noise_rng.normal(0.0, sigma, size=len(g))
        self.credits = np.asarray(g, dtype=float)
        return self.credits.copy()


def make_pair(task, config, sense_gain, *, seed_offset):
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1APartitionedRNGTile(task["target"], tc, sense_gain=sense_gain)
    d = TW1APartitionedRNGTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def run_order_contrast_training(
    task,
    config: TW1ADriftKickConfig,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    dynamic_seed: int | None = None,
):
    gain = recommend_sense_gain(task, config) if sense_gain is None else float(sense_gain)
    et, ed = make_pair(task, config, gain, seed_offset=0)
    st, sd = make_pair(task, config, gain, seed_offset=100_003)
    copy_circuit_disorder(et, st)
    copy_circuit_disorder(et, sd)
    _sync_theta(et, st)
    _sync_theta(et, sd)

    if dynamic_seed is not None:
        # Role offsets mean target/distractor measurements are independent
        # physical repeats while remaining reproducible for this replicate.
        for role, tile in enumerate((et, ed, st, sd)):
            tile.reseed_dynamic_streams(int(dynamic_seed) * 16 + role)

    eti, edi = PartitionedRNGInterpreter(et), PartitionedRNGInterpreter(ed)
    sti, sdi = PartitionedRNGInterpreter(st), PartitionedRNGInterpreter(sd)
    et0, ed0, c0 = _eval_pair(eti, edi)
    st0, sd0, sc0 = _eval_pair(sti, sdi)
    ec = [c0]
    sc = [sc0]
    ete = [et0]
    ede = [ed0]
    ste = [st0]
    sde = [sd0]
    mt = []
    md = []
    cr = []
    perm = np.random.default_rng(shuffle_seed).permutation(len(et.theta))

    for _ in range(int(iterations)):
        rt = eti.execute(stochastic_forward=True)
        rd = edi.execute(stochastic_forward=True)
        a = float(rt["objective"])
        b = float(rd["objective"])
        gc = contrast_gradient(
            a,
            b,
            np.asarray(rt["credits"], dtype=float),
            np.asarray(rd["credits"], dtype=float),
        )
        mt.append(a)
        md.append(b)
        cr.append(_rms(gc))
        et.apply_credits(-gc, step_size=step_size, normalize_rms=normalize_rms)
        _sync_theta(et, ed)
        if include_shuffle:
            st.apply_credits(-gc[perm], step_size=step_size, normalize_rms=normalize_rms)
            _sync_theta(st, sd)
        a, b, c = _eval_pair(eti, edi)
        x, y, s = _eval_pair(sti, sdi)
        ete.append(a)
        ede.append(b)
        ec.append(c)
        ste.append(x)
        sde.append(y)
        sc.append(s)

    return OrderContrastTrainingResult(
        exact_contrast=ec,
        shuffled_contrast=sc,
        exact_target_energy=ete,
        exact_distractor_energy=ede,
        shuffled_target_energy=ste,
        shuffled_distractor_energy=sde,
        measured_target_energy=mt,
        measured_distractor_energy=md,
        combined_credit_rms=cr,
        final_theta=et.theta.copy(),
        final_theta_shuffled=st.theta.copy(),
    ), gain
