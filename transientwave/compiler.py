"""WaveProgram -> reversible TW-1 manifest compiler.

The v0.1 compiler intentionally implements only the exact scalar-damping path.
It is better to reject a model than silently approximate a physical semantic.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .ir import Program, program_from_dict


class CompileError(RuntimeError):
    """A source program cannot be represented by the selected exact backend."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _matrix(x: tuple[tuple[float, ...], ...] | None, n: int, name: str) -> np.ndarray:
    if x is None:
        raise CompileError("E001 MISSING_MATRIX", f"{name} is required")
    a = np.asarray(x, dtype=float)
    if a.shape != (n, n):
        raise CompileError("E002 MATRIX_SHAPE", f"{name} has shape {a.shape}, expected {(n, n)}")
    if not np.all(np.isfinite(a)):
        raise CompileError("E003 NONFINITE_MATRIX", f"{name} contains NaN or infinity")
    return a


def _symmetry_error(a: np.ndarray) -> float:
    return float(np.max(np.abs(a - a.T))) if a.size else 0.0


def _port_vector(program: Program, port) -> np.ndarray:
    n = program.state.nodes
    b = np.zeros(n, dtype=float)
    if port.node is not None:
        if not 0 <= port.node < n:
            raise CompileError("E120 PORT_NODE", f"port {port.name!r} uses invalid node {port.node}")
        b[port.node] += 1.0
    for i, w in port.sparse_weights:
        if not 0 <= i < n:
            raise CompileError("E120 PORT_NODE", f"port {port.name!r} uses invalid node {i}")
        b[i] += float(w)
    if not np.any(b):
        raise CompileError("E121 EMPTY_PORT", f"port {port.name!r} is not connected to any node")
    return b


def _waveform(values: tuple[float, ...], steps: int) -> np.ndarray:
    if len(values) > steps:
        raise CompileError(
            "E122 WAVEFORM_LENGTH",
            f"waveform has {len(values)} samples but program horizon is {steps}",
        )
    out = np.zeros(steps, dtype=float)
    if values:
        out[: len(values)] = np.asarray(values, dtype=float)
    return out


def _compile_objective(program: Program, r: float) -> dict[str, Any]:
    obj = program.objective
    names = {p.name: p for p in program.ports}
    if obj.port is None or obj.port not in names:
        raise CompileError("E150 OBJECTIVE_PORT", "objective must name an existing port")
    p = names[obj.port]
    if p.kind not in {"sense", "error"}:
        raise CompileError(
            "E151 OBJECTIVE_PORT_KIND",
            f"objective port {p.name!r} must be sense/error, got {p.kind!r}",
        )

    # Sense convention: sample k=0 observes state index n=k+1 after the kth mesh clock.
    state_index = np.arange(1, program.steps + 1, dtype=float)
    state_scale = r ** state_index

    if obj.kind == "quadratic_energy":
        source_weights = np.full(program.steps, obj.weight, dtype=float)
    elif obj.kind == "weighted_quadratic_energy":
        if len(obj.weights) != program.steps:
            raise CompileError(
                "E152 OBJECTIVE_WEIGHTS",
                "weighted_quadratic_energy requires exactly steps weights",
            )
        source_weights = np.asarray(obj.weights, dtype=float)
    else:
        raise CompileError(
            "E153 OBJECTIVE_KIND",
            f"objective kind {obj.kind!r} is not implemented in executable v0.1",
        )

    compiled_weights = source_weights * state_scale**2
    return {
        "kind": obj.kind,
        "port": obj.port,
        "sense_state_indices": [int(x) for x in state_index],
        "source_domain_weights": source_weights.tolist(),
        "compiled_quadratic_weights": compiled_weights.tolist(),
        "compiled_error_multiplier": (2.0 * compiled_weights).tolist(),
        "note": "error injection sample also multiplies the measured compiled port state z[k]",
    }


