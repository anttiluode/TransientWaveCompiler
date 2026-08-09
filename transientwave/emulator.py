"""Noisy TW-1A 8x8 physical-tile emulator and closed-loop trainer.

The emulator executes the *compiled* reversible recurrence.  It intentionally
models the first mixed-signal hardware contract rather than a generic neural
network accelerator:

    z[n+1] = Q z[n] - z[n-1] + source[n]

Training uses the four-pass microcode emitted by :mod:`transientwave.microcode`.
The tile stores only the live second-order state pair plus one scalar energy
accumulator per trainable edge.  The Python emulator may of course keep
additional diagnostics, but the interpreter never uses an N x T forward-state
history to form credit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any, Iterable

import numpy as np

from .backend import TW1AGridBackend


Array = np.ndarray


@dataclass(frozen=True)
class TW1APhysicalTileConfig:
    """Mixed-signal imperfection model for the logical TW-1A tile.

    Fractions are dimensionless RMS/gain fractions. ``leakage_rate`` is the
    exponential rate per tile tick, so a node with rate ``ell`` retains
    ``exp(-ell)`` of each analog state register between updates.
    """

    weight_bits: int | None = 8
    weight_quantizer: str = "uniform"  # uniform | mu_law
    weight_mu: float = 31.0
    dac_bits: int | None = 8
    adc_bits: int | None = 8

    state_noise_std: float = 0.0
    state_full_scale: float = 2.0
    clip_state: bool = True

    leakage_rate: float = 0.0
    leakage_cv: float = 0.0

    mirror_error: float = 0.05
    differential_pass_drift: float = 0.002

    credit_offset_fraction: float = 0.0
    credit_noise_fraction: float = 0.05

    adc_full_scale: float = 2.0
    seed: int = 0

    def validate(self) -> None:
        for name, bits in (
            ("weight_bits", self.weight_bits),
            ("dac_bits", self.dac_bits),
            ("adc_bits", self.adc_bits),
        ):
            if bits is not None and bits < 2:
                raise ValueError(f"{name} must be >=2 or None")
        if self.weight_quantizer not in {"uniform", "mu_law"}:
            raise ValueError("weight_quantizer must be 'uniform' or 'mu_law'")
        if self.weight_mu <= 0:
            raise ValueError("weight_mu must be positive")
        if self.state_full_scale <= 0 or self.adc_full_scale <= 0:
            raise ValueError("full-scale values must be positive")
        for name in (
            "state_noise_std",
            "leakage_rate",
            "leakage_cv",
            "mirror_error",
            "differential_pass_drift",
            "credit_offset_fraction",
            "credit_noise_fraction",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")


def _uniform_quantize(x: Array, bits: int | None, full_scale: float) -> Array:
    x = np.asarray(x, dtype=float)
    if bits is None:
        return x.copy()
    levels = (1 << int(bits)) - 1
    if levels <= 0:
        return x.copy()
    fs = float(abs(full_scale))
    if fs <= 0:
        return np.zeros_like(x)
    y = np.clip(x, -fs, fs)
    q = np.round((y + fs) * levels / (2.0 * fs))
    return q * (2.0 * fs) / levels - fs


def _mu_law_quantize(x: Array, bits: int | None, full_scale: float, mu: float) -> Array:
    x = np.asarray(x, dtype=float)
    if bits is None:
        return x.copy()
    fs = float(abs(full_scale))
    if fs <= 0:
        return np.zeros_like(x)
    y = np.clip(x / fs, -1.0, 1.0)
    c = np.sign(y) * np.log1p(mu * np.abs(y)) / math.log1p(mu)
    cq = _uniform_quantize(c, bits, 1.0)
    out = np.sign(cq) * np.expm1(np.abs(cq) * math.log1p(mu)) / mu
    return fs * out


def _rms(x: Array) -> float:
    a = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(a * a))) if a.size else 0.0


class TW1APhysicalTile:
    """Stateful 8x8 mixed-signal TW-1A tile.

    ``programmed_Q`` is the host-programmed high-resolution coefficient matrix.
    Every traversal derives a quantized physical matrix from it.  Reverse PLUS
    and MINUS passes may then receive independent quasi-static reciprocal drift.
    """

    def __init__(self, manifest: dict[str, Any], config: TW1APhysicalTileConfig | None = None):
        self.manifest = manifest
        self.config = TW1APhysicalTileConfig() if config is None else config
        self.config.validate()
        self.backend = TW1AGridBackend()
        if manifest.get("backend") != "tw1a-8x8-v0":
            raise ValueError("TW1APhysicalTile requires a strict tw1a-8x8-v0 manifest")

        self.logical_nodes = int(manifest["resources"]["nodes"])
        if not 0 < self.logical_nodes <= self.backend.nodes:
            raise ValueError("invalid logical node count")
        self.nodes = self.backend.nodes
        self.steps = int(manifest["steps"])
        self.rng = np.random.default_rng(self.config.seed)

        q = np.asarray(manifest["Q"], dtype=float)
        if q.shape != (self.logical_nodes, self.logical_nodes):
            raise ValueError("manifest Q shape does not match logical node count")
        self.base_manifest_Q = np.zeros((self.nodes, self.nodes), dtype=float)
        self.base_manifest_Q[: self.logical_nodes, : self.logical_nodes] = q

        self.trainable = list(manifest.get("trainable_edges", []))
        self._train_pairs = [tuple(map(int, e["edge"])) for e in self.trainable]
        self._credit_scales = np.asarray(
            [float(e["compiled_credit_scale"]) for e in self.trainable], dtype=float
        )
        self._theta_min = np.asarray([float(e["min"]) for e in self.trainable], dtype=float)
        self._theta_max = np.asarray([float(e["max"]) for e in self.trainable], dtype=float)

        # Infer the initial parameter from the off-diagonal term.  Under the
        # compiler's declared rank-one edge semantics,
        #   dQ/dtheta = s (ei-ej)(ei-ej)^T,
        # hence dQ_ij/dtheta = -s.
        theta = []
        for (i, j), s, lo, hi in zip(
            self._train_pairs, self._credit_scales, self._theta_min, self._theta_max
        ):
            if abs(s) < 1e-30:
                raise ValueError(f"trainable edge {(i, j)} has zero compiled_credit_scale")
            t = -self.base_manifest_Q[i, j] / s
            if t < lo - 1e-7 or t > hi + 1e-7:
                raise ValueError(
                    f"cannot infer initial parameter for edge {(i, j)}: {t} outside [{lo},{hi}]"
                )
            theta.append(float(np.clip(t, lo, hi)))
        self.theta = np.asarray(theta, dtype=float)

        # Remove the inferred trainable contribution to leave a fixed base Q.
        self.fixed_Q = self.base_manifest_Q.copy()
        for t, (i, j), s in zip(self.theta, self._train_pairs, self._credit_scales):
            self._add_rank1(self.fixed_Q, i, j, -t * s)
        self.programmed_Q = self._rebuild_programmed_Q()

        # Quasi-static spatial leakage mismatch is fixed for the lifetime of a
        # tile instance.  Negative Gaussian draws are clipped to zero rate.
        if self.config.leakage_rate == 0.0:
            rates = np.zeros(self.nodes, dtype=float)
        else:
            mult = 1.0 + self.config.leakage_cv * self.rng.normal(size=self.nodes)
            rates = self.config.leakage_rate * np.maximum(mult, 0.0)
        self.leakage_rates = rates
        self.retention = np.exp(-rates)

        self._credit_offset_unit = self.rng.normal(size=max(1, len(self.trainable)))
        self.current = np.zeros(self.nodes, dtype=float)
        self.previous = np.zeros(self.nodes, dtype=float)
        self.reset_state()

    @staticmethod
    def _add_rank1(Q: Array, i: int, j: int, amount: float) -> None:
        Q[i, i] += amount
        Q[j, j] += amount
        Q[i, j] -= amount
        Q[j, i] -= amount

    def _rebuild_programmed_Q(self) -> Array:
        q = self.fixed_Q.copy()
        for t, (i, j), s in zip(self.theta, self._train_pairs, self._credit_scales):
            self._add_rank1(q, i, j, t * s)
        self.programmed_Q = q
        return q

    def clone(self, *, seed: int | None = None) -> "TW1APhysicalTile":
        cfg = self.config if seed is None else replace(self.config, seed=seed)
        out = TW1APhysicalTile(self.manifest, cfg)
        out.theta = self.theta.copy()
        out.fixed_Q = self.fixed_Q.copy()
        out._rebuild_programmed_Q()
        # Preserve the same leakage field for deterministic comparison when the
        # seed is unchanged; a changed seed deliberately creates another chip.
        if seed is None or seed == self.config.seed:
            out.leakage_rates = self.leakage_rates.copy()
            out.retention = self.retention.copy()
        return out

    def reset_state(self) -> None:
        self.current.fill(0.0)
        self.previous.fill(0.0)
        x0 = np.asarray(self.manifest["initial_state"], dtype=float)
        xm1 = np.asarray(self.manifest["initial_previous"], dtype=float)
        self.current[: self.logical_nodes] = x0
        self.previous[: self.logical_nodes] = xm1

    def _quantize_weight_values(self, x: Array, full_scale: float) -> Array:
        if self.config.weight_quantizer == "uniform":
            return _uniform_quantize(x, self.config.weight_bits, full_scale)
        return _mu_law_quantize(
            x, self.config.weight_bits, full_scale, self.config.weight_mu
        )

    def quantized_Q(self) -> Array:
        """Return a reciprocal Q after programmed coefficient quantization."""
        src = self.programmed_Q
        q = np.zeros_like(src)
        # Diagonal path has its own physical range.
        diag = np.diag(src)
        qdiag = self._quantize_weight_values(diag, max(abs(self.backend.q_diag_min), abs(self.backend.q_diag_max)))
        np.fill_diagonal(q, qdiag)

        # Only legal four-neighbor physical couplings exist in silicon.
        for i, j in self.backend.physical_edges():
            v = 0.5 * (src[i, j] + src[j, i])
            qq = float(
                self._quantize_weight_values(
                    np.asarray([v]), max(abs(self.backend.q_edge_min), abs(self.backend.q_edge_max))
                )[0]
            )
            q[i, j] = qq
            q[j, i] = qq
        return q

    def effective_Q(self, *, reverse: bool = False) -> Array:
        q = self.quantized_Q()
        if not reverse or self.config.differential_pass_drift == 0.0:
            return q

        sigma = self.config.differential_pass_drift
        out = q.copy()
        # Drift is reciprocal *within* one pass but independent between PLUS and
        # MINUS passes because each call draws a fresh quasi-static realization.
        d = 1.0 + self.rng.normal(0.0, sigma, size=self.nodes)
        idx = np.diag_indices(self.nodes)
        out[idx] *= d
        for i, j in self.backend.physical_edges():
            gain = 1.0 + float(self.rng.normal(0.0, sigma))
            out[i, j] *= gain
            out[j, i] = out[i, j]
        return out

    def quantize_dac_schedule(self, x: Array) -> Array:
        x = np.asarray(x, dtype=float)
        if self.config.dac_bits is None:
            return x.copy()
        fs = float(np.max(np.abs(x))) if x.size else 0.0
        if fs <= 0:
            return np.zeros_like(x)
        return _uniform_quantize(x, self.config.dac_bits, fs)

    def quantize_adc(self, x: Array | float) -> Array:
        return _uniform_quantize(np.asarray(x, dtype=float), self.config.adc_bits, self.config.adc_full_scale)

    def tick(self, source: Array, Q: Array, *, stochastic: bool = True) -> None:
        source = np.asarray(source, dtype=float)
        if source.shape != (self.nodes,):
            raise ValueError("source vector has wrong shape")

        x = self.retention * self.current
        xm1 = self.retention * self.previous
        nxt = Q @ x - xm1 + source
        if stochastic and self.config.state_noise_std > 0:
            nxt = nxt + self.rng.normal(
                0.0, self.config.state_noise_std * self.config.state_full_scale, size=self.nodes
            )
        if self.config.clip_state:
            nxt = np.clip(nxt, -self.config.state_full_scale, self.config.state_full_scale)
        self.previous = x
        self.current = nxt

    def mirror(self) -> None:
        """Reverse the terminal second-order state pair with gain error.

        Exact reversal swaps ``current`` and ``previous``.  The error model
        preserves their midpoint and scales the reversed difference by
        ``1-mirror_error``.  At zero error this is exactly a swap.
        """
        a = self.current.copy()
        b = self.previous.copy()
        mid = 0.5 * (a + b)
        diff = a - b
        gain = 1.0 - self.config.mirror_error
        self.current = mid - 0.5 * gain * diff
        self.previous = mid + 0.5 * gain * diff

    def edge_differences(self) -> Array:
        if not self._train_pairs:
            return np.zeros(0, dtype=float)
        return np.asarray([self.current[j] - self.current[i] for i, j in self._train_pairs])

    def apply_credits(
        self,
        credits: Array,
        *,
        step_size: float = 0.25,
        normalize_rms: bool = True,
    ) -> Array:
        """Apply host-side SGD to trainable source parameters and rebuild Q."""
        g = np.asarray(credits, dtype=float)
        if g.shape != self.theta.shape:
            raise ValueError("credit vector shape mismatch")
        if normalize_rms:
            denom = _rms(g) + 1e-12
            delta = -float(step_size) * g / denom
        else:
            delta = -float(step_size) * g
        new_theta = np.clip(self.theta + delta, self._theta_min, self._theta_max)
        self.theta = new_theta
        self._rebuild_programmed_Q()
        return new_theta.copy()


class MicrocodeInterpreter:
    """Execute compiled TW-1A inference/training microcode on a physical tile."""

    def __init__(self, tile: TW1APhysicalTile):
        self.tile = tile
        self.manifest = tile.manifest
        self.mode = "FORWARD"
        self.credit_phase = 1.0
        self.forward_trace: Array | None = None
        self.forward_source: Array | None = None
        self.error_schedule: Array | None = None
        self.objective_value: float | None = None
        self.plus_energy: Array | None = None
        self.minus_energy: Array | None = None
        self.credits: Array | None = None

        ports = {p["name"]: p for p in self.manifest["ports"]}
        self.output_name = str(self.manifest["objective"]["port"])
        if self.output_name not in ports:
            raise ValueError("objective port missing from compiled manifest")
        self.output_vector = self._pad(np.asarray(ports[self.output_name]["vector"], dtype=float))
        self._drive_ports = [p for p in self.manifest["ports"] if p["kind"] == "drive"]

    def _pad(self, x: Array) -> Array:
        out = np.zeros(self.tile.nodes, dtype=float)
        out[: len(x)] = x
        return out

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

    def _sense_output(self) -> float:
        raw = float(np.dot(self.output_vector, self.tile.current))
        return float(self.tile.quantize_adc(raw))

    def _run_forward(self, ticks: int, *, stochastic: bool = True) -> None:
        if ticks != self.tile.steps:
            raise ValueError("v0.1 interpreter expects the full compiled horizon")
        q = self.tile.effective_Q(reverse=False)
        src = self._forward_source_schedule()
        trace = np.zeros(ticks, dtype=float)
        for k in range(ticks):
            self.tile.tick(src[k], q, stochastic=stochastic)
            trace[k] = self._sense_output()
        self.forward_trace = trace

    def _objective(self) -> float:
        if self.forward_trace is None:
            raise RuntimeError("READ_OBJECTIVE before FORWARD")
        w = np.asarray(self.manifest["objective"]["compiled_quadratic_weights"], dtype=float)
        if len(w) != len(self.forward_trace):
            raise ValueError("objective weight length mismatch")
        return float(np.sum(w * self.forward_trace * self.forward_trace))

    def _build_error_schedule(self) -> Array:
        if self.forward_trace is None:
            raise RuntimeError("reverse pass requires a forward output trace")
        T = self.tile.steps
        mult = np.asarray(self.manifest["objective"]["compiled_error_multiplier"], dtype=float)
        # q[1..T] = dJ/dz[k] injected along the objective port.
        scalar = mult * self.forward_trace
        q = np.zeros((T + 1, self.tile.nodes), dtype=float)
        q[1:] = scalar[:, None] * self.output_vector[None, :]
        # Treat the complete error waveform as one scheduled DAC stream so bit
        # depth pays the quadratic-envelope dynamic-range cost.
        q[1:] = self.tile.quantize_dac_schedule(q[1:])
        self.error_schedule = q
        return q

    def _arm_mirror(self) -> None:
        self.tile.mirror()
        q = self._build_error_schedule()
        # a[0]=0, a[1]=q[T].  The mirror establishes w[1]; add the first
        # causal adjoint state before the first reverse energy sample.
        self.tile.current = self.tile.current + self.credit_phase * q[self.tile.steps]
        if self.tile.config.clip_state:
            self.tile.current = np.clip(
                self.tile.current,
                -self.tile.config.state_full_scale,
                self.tile.config.state_full_scale,
            )

    def _run_reverse(self, ticks: int) -> Array:
        if ticks != self.tile.steps:
            raise ValueError("v0.1 interpreter expects the full compiled horizon")
        if self.error_schedule is None:
            raise RuntimeError("MIRROR_ARM must precede reverse RUN")
        src_fwd = self._forward_source_schedule()
        qerr = self.error_schedule
        qpass = self.tile.effective_Q(reverse=True)
        energy = np.zeros(len(self.tile.trainable), dtype=float)

        # Current state is combined y[1]=w[1] +/- a[1].  Sample it, then
        # generate y[2] ... y[T].
        for j in range(1, ticks + 1):
            d = self.tile.edge_differences()
            energy += d * d
            if j < ticks:
                source = src_fwd[ticks - j] + self.credit_phase * qerr[ticks - j]
                source = self.tile.quantize_dac_schedule(source)
                self.tile.tick(source, qpass, stochastic=True)
        return energy

    def _read_credit(self) -> Array:
        if self.plus_energy is None or self.minus_energy is None:
            raise RuntimeError("READ_CREDIT before both reverse phases")
        cross = 0.25 * (self.plus_energy - self.minus_energy)
        g = self.tile._credit_scales * cross

        if len(g):
            energy_scale = 0.125 * (self.plus_energy + self.minus_energy)
            if self.tile.config.credit_offset_fraction > 0:
                g = g + (
                    self.tile.config.credit_offset_fraction
                    * self.tile._credit_scales
                    * energy_scale
                    * self.tile._credit_offset_unit[: len(g)]
                )
            if self.tile.config.credit_noise_fraction > 0:
                sigma = self.tile.config.credit_noise_fraction * (_rms(g) + 1e-30)
                g = g + self.tile.rng.normal(0.0, sigma, size=len(g))
        self.credits = np.asarray(g, dtype=float)
        return self.credits.copy()

    def execute(
        self,
        program: Iterable[dict[str, Any]] | None = None,
        *,
        stochastic_forward: bool = True,
    ) -> dict[str, Any]:
        """Execute one semantic microcode program."""
        code = (
            self.manifest["microcode"]["training"]
            if program is None
            else list(program)
        )
        for ins in code:
            op = str(ins["op"])
            if op == "CREDIT_CLEAR":
                self.plus_energy = None
                self.minus_energy = None
                self.credits = None
            elif op == "RESET_STATE":
                self.tile.reset_state()
            elif op == "SET_MODE":
                self.mode = str(ins["mode"])
            elif op == "CREDIT_PHASE":
                self.credit_phase = 1.0 if str(ins["sign"]) == "PLUS" else -1.0
            elif op == "FREEZE":
                pass
            elif op == "MIRROR_ARM":
                self._arm_mirror()
            elif op == "RUN":
                ticks = int(ins["ticks"])
                if self.mode == "FORWARD":
                    self._run_forward(ticks, stochastic=stochastic_forward)
                elif self.mode in {"REVERSE_PLUS", "REVERSE_MINUS"}:
                    e = self._run_reverse(ticks)
                    if self.mode == "REVERSE_PLUS":
                        self.plus_energy = e
                    else:
                        self.minus_energy = e
                else:
                    raise ValueError(f"unknown execution mode {self.mode!r}")
            elif op == "READ_OBJECTIVE":
                self.objective_value = self._objective()
            elif op == "READ_CREDIT":
                self._read_credit()
            elif op in {"SNAPSHOT_TERMINAL", "RESTORE_TERMINAL"}:
                raise NotImplementedError("TW-1A v0 emulator models the four-pass no-snapshot chip")
            else:
                raise ValueError(f"unsupported microcode op {op!r}")

        return {
            "objective": self.objective_value,
            "credits": None if self.credits is None else self.credits.copy(),
            "forward_trace": None if self.forward_trace is None else self.forward_trace.copy(),
            "plus_energy": None if self.plus_energy is None else self.plus_energy.copy(),
            "minus_energy": None if self.minus_energy is None else self.minus_energy.copy(),
        }

    def deterministic_forward_loss(self) -> float:
        """Evaluate current programmed hardware without stochastic noise/drift.

        Weight/DAC/ADC quantization and the fixed leakage field remain active.
        """
        self.tile.reset_state()
        self._run_forward(self.tile.steps, stochastic=False)
        return self._objective()


@dataclass
class TrainingResult:
    exact_loss: list[float]
    shuffled_loss: list[float]
    measured_objective: list[float]
    credit_rms: list[float]
    final_theta: Array
    final_theta_shuffled: Array

    @property
    def exact_reduction(self) -> float:
        a, b = self.exact_loss[0], self.exact_loss[-1]
        return float((a - b) / max(abs(a), 1e-30))

    @property
    def shuffled_reduction(self) -> float:
        a, b = self.shuffled_loss[0], self.shuffled_loss[-1]
        return float((a - b) / max(abs(a), 1e-30))


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
    """Run four-pass physical echo learning with a host-side SGD update.

    The shuffled arm receives the *same corrupted credit values* from the exact
    learner, permuted by one frozen edge permutation.  It therefore preserves
    update norm and marginal values while destroying physical edge placement.
    """
    cfg = TW1APhysicalTileConfig() if config is None else config
    exact_tile = TW1APhysicalTile(manifest, cfg)
    shuffle_tile = exact_tile.clone(seed=cfg.seed + 100_003)

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
