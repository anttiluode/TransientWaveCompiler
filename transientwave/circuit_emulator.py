"""Circuit-native emulator for the TW-1A v0.2 lockstep architecture.

This model intentionally removes the old abstract assumptions
``mirror_error`` and independent PLUS/MINUS ``differential_pass_drift``.
Instead it models the physical errors created by the proposed switched-capacitor
architecture:

* one held reciprocal edge/self realization across a complete gradient;
* exact current/previous pointer-swap time mirror;
* one terminal copy into a second reverse context;
* lane A = F+A and lane B = F-A evolved in lockstep;
* the same edge MDAC used by A then B inside one wave tick;
* one signed local square/integrate credit accumulator.

The circuit recurrence is still

    z[n+1] = Q z[n] - z[n-1] + u[n]

when all circuit-native errors are zero.  Nonidealities are introduced at the
physical primitive that would create them rather than as arbitrary matrix drift.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .emulator import TW1APhysicalTileConfig, _rms
from .emulator_v02 import signed_midtread_quantize
from .emulator_v05 import TW1APhysicalTile as _V05Tile
from .order_contrast import (
    OrderContrastTrainingResult,
    _sync_theta,
    contrast_from_energies,
    contrast_gradient,
)


Array = np.ndarray


@dataclass(frozen=True)
class TW1ACircuitEmulatorConfig(TW1APhysicalTileConfig):
    """Mixed-signal errors attached to concrete TW-1A v0.2 primitives.

    The inherited ``mirror_error`` and ``differential_pass_drift`` fields are
    fixed to zero.  A nonzero value is rejected because those abstractions no
    longer correspond to the lockstep circuit.
    """

    # Override obsolete v0.1 defaults.
    mirror_error: float = 0.0
    differential_pass_drift: float = 0.0

    # Circuit precision that is distinct from the inherited edge/DAC/ADC paths.
    self_bits: int | None = 12
    self_full_scale: float = 3.0
    error_dac_bits: int | None = 10

    # Static physical coefficient realization, common to both reverse lanes.
    edge_gain_cv: float = 0.0
    self_gain_cv: float = 0.0

    # One-time terminal A -> B state copy.
    terminal_clone_gain_std: float = 0.0
    terminal_clone_noise_std: float = 0.0

    # Adjacent A/B subphase behavior of the shared edge MDAC.
    edge_settling_error: float = 0.0
    ab_edge_memory: float = 0.0
    edge_charge_injection_std: float = 0.0

    # Shared recurrence/history primitive.
    prev_ratio_error_std: float = 0.0

    # One error DAC magnitude sample is routed with opposite sign to A and B.
    error_dac_sign_asymmetry: float = 0.0

    # Shared local credit detector / storage.
    lcc_curvature: float = 0.0
    credit_accumulator_leakage: float = 0.0

    def validate(self) -> None:
        super().validate()
        if self.mirror_error != 0.0:
            raise ValueError("circuit emulator uses pointer-swap mirror; mirror_error must be zero")
        if self.differential_pass_drift != 0.0:
            raise ValueError(
                "circuit emulator uses one held operator and lockstep reverse lanes; "
                "differential_pass_drift must be zero"
            )
        for name, bits in (("self_bits", self.self_bits), ("error_dac_bits", self.error_dac_bits)):
            if bits is not None and int(bits) < 2:
                raise ValueError(f"{name} must be >=2 or None")
        if not math.isfinite(self.self_full_scale) or self.self_full_scale <= 0:
            raise ValueError("self_full_scale must be finite and positive")
        nonnegative = (
            "edge_gain_cv",
            "self_gain_cv",
            "terminal_clone_gain_std",
            "terminal_clone_noise_std",
            "edge_settling_error",
            "edge_charge_injection_std",
            "prev_ratio_error_std",
            "error_dac_sign_asymmetry",
            "lcc_curvature",
            "credit_accumulator_leakage",
        )
        for name in nonnegative:
            v = float(getattr(self, name))
            if not math.isfinite(v) or v < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not math.isfinite(self.ab_edge_memory) or abs(self.ab_edge_memory) > 1.0:
            raise ValueError("ab_edge_memory must be finite and lie in [-1,1]")
        if self.edge_settling_error >= 1.0:
            raise ValueError("edge_settling_error must be <1")
        if self.error_dac_sign_asymmetry >= 2.0:
            raise ValueError("error_dac_sign_asymmetry must be <2")


class TW1ACircuitTile(_V05Tile):
    """TW-1A v0.2 tile with circuit-native static disorder.

    Dynamic A/B reverse state is held by :class:`LockstepCircuitInterpreter`.
    The tile owns the programmed coefficients, converter behavior and fixed chip
    mismatch fields.
    """

    def __init__(
        self,
        manifest: dict[str, Any],
        config: TW1ACircuitEmulatorConfig | None = None,
        *,
        sense_gain: float = 1.0,
    ):
        cfg = TW1ACircuitEmulatorConfig() if config is None else config
        cfg.validate()
        super().__init__(manifest, cfg, sense_gain=sense_gain)
        self.config: TW1ACircuitEmulatorConfig

        pairs = self.backend.physical_edges()
        e = len(pairs)
        n = self.nodes

        def positive_gain(cv: float, size: int) -> Array:
            if cv == 0.0:
                return np.ones(size, dtype=float)
            return np.maximum(1.0 + cv * self.rng.normal(size=size), 1e-9)

        self.edge_gain = positive_gain(self.config.edge_gain_cv, e)
        self.self_gain = positive_gain(self.config.self_gain_cv, n)
        self.prev_ratio_gain = positive_gain(self.config.prev_ratio_error_std, n)

        # Copy mismatch belongs to the two state banks independently.
        self.clone_gain_current = positive_gain(self.config.terminal_clone_gain_std, n)
        self.clone_gain_previous = positive_gain(self.config.terminal_clone_gain_std, n)

        # Residual lane-select charge injection.  A/B offsets are fixed for the
        # chip but distinct because the lane-select switches are distinct.
        sigma_q = self.config.edge_charge_injection_std * self.config.state_full_scale
        if sigma_q == 0.0:
            self.edge_injection_a = np.zeros(e, dtype=float)
            self.edge_injection_b = np.zeros(e, dtype=float)
        else:
            self.edge_injection_a = self.rng.normal(0.0, sigma_q, size=e)
            self.edge_injection_b = self.rng.normal(0.0, sigma_q, size=e)

    def _quantize_onsite_values(self, x: Array) -> Array:
        return signed_midtread_quantize(
            np.asarray(x, dtype=float),
            self.config.self_bits,
            self.config.self_full_scale,
        )

    def clone(self, *, seed: int | None = None) -> "TW1ACircuitTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1ACircuitTile(self.manifest, cfg, sense_gain=self.sense_gain)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        if seed is None or seed == self.config.seed:
            copy_circuit_disorder(self, out)
        return out

    def physical_components(self) -> tuple[Array, Array, Array]:
        """Return held self vector, held edge matrix and held edge amounts.

        The result is one physical realization used by forward and both reverse
        contexts until the host changes edge codes.  Static post-programming
        mismatch is therefore common-mode across the gradient.
        """
        onsite, raw_edges = self._edge_cell_decomposition()
        qself = self._quantize_onsite_values(onsite) * self.self_gain

        pairs = self.backend.physical_edges()
        raw = np.asarray([raw_edges[p] for p in pairs], dtype=float)
        qedge = self._quantize_edge_values(raw) * self.edge_gain

        edge_matrix = np.zeros((self.nodes, self.nodes), dtype=float)
        for (i, j), a in zip(pairs, qedge):
            if a != 0.0:
                self._add_rank1(edge_matrix, i, j, float(a))
        return np.asarray(qself, dtype=float), edge_matrix, np.asarray(qedge, dtype=float)

    def quantized_Q(self) -> Array:
        qself, qedge, _ = self.physical_components()
        out = qedge.copy()
        idx = np.diag_indices(self.nodes)
        out[idx] += qself
        return out

    def quantize_error_schedule(self, x: Array) -> Array:
        a = np.asarray(x, dtype=float)
        if self.config.error_dac_bits is None:
            return a.copy()
        fs = float(np.max(np.abs(a))) if a.size else 0.0
        if fs <= 0.0:
            return np.zeros_like(a)
        return signed_midtread_quantize(a, self.config.error_dac_bits, fs)

    def edge_difference_vector(self, state: Array) -> Array:
        x = np.asarray(state, dtype=float)
        pairs = self._train_pairs
        if not pairs:
            return np.zeros(0, dtype=float)
        return np.asarray([x[j] - x[i] for i, j in pairs], dtype=float)

    def edge_injection_node_vector(self, lane: str, active_amounts: Array) -> Array:
        """Map fixed edge charge-injection packets to equal/opposite node charge."""
        packets = self.edge_injection_a if lane == "A" else self.edge_injection_b
        out = np.zeros(self.nodes, dtype=float)
        for k, ((i, j), a) in enumerate(zip(self.backend.physical_edges(), active_amounts)):
            if a == 0.0:
                continue
            q = float(packets[k])
            out[i] += q
            out[j] -= q
        return out


def copy_circuit_disorder(src: TW1ACircuitTile, dst: TW1ACircuitTile) -> None:
    """Make two manifests observe the same physical tile realization."""
    dst.leakage_rates = src.leakage_rates.copy()
    dst.retention = src.retention.copy()
    dst._credit_offset_unit = src._credit_offset_unit.copy()
    dst.edge_gain = src.edge_gain.copy()
    dst.self_gain = src.self_gain.copy()
    dst.prev_ratio_gain = src.prev_ratio_gain.copy()
    dst.clone_gain_current = src.clone_gain_current.copy()
    dst.clone_gain_previous = src.clone_gain_previous.copy()
    dst.edge_injection_a = src.edge_injection_a.copy()
    dst.edge_injection_b = src.edge_injection_b.copy()


class LockstepCircuitInterpreter:
    """Execute one forward plus one simultaneous +/- reverse pair.

    No N x T internal trajectory is retained.  Only the externally sensed
    output trace is stored to construct the objective-specific error waveform.
    """

    def __init__(self, tile: TW1ACircuitTile):
        self.tile = tile
        self.manifest = tile.manifest
        self.forward_trace: Array | None = None
        self.forward_source: Array | None = None
        self.error_schedule: Array | None = None
        self.objective_value: float | None = None
        self.credits: Array | None = None
        self.plus_energy: Array | None = None
        self.minus_energy: Array | None = None

        ports = {p["name"]: p for p in self.manifest["ports"]}
        self.output_name = str(self.manifest["objective"]["port"])
        if self.output_name not in ports:
            raise ValueError("objective port missing from compiled manifest")
        self.output_vector = self._pad(np.asarray(ports[self.output_name]["vector"], dtype=float))
        self._drive_ports = [p for p in self.manifest["ports"] if p["kind"] == "drive"]

        self.a_current = np.zeros(self.tile.nodes, dtype=float)
        self.a_previous = np.zeros(self.tile.nodes, dtype=float)
        self.b_current = np.zeros(self.tile.nodes, dtype=float)
        self.b_previous = np.zeros(self.tile.nodes, dtype=float)
        self._reset_lane_a()

    def _pad(self, x: Array) -> Array:
        out = np.zeros(self.tile.nodes, dtype=float)
        out[: len(x)] = x
        return out

    def _reset_lane_a(self) -> None:
        self.a_current.fill(0.0)
        self.a_previous.fill(0.0)
        x0 = np.asarray(self.manifest["initial_state"], dtype=float)
        xm1 = np.asarray(self.manifest["initial_previous"], dtype=float)
        self.a_current[: self.tile.logical_nodes] = x0
        self.a_previous[: self.tile.logical_nodes] = xm1
        self.b_current.fill(0.0)
        self.b_previous.fill(0.0)

    def _forward_source_schedule(self) -> Array:
        if self.forward_source is not None:
            return self.forward_source
        T = self.tile.steps
        src = np.zeros((T, self.tile.nodes), dtype=float)
        for p in self._drive_ports:
            b = self._pad(np.asarray(p["vector"], dtype=float))
            wave = np.asarray(p["compiled_waveform"], dtype=float)
            qwave = self.tile.quantize_dac_schedule(wave)
            src += qwave[:, None] * b[None, :]
        self.forward_source = src
        return src

    def _sense(self, state: Array) -> float:
        raw = float(np.dot(self.output_vector, state))
        return float(self.tile.quantize_adc(raw))

    def _clip(self, x: Array) -> Array:
        if not self.tile.config.clip_state:
            return x
        return np.clip(x, -self.tile.config.state_full_scale, self.tile.config.state_full_scale)

    def _state_noise(self) -> Array:
        if self.tile.config.state_noise_std <= 0.0:
            return np.zeros(self.tile.nodes, dtype=float)
        return self.tile.rng.normal(
            0.0,
            self.tile.config.state_noise_std * self.tile.config.state_full_scale,
            size=self.tile.nodes,
        )

    def _single_tick(
        self,
        current: Array,
        previous: Array,
        source: Array,
        self_coeff: Array,
        edge_matrix: Array,
        injection: Array,
        *,
        stochastic: bool,
    ) -> tuple[Array, Array]:
        x = self.tile.retention * current
        xm1 = self.tile.retention * previous
        nxt = self_coeff * x + edge_matrix @ x - self.tile.prev_ratio_gain * xm1 + source + injection
        if stochastic:
            nxt = nxt + self._state_noise()
        return self._clip(nxt), x

    def _run_forward(self, *, stochastic: bool) -> tuple[Array, Array, Array, Array]:
        self._reset_lane_a()
        self_coeff, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)
        for k in range(self.tile.steps):
            self.a_current, self.a_previous = self._single_tick(
                self.a_current,
                self.a_previous,
                src[k],
                self_coeff,
                edge_matrix,
                inj_a,
                stochastic=stochastic,
            )
            trace[k] = self._sense(self.a_current)
        self.forward_trace = trace
        return self_coeff, edge_matrix, edge_amounts, inj_a

    def _objective(self) -> float:
        if self.forward_trace is None:
            raise RuntimeError("objective requested before forward run")
        w = np.asarray(self.manifest["objective"]["compiled_quadratic_weights"], dtype=float)
        if len(w) != len(self.forward_trace):
            raise ValueError("objective weight length mismatch")
        return float(np.sum(w * self.forward_trace * self.forward_trace))

    def _build_error_schedule(self) -> Array:
        if self.forward_trace is None:
            raise RuntimeError("error schedule requires forward output trace")
        T = self.tile.steps
        mult = np.asarray(self.manifest["objective"]["compiled_error_multiplier"], dtype=float)
        scalar = mult * self.forward_trace
        q = np.zeros((T + 1, self.tile.nodes), dtype=float)
        q[1:] = scalar[:, None] * self.output_vector[None, :]
        q[1:] = self.tile.quantize_error_schedule(q[1:])
        self.error_schedule = q
        return q

    def _clone_and_mirror(self, error_schedule: Array, *, stochastic: bool) -> None:
        # One terminal analog copy into lane B.
        self.b_current = self.a_current * self.tile.clone_gain_current
        self.b_previous = self.a_previous * self.tile.clone_gain_previous
        if stochastic and self.tile.config.terminal_clone_noise_std > 0.0:
            sigma = self.tile.config.terminal_clone_noise_std * self.tile.config.state_full_scale
            self.b_current = self.b_current + self.tile.rng.normal(0.0, sigma, size=self.tile.nodes)
            self.b_previous = self.b_previous + self.tile.rng.normal(0.0, sigma, size=self.tile.nodes)

        # Exact time mirror is a role swap, not a gain operation.
        self.a_current, self.a_previous = self.a_previous.copy(), self.a_current.copy()
        self.b_current, self.b_previous = self.b_previous.copy(), self.b_current.copy()

        asym = self.tile.config.error_dac_sign_asymmetry
        plus_gain = 1.0 + 0.5 * asym
        minus_gain = 1.0 - 0.5 * asym
        qT = error_schedule[self.tile.steps]
        self.a_current = self._clip(self.a_current + plus_gain * qT)
        self.b_current = self._clip(self.b_current - minus_gain * qT)

    def _lcc_square(self, x: Array) -> Array:
        x = np.asarray(x, dtype=float)
        kappa = self.tile.config.lcc_curvature
        if kappa == 0.0:
            return x * x
        edge_fs = max(2.0 * self.tile.config.state_full_scale, 1e-30)
        y = x / edge_fs
        return x * x * (1.0 + kappa * y * y)

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

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus_sum = np.zeros_like(acc)
        minus_sum = np.zeros_like(acc)
        credit_ret = math.exp(-self.tile.config.credit_accumulator_leakage)

        asym = self.tile.config.error_dac_sign_asymmetry
        plus_gain = 1.0 + 0.5 * asym
        minus_gain = 1.0 - 0.5 * asym
        settle = self.tile.config.edge_settling_error
        memory = self.tile.config.ab_edge_memory

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

            edge_a = edge_matrix @ ax
            edge_b = (1.0 - settle) * (edge_matrix @ bx) + memory * edge_a

            next_a = self_coeff * ax + edge_a - self.tile.prev_ratio_gain * ap + common + qa + inj_a
            next_b = self_coeff * bx + edge_b - self.tile.prev_ratio_gain * bp + common + qb + inj_b
            if stochastic:
                next_a = next_a + self._state_noise()
                next_b = next_b + self._state_noise()
            self.a_previous, self.a_current = ax, self._clip(next_a)
            self.b_previous, self.b_current = bx, self._clip(next_b)

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc

    def _finalize_credit(self, raw_overlap: Array) -> Array:
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
                g = g + self.tile.rng.normal(0.0, sigma, size=len(g))
        self.credits = np.asarray(g, dtype=float)
        return self.credits.copy()

    def execute(self, *, stochastic_forward: bool = True) -> dict[str, Any]:
        """Execute one circuit-native physical gradient evaluation."""
        self.forward_source = None
        self.error_schedule = None
        self.credits = None
        self.plus_energy = None
        self.minus_energy = None

        # PARAM_HOLD: physical components are evaluated once and reused by
        # forward and both lockstep reverse contexts.
        self_coeff, edge_matrix, edge_amounts, _ = self._run_forward(
            stochastic=stochastic_forward
        )
        self.objective_value = self._objective()
        qerr = self._build_error_schedule()
        self._clone_and_mirror(qerr, stochastic=stochastic_forward)
        raw = self._run_lockstep_reverse(
            self_coeff,
            edge_matrix,
            edge_amounts,
            stochastic=stochastic_forward,
        )
        credits = self._finalize_credit(raw)
        return {
            "objective": self.objective_value,
            "credits": credits,
            "forward_trace": None if self.forward_trace is None else self.forward_trace.copy(),
            "plus_energy": None if self.plus_energy is None else self.plus_energy.copy(),
            "minus_energy": None if self.minus_energy is None else self.minus_energy.copy(),
        }

    def deterministic_forward_loss(self) -> float:
        """Evaluate the currently programmed physical forward body."""
        self.forward_source = None
        self._run_forward(stochastic=False)
        return self._objective()


def _nominal_gain_config(config: TW1ACircuitEmulatorConfig) -> TW1ACircuitEmulatorConfig:
    """Compiler-model conditions used only to pick one frozen sense PGA."""
    return replace(
        config,
        adc_bits=None,
        state_noise_std=0.0,
        leakage_rate=0.0,
        leakage_cv=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        edge_gain_cv=0.0,
        self_gain_cv=0.0,
        terminal_clone_gain_std=0.0,
        terminal_clone_noise_std=0.0,
        edge_settling_error=0.0,
        ab_edge_memory=0.0,
        edge_charge_injection_std=0.0,
        prev_ratio_error_std=0.0,
        error_dac_sign_asymmetry=0.0,
        lcc_curvature=0.0,
        credit_accumulator_leakage=0.0,
        seed=777,
    )


def _initial_raw_peak(manifest: dict[str, Any], config: TW1ACircuitEmulatorConfig) -> float:
    tile = TW1ACircuitTile(manifest, _nominal_gain_config(config), sense_gain=1.0)
    interp = LockstepCircuitInterpreter(tile)
    interp._run_forward(stochastic=False)
    trace = np.asarray(interp.forward_trace, dtype=float)
    return float(np.max(np.abs(trace))) if trace.size else 0.0


def recommend_sense_gain(
    task: dict[str, Any],
    config: TW1ACircuitEmulatorConfig,
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
    if peak <= 0.0:
        return float(max_gain)
    target = float(config.adc_full_scale) * float(target_fraction)
    gain = 1
    while gain * 2 <= max_gain and peak * (gain * 2) <= target:
        gain *= 2
    return float(gain)


def _make_pair(
    task: dict[str, Any],
    config: TW1ACircuitEmulatorConfig,
    sense_gain: float,
    *,
    seed_offset: int,
) -> tuple[TW1ACircuitTile, TW1ACircuitTile]:
    tc = replace(config, seed=int(config.seed) + seed_offset)
    dc = replace(config, seed=int(config.seed) + seed_offset + 1)
    t = TW1ACircuitTile(task["target"], tc, sense_gain=sense_gain)
    d = TW1ACircuitTile(task["distractor"], dc, sense_gain=sense_gain)
    copy_circuit_disorder(t, d)
    _sync_theta(t, d)
    return t, d


def _eval_pair(
    ti: LockstepCircuitInterpreter, di: LockstepCircuitInterpreter
) -> tuple[float, float, float]:
    et = float(ti.deterministic_forward_loss())
    ed = float(di.deterministic_forward_loss())
    return et, ed, contrast_from_energies(et, ed)


def run_order_contrast_training(
    task: dict[str, Any],
    config: TW1ACircuitEmulatorConfig | None = None,
    *,
    sense_gain: float | None = None,
    iterations: int = 30,
    step_size: float = 0.20,
    normalize_rms: bool = True,
    include_shuffle: bool = True,
    shuffle_seed: int = 1729,
    eps: float = 1e-30,
) -> tuple[OrderContrastTrainingResult, float]:
    """Run temporal-order learning through the lockstep circuit emulator."""
    cfg = TW1ACircuitEmulatorConfig() if config is None else config
    gain = recommend_sense_gain(task, cfg) if sense_gain is None else float(sense_gain)

    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t)
    _sync_theta(exact_t, shuffle_d)

    eti = LockstepCircuitInterpreter(exact_t)
    edi = LockstepCircuitInterpreter(exact_d)
    sti = LockstepCircuitInterpreter(shuffle_t)
    sdi = LockstepCircuitInterpreter(shuffle_d)

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

        # Tile apply_credits performs descent; negate dC/dtheta to maximize C.
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

    result = OrderContrastTrainingResult(
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
    )
    return result, gain