def compile_program(program: Program) -> dict[str, Any]:
    """Compile one WaveProgram into a JSON-serializable reversible TW-1 manifest."""
    n = program.state.nodes
    c = program.constraints

    if c.max_nodes is not None and n > c.max_nodes:
        raise CompileError("E010 NODE_LIMIT", f"program has {n} nodes; limit is {c.max_nodes}")
    if c.max_ports is not None and len(program.ports) > c.max_ports:
        raise CompileError(
            "E011 PORT_LIMIT", f"program has {len(program.ports)} ports; limit is {c.max_ports}"
        )

    gauge: dict[str, Any]
    if program.dynamics.form == "damped_second_order":
        a = float(program.dynamics.a)  # type: ignore[arg-type]
        if not (0.0 < a <= 1.0):
            raise CompileError(
                "E100 DAMPING_RANGE",
                f"exact damping-gauge backend requires 0 < a <= 1, got {a}",
            )
        M = _matrix(program.dynamics.M, n, "M")
        asym = _symmetry_error(M)
        if c.require_reciprocal and asym > c.max_operator_asymmetry:
            raise CompileError(
                "E101 NONRECIPROCAL",
                f"M asymmetry {asym:.3e} exceeds {c.max_operator_asymmetry:.3e}",
            )
        r = math.sqrt(a)
        Q = M / r
        input_envelope = r ** (-np.arange(1, program.steps + 1, dtype=float))
        state_scale = r ** np.arange(0, program.steps + 1, dtype=float)
        max_gain = float(np.max(np.abs(input_envelope)))
        if max_gain > c.max_boundary_gain:
            raise CompileError(
                "E305 BOUNDARY_GAIN",
                f"required input envelope reaches {max_gain:.6g}x, limit is {c.max_boundary_gain:.6g}x",
            )
        gauge = {
            "kind": "scalar_damping_gauge",
            "a": a,
            "r": r,
            "input_envelope": input_envelope.tolist(),
            "state_scale_psi_over_z": state_scale.tolist(),
            "max_input_gain": max_gain,
            "z_initial_from_psi_initial": 1.0,
            "z_previous_from_psi_previous": r,
        }
        z0 = np.asarray(program.state.initial, dtype=float)
        zprev = r * np.asarray(program.state.initial_previous, dtype=float)
    elif program.dynamics.form == "reversible_second_order":
        Q = _matrix(program.dynamics.Q, n, "Q")
        asym = _symmetry_error(Q)
        if c.require_reciprocal and asym > c.max_operator_asymmetry:
            raise CompileError(
                "E101 NONRECIPROCAL",
                f"Q asymmetry {asym:.3e} exceeds {c.max_operator_asymmetry:.3e}",
            )
        r = 1.0
        input_envelope = np.ones(program.steps, dtype=float)
        gauge = {
            "kind": "identity",
            "a": 1.0,
            "r": 1.0,
            "input_envelope": input_envelope.tolist(),
            "state_scale_psi_over_z": np.ones(program.steps + 1).tolist(),
            "max_input_gain": 1.0,
            "z_initial_from_psi_initial": 1.0,
            "z_previous_from_psi_previous": 1.0,
        }
        z0 = np.asarray(program.state.initial, dtype=float)
        zprev = np.asarray(program.state.initial_previous, dtype=float)
    else:  # parser should already prevent this
        raise CompileError("E099 DYNAMICS_FORM", program.dynamics.form)

    asym_q = _symmetry_error(Q)
    if c.require_reciprocal and asym_q > c.max_operator_asymmetry:
        raise CompileError(
            "E101 NONRECIPROCAL",
            f"compiled Q asymmetry {asym_q:.3e} exceeds tolerance",
        )

    # Exact backend is symmetric, therefore eigvalsh is appropriate and auditable.
    evals = np.linalg.eigvalsh((Q + Q.T) * 0.5)
    lo = float(np.min(evals))
    hi = float(np.max(evals))
    allowed_lo = -2.0 + c.stability_margin
    allowed_hi = 2.0 - c.stability_margin
    if lo < allowed_lo or hi > allowed_hi:
        raise CompileError(
            "E211 STABILITY_MARGIN",
            f"compiled Q eigenvalue range [{lo:.8g}, {hi:.8g}] is outside "
            f"[{allowed_lo:.8g}, {allowed_hi:.8g}]",
        )

    compiled_ports = []
    drive_count = 0
    for p in program.ports:
        vector = _port_vector(program, p)
        rec: dict[str, Any] = {
            "name": p.name,
            "kind": p.kind,
            "vector": vector.tolist(),
        }
        if p.kind == "drive":
            drive_count += 1
            source_wave = _waveform(p.waveform, program.steps)
            compiled_wave = source_wave * input_envelope
            port_limit = c.max_boundary_gain if p.gain_limit is None else p.gain_limit
            if np.max(np.abs(compiled_wave)) > port_limit + 1e-15:
                raise CompileError(
                    "E306 PORT_GAIN",
                    f"compiled waveform on port {p.name!r} exceeds gain/amplitude limit {port_limit}",
                )
            rec["source_waveform"] = source_wave.tolist()
            rec["compiled_waveform"] = compiled_wave.tolist()
        compiled_ports.append(rec)

    objective = _compile_objective(program, r)

    trainable = []
    seen_edges: set[tuple[int, int]] = set()
    for e in program.trainable_edges:
        if e.i == e.j or not (0 <= e.i < n and 0 <= e.j < n):
            raise CompileError("E180 EDGE_INDEX", f"invalid trainable edge ({e.i}, {e.j})")
        ij = tuple(sorted((e.i, e.j)))
        if ij in seen_edges:
            raise CompileError("E181 DUPLICATE_EDGE", f"duplicate trainable edge {ij}")
        seen_edges.add(ij)
        if e.minimum > e.maximum:
            raise CompileError("E182 EDGE_RANGE", f"edge {ij} has min > max")
        # Source parameter semantics:
        # dM/dtheta = matrix_scale * (ei-ej)(ei-ej)^T.
        # Q=M/r, hence local compiled overlap is scaled by matrix_scale/r.
        trainable.append(
            {
                "edge": [e.i, e.j],
                "group": e.group,
                "min": e.minimum,
                "max": e.maximum,
                "source_matrix_scale": e.matrix_scale,
                "compiled_credit_scale": e.matrix_scale / r,
                "parameterization": "rank1_edge_difference",
            }
        )

    if c.max_edges is not None and len(trainable) > c.max_edges:
        raise CompileError(
            "E012 EDGE_LIMIT",
            f"program has {len(trainable)} trainable edges; limit is {c.max_edges}",
        )

    tile_size = 64
    tile_count = int(math.ceil(n / tile_size))
    if tile_count > 1 and not c.allow_partition:
        raise CompileError(
            "E400 PARTITION_REQUIRED",
            f"TW-1 v0.1 logical tile has {tile_size} nodes; program needs {tile_count} tiles and allow_partition=false",
        )

    node_map = [
        {"logical_node": i, "tile": i // tile_size, "tile_node": i % tile_size}
        for i in range(n)
    ]

    return {
        "format": "tw1-manifest-v0.1",
        "program": program.name,
        "steps": program.steps,
        "dt": program.dt,
        "backend": "tw1-clocked-mixed-signal",
        "recurrence": "z[n+1] = Q z[n] - z[n-1] + source[n]",
        "Q": Q.tolist(),
        "initial_state": z0.tolist(),
        "initial_previous": zprev.tolist(),
        "gauge": gauge,
        "ports": compiled_ports,
        "objective": objective,
        "trainable_edges": trainable,
        "stability": {
            "eigenvalue_min": lo,
            "eigenvalue_max": hi,
            "allowed_min": allowed_lo,
            "allowed_max": allowed_hi,
            "margin_to_minus_two": lo + 2.0,
            "margin_to_plus_two": 2.0 - hi,
        },
        "resources": {
            "nodes": n,
            "trainable_edges": len(trainable),
            "ports": len(program.ports),
            "drive_ports": drive_count,
            "tile_size": tile_size,
            "tiles": tile_count,
            "live_state_scalars": 2 * n,
            "trajectory_history_scalars": 0,
            "local_credit_scalars": len(trainable),
        },
        "training_protocol": {
            "default_passes_without_terminal_restore": 4,
            "phases": [
                "forward",
                "reverse_plus",
                "forward_recreate_terminal_state",
                "reverse_minus",
                "parameter_update",
            ],
            "local_observable": "(E_plus - E_minus)/4",
        },
        "diagnostics": {
            "source_operator_asymmetry": asym,
            "compiled_operator_asymmetry": asym_q,
            "note": "v0.1 emits logical placement only; coefficient quantization and physical routing are future backend passes",
        },
    }


def compile_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return compile_program(program_from_dict(data))


def simulate_source(program: Program) -> np.ndarray:
    """Reference source-domain state history, including state index 0."""
    n = program.state.nodes
    if program.dynamics.form != "damped_second_order":
        raise ValueError("simulate_source currently expects damped_second_order")
    M = _matrix(program.dynamics.M, n, "M")
    a = float(program.dynamics.a)  # type: ignore[arg-type]
    x_prev = np.asarray(program.state.initial_previous, dtype=float).copy()
    x = np.asarray(program.state.initial, dtype=float).copy()
    hist = [x.copy()]
    drive_ports = [(p, _port_vector(program, p), _waveform(p.waveform, program.steps))
                   for p in program.ports if p.kind == "drive"]
    for k in range(program.steps):
        source = np.zeros(n, dtype=float)
        for _p, b, w in drive_ports:
            source += b * w[k]
        nxt = M @ x - a * x_prev + source
        x_prev, x = x, nxt
        hist.append(x.copy())
    return np.asarray(hist)


def simulate_compiled(program: Program, manifest: dict[str, Any] | None = None) -> np.ndarray:
    """Reference compiled z history, including state index 0."""
    man = compile_program(program) if manifest is None else manifest
    Q = np.asarray(man["Q"], dtype=float)
    z_prev = np.asarray(man["initial_previous"], dtype=float).copy()
    z = np.asarray(man["initial_state"], dtype=float).copy()
    hist = [z.copy()]
    drives = [(np.asarray(p["vector"], dtype=float), np.asarray(p["compiled_waveform"], dtype=float))
              for p in man["ports"] if p["kind"] == "drive"]
    for k in range(program.steps):
        source = np.zeros(program.state.nodes, dtype=float)
        for b, w in drives:
            source += b * w[k]
        nxt = Q @ z - z_prev + source
        z_prev, z = z, nxt
        hist.append(z.copy())
    return np.asarray(hist)
