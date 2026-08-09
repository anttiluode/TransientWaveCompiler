"""WaveProgram -> reversible TW-1 manifest compiler.

The executable v0.1 path is intentionally narrow: linear, reciprocal, scalar-damped
second-order wave systems. The compiler rejects unsupported physics rather than
silently approximating it.
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


def _matrix(x, n: int, name: str) -> np.ndarray:
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


def _check_reciprocal(program: Program, A: np.ndarray, name: str) -> float:
    asym = _symmetry_error(A)
    c = program.constraints
    if c.require_reciprocal and asym > c.max_operator_asymmetry:
        raise CompileError(
            "E101 NONRECIPROCAL",
            f"{name} asymmetry {asym:.3e} exceeds {c.max_operator_asymmetry:.3e}",
        )
    return asym


def _lower_source_recurrence(program: Program) -> dict[str, Any]:
    """Lower the source model to x[n+1]=M x[n]-a x[n-1]+drive_scale*source[n]."""
    n = program.state.nodes
    d = program.dynamics

    if d.form == "damped_second_order":
        a = float(d.a)  # type: ignore[arg-type]
        M = _matrix(d.M, n, "M")
        asym = _check_reciprocal(program, M, "M")
        return {
            "kind": "damped_second_order",
            "a": a,
            "M": M,
            "drive_scale": 1.0,
            "source_operator_asymmetry": asym,
            "integration": "already_discrete",
        }

    if d.form == "continuous_damped_wave":
        if d.integration != "semi_implicit_euler":
            raise CompileError(
                "E090 INTEGRATION_SCHEME",
                f"continuous_damped_wave supports only semi_implicit_euler in v0.1, got {d.integration!r}",
            )
        gamma = float(d.gamma)  # type: ignore[arg-type]
        if gamma < 0:
            raise CompileError("E091 NEGATIVE_DAMPING", f"gamma must be >= 0, got {gamma}")
        H = _matrix(d.H, n, "H")
        asym = _check_reciprocal(program, H, "H")
        a = 1.0 - program.dt * gamma
        M = (1.0 + a) * np.eye(n) - (program.dt**2) * H
        return {
            "kind": "continuous_damped_wave",
            "a": a,
            "M": M,
            "H": H,
            "gamma": gamma,
            "drive_scale": program.dt**2,
            "source_operator_asymmetry": asym,
            "integration": "semi_implicit_euler",
            "lowering_equations": {
                "velocity": "v[n+1]=(1-dt*gamma)v[n]-dt*H*x[n]+dt*source[n]",
                "position": "x[n+1]=x[n]+dt*v[n+1]",
                "second_order": "x[n+1]=M*x[n]-a*x[n-1]+dt^2*source[n]",
            },
        }

    raise CompileError("E099 DYNAMICS_FORM", f"{d.form!r} has no damped source lowering")


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
        "note": "error sample = compiled_error_multiplier[k] * measured compiled output z[k+1]",
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

    source_lowering: dict[str, Any]
    if program.dynamics.form == "reversible_second_order":
        Q = _matrix(program.dynamics.Q, n, "Q")
        asym = _check_reciprocal(program, Q, "Q")
        r = 1.0
        drive_scale = 1.0
        input_envelope = np.ones(program.steps, dtype=float)
        state_scale = np.ones(program.steps + 1, dtype=float)
        z0 = np.asarray(program.state.initial, dtype=float)
        zprev = np.asarray(program.state.initial_previous, dtype=float)
        source_lowering = {
            "kind": "reversible_second_order",
            "drive_scale": 1.0,
            "source_operator_asymmetry": asym,
            "integration": "already_reversible",
        }
        gauge = {
            "kind": "identity",
            "a": 1.0,
            "r": r,
            "input_envelope": input_envelope.tolist(),
            "state_scale_psi_over_z": state_scale.tolist(),
            "max_input_gain": 1.0,
            "z_initial_from_psi_initial": 1.0,
            "z_previous_from_psi_previous": 1.0,
        }
    else:
        source_lowering = _lower_source_recurrence(program)
        M = np.asarray(source_lowering["M"], dtype=float)
        a = float(source_lowering["a"])
        drive_scale = float(source_lowering["drive_scale"])
        if not (0.0 < a <= 1.0):
            raise CompileError(
                "E100 DAMPING_RANGE",
                f"exact damping-gauge backend requires 0 < a <= 1 after lowering, got {a}",
            )
        r = math.sqrt(a)
        Q = M / r
        input_envelope = r ** (-np.arange(1, program.steps + 1, dtype=float))
        state_scale = r ** np.arange(0, program.steps + 1, dtype=float)
        max_gain = float(np.max(np.abs(input_envelope)))
        if max_gain > c.max_boundary_gain:
            raise CompileError(
                "E305 BOUNDARY_GAIN",
                f"required damping-gauge envelope reaches {max_gain:.6g}x, limit is {c.max_boundary_gain:.6g}x",
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

    asym_q = _check_reciprocal(program, Q, "compiled Q")
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
        rec: dict[str, Any] = {"name": p.name, "kind": p.kind, "vector": vector.tolist()}
        if p.kind == "drive":
            drive_count += 1
            source_wave = _waveform(p.waveform, program.steps)
            recurrence_wave = source_wave * drive_scale
            compiled_wave = recurrence_wave * input_envelope
            port_limit = c.max_boundary_gain if p.gain_limit is None else p.gain_limit
            if float(np.max(np.abs(compiled_wave))) > port_limit + 1e-15:
                raise CompileError(
                    "E306 PORT_GAIN",
                    f"compiled waveform on port {p.name!r} exceeds amplitude limit {port_limit}",
                )
            rec["source_waveform"] = source_wave.tolist()
            rec["recurrence_waveform"] = recurrence_wave.tolist()
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

        if e.parameter_space == "recurrence_M":
            source_matrix_scale = e.scale
        elif e.parameter_space == "stiffness_H":
            if source_lowering["kind"] != "continuous_damped_wave":
                raise CompileError(
                    "E183 EDGE_PARAMETER_SPACE",
                    "stiffness_scale is legal only with continuous_damped_wave",
                )
            source_matrix_scale = -(program.dt**2) * e.scale
        else:
            raise CompileError("E183 EDGE_PARAMETER_SPACE", e.parameter_space)

        trainable.append(
            {
                "edge": [e.i, e.j],
                "group": e.group,
                "min": e.minimum,
                "max": e.maximum,
                "parameter_space": e.parameter_space,
                "declared_parameter_scale": e.scale,
                "source_matrix_scale": source_matrix_scale,
                "compiled_credit_scale": source_matrix_scale / r,
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

    serializable_lowering = {
        k: (v.tolist() if isinstance(v, np.ndarray) else v)
        for k, v in source_lowering.items()
        if k != "H"
    }

    return {
        "format": "tw1-manifest-v0.1",
        "program": program.name,
        "steps": program.steps,
        "dt": program.dt,
        "backend": "tw1-clocked-mixed-signal",
        "source_lowering": serializable_lowering,
        "recurrence": "z[n+1] = Q z[n] - z[n-1] + source[n]",
        "Q": Q.tolist(),
        "initial_state": z0.tolist(),
        "initial_previous": zprev.tolist(),
        "gauge": gauge,
        "ports": compiled_ports,
        "objective": objective,
        "trainable_edges": trainable,
        "node_map": node_map,
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
            "source_operator_asymmetry": float(source_lowering["source_operator_asymmetry"]),
            "compiled_operator_asymmetry": asym_q,
            "note": "logical backend only; physical routing and coefficient quantization are later passes",
        },
    }


def compile_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return compile_program(program_from_dict(data))


def simulate_source(program: Program) -> np.ndarray:
    """Reference source-domain state history, including state index 0."""
    n = program.state.nodes
    if program.dynamics.form == "reversible_second_order":
        M = _matrix(program.dynamics.Q, n, "Q")
        a = 1.0
        drive_scale = 1.0
    else:
        low = _lower_source_recurrence(program)
        M = np.asarray(low["M"], dtype=float)
        a = float(low["a"])
        drive_scale = float(low["drive_scale"])

    x_prev = np.asarray(program.state.initial_previous, dtype=float).copy()
    x = np.asarray(program.state.initial, dtype=float).copy()
    hist = [x.copy()]
    drives = [
        (_port_vector(program, p), _waveform(p.waveform, program.steps))
        for p in program.ports
        if p.kind == "drive"
    ]
    for k in range(program.steps):
        source = np.zeros(n, dtype=float)
        for b, w in drives:
            source += b * (drive_scale * w[k])
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
    drives = [
        (np.asarray(p["vector"], dtype=float), np.asarray(p["compiled_waveform"], dtype=float))
        for p in man["ports"]
        if p["kind"] == "drive"
    ]
    for k in range(program.steps):
        source = np.zeros(program.state.nodes, dtype=float)
        for b, w in drives:
            source += b * w[k]
        nxt = Q @ z - z_prev + source
        z_prev, z = z, nxt
        hist.append(z.copy())
    return np.asarray(hist)
