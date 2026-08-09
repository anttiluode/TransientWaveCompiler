"""Typed WaveProgram v0.1 intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StateSpec:
    nodes: int
    initial: tuple[float, ...]
    initial_previous: tuple[float, ...]


@dataclass(frozen=True)
class DynamicsSpec:
    form: str
    a: float | None = None
    M: tuple[tuple[float, ...], ...] | None = None
    Q: tuple[tuple[float, ...], ...] | None = None


@dataclass(frozen=True)
class PortSpec:
    name: str
    kind: str
    node: int | None = None
    sparse_weights: tuple[tuple[int, float], ...] = ()
    waveform: tuple[float, ...] = ()
    gain_limit: float | None = None


@dataclass(frozen=True)
class ObjectiveSpec:
    kind: str
    port: str | None = None
    weight: float = 1.0
    weights: tuple[float, ...] = ()
    epsilon: float = 1e-30


@dataclass(frozen=True)
class TrainableEdgeSpec:
    i: int
    j: int
    minimum: float
    maximum: float
    matrix_scale: float
    group: str = "default"


@dataclass(frozen=True)
class ConstraintsSpec:
    stability_margin: float = 1e-3
    max_boundary_gain: float = 8.0
    max_operator_asymmetry: float = 1e-10
    require_reciprocal: bool = True
    max_nodes: int | None = None
    max_edges: int | None = None
    max_ports: int | None = None
    allow_partition: bool = False


@dataclass(frozen=True)
class Program:
    name: str
    version: int
    dt: float
    steps: int
    state: StateSpec
    dynamics: DynamicsSpec
    ports: tuple[PortSpec, ...]
    objective: ObjectiveSpec
    trainable_edges: tuple[TrainableEdgeSpec, ...] = ()
    constraints: ConstraintsSpec = field(default_factory=ConstraintsSpec)
    metadata: dict[str, Any] = field(default_factory=dict)


def _vec(x: Any, name: str) -> tuple[float, ...]:
    if not isinstance(x, list):
        raise ValueError(f"{name} must be a JSON list")
    return tuple(float(v) for v in x)


def _matrix(x: Any, name: str) -> tuple[tuple[float, ...], ...]:
    if not isinstance(x, list) or not x:
        raise ValueError(f"{name} must be a non-empty JSON matrix")
    return tuple(_vec(row, f"{name} row") for row in x)


def program_from_dict(d: dict[str, Any]) -> Program:
    """Parse the intentionally small WaveProgram v0.1 JSON object."""
    if not isinstance(d, dict):
        raise ValueError("program root must be a JSON object")

    name = str(d.get("name", "unnamed"))
    version = int(d.get("version", 1))
    if version != 1:
        raise ValueError(f"unsupported WaveProgram version {version}")

    dt = float(d.get("dt", 1.0))
    steps = int(d["steps"])
    if dt <= 0 or steps <= 0:
        raise ValueError("dt and steps must be positive")

    sd = d["state"]
    nodes = int(sd["nodes"])
    if nodes <= 0:
        raise ValueError("state.nodes must be positive")
    initial = _vec(sd.get("initial", [0.0] * nodes), "state.initial")
    initial_previous = _vec(
        sd.get("initial_previous", [0.0] * nodes), "state.initial_previous"
    )
    if len(initial) != nodes or len(initial_previous) != nodes:
        raise ValueError("initial state vectors must have state.nodes entries")
    state = StateSpec(nodes, initial, initial_previous)

    dd = d["dynamics"]
    form = str(dd["form"])
    if form == "damped_second_order":
        dynamics = DynamicsSpec(form=form, a=float(dd["a"]), M=_matrix(dd["M"], "dynamics.M"))
    elif form == "reversible_second_order":
        dynamics = DynamicsSpec(form=form, Q=_matrix(dd["Q"], "dynamics.Q"))
    else:
        raise ValueError(f"unsupported dynamics form {form!r}")

    ports: list[PortSpec] = []
    for pd in d.get("ports", []):
        sparse = tuple((int(i), float(w)) for i, w in pd.get("sparse_weights", []))
        node = pd.get("node")
        ports.append(
            PortSpec(
                name=str(pd["name"]),
                kind=str(pd["kind"]),
                node=None if node is None else int(node),
                sparse_weights=sparse,
                waveform=_vec(pd.get("waveform", []), f"port {pd['name']} waveform"),
                gain_limit=None if pd.get("gain_limit") is None else float(pd["gain_limit"]),
            )
        )

    od = d.get("objective", {"kind": "quadratic_energy"})
    objective = ObjectiveSpec(
        kind=str(od["kind"]),
        port=od.get("port"),
        weight=float(od.get("weight", 1.0)),
        weights=_vec(od.get("weights", []), "objective.weights"),
        epsilon=float(od.get("epsilon", 1e-30)),
    )

    edges: list[TrainableEdgeSpec] = []
    for ed in d.get("trainable_edges", []):
        edges.append(
            TrainableEdgeSpec(
                i=int(ed["i"]),
                j=int(ed["j"]),
                minimum=float(ed.get("min", float("-inf"))),
                maximum=float(ed.get("max", float("inf"))),
                matrix_scale=float(ed["matrix_scale"]),
                group=str(ed.get("group", "default")),
            )
        )

    cd = d.get("constraints", {})
    constraints = ConstraintsSpec(
        stability_margin=float(cd.get("stability_margin", 1e-3)),
        max_boundary_gain=float(cd.get("max_boundary_gain", 8.0)),
        max_operator_asymmetry=float(cd.get("max_operator_asymmetry", 1e-10)),
        require_reciprocal=bool(cd.get("require_reciprocal", True)),
        max_nodes=None if cd.get("max_nodes") is None else int(cd["max_nodes"]),
        max_edges=None if cd.get("max_edges") is None else int(cd["max_edges"]),
        max_ports=None if cd.get("max_ports") is None else int(cd["max_ports"]),
        allow_partition=bool(cd.get("allow_partition", False)),
    )

    return Program(
        name=name,
        version=version,
        dt=dt,
        steps=steps,
        state=state,
        dynamics=dynamics,
        ports=tuple(ports),
        objective=objective,
        trainable_edges=tuple(edges),
        constraints=constraints,
        metadata=dict(d.get("metadata", {})),
    )
