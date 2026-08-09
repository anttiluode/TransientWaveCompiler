"""Generic computer-side tuning for explicit-port reciprocal coupling matrices."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from .generalized_coupling_matrix import (
    complex_response_loss_and_gradient,
    generalized_scattering,
)


@dataclass(frozen=True)
class FilterKnob:
    name: str
    i: int
    j: int
    initial: float
    minimum: float
    maximum: float

    def parameter(self) -> MatrixParameter:
        return MatrixParameter(int(self.i), int(self.j), str(self.name))


@dataclass(frozen=True)
class AdamConfig:
    iterations: int = 1200
    learning_rate: float = 0.015
    beta1: float = 0.9
    beta2: float = 0.999
    epsilon: float = 1e-8

    def validate(self) -> None:
        if self.iterations <= 0:
            raise ValueError("optimizer iterations must be positive")
        if self.learning_rate <= 0:
            raise ValueError("optimizer learning_rate must be positive")
        if not (0.0 <= self.beta1 < 1.0 and 0.0 <= self.beta2 < 1.0):
            raise ValueError("Adam beta values must lie in [0,1)")
        if self.epsilon <= 0:
            raise ValueError("optimizer epsilon must be positive")


def _complex_array(obj: Mapping[str, Any], name: str, expected: int) -> np.ndarray:
    if "real" not in obj or "imag" not in obj:
        raise ValueError(f"{name} requires real and imag arrays")
    real = np.asarray(obj["real"], dtype=float)
    imag = np.asarray(obj["imag"], dtype=float)
    if real.shape != (expected,) or imag.shape != (expected,):
        raise ValueError(f"{name} real/imag arrays must have length {expected}")
    if not np.all(np.isfinite(real)) or not np.all(np.isfinite(imag)):
        raise ValueError(f"{name} contains non-finite data")
    return real + 1j * imag


def parse_filter_spec(spec: Mapping[str, Any]) -> tuple[
    int,
    list[FilterKnob],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    AdamConfig,
]:
    model = str(spec.get("model", "explicit-port"))
    if model != "explicit-port":
        raise ValueError("only model='explicit-port' is currently supported")
    nodes = int(spec["nodes"])
    if nodes < 3:
        raise ValueError("explicit-port model requires source, >=1 resonator, and load")

    raw_knobs = spec.get("parameters")
    if not isinstance(raw_knobs, list) or not raw_knobs:
        raise ValueError("parameters must be a non-empty list")
    knobs: list[FilterKnob] = []
    seen_names: set[str] = set()
    seen_entries: set[tuple[int, int]] = set()
    for item in raw_knobs:
        if not isinstance(item, Mapping):
            raise ValueError("each parameter must be an object")
        knob = FilterKnob(
            name=str(item["name"]),
            i=int(item["i"]),
            j=int(item["j"]),
            initial=float(item["initial"]),
            minimum=float(item["min"]),
            maximum=float(item["max"]),
        )
        if not knob.name or knob.name in seen_names:
            raise ValueError(f"parameter names must be unique and non-empty: {knob.name!r}")
        if not (0 <= knob.i < nodes and 0 <= knob.j < nodes):
            raise ValueError(f"parameter {knob.name} endpoint out of range")
        key = tuple(sorted((knob.i, knob.j)))
        if key in seen_entries:
            raise ValueError(f"duplicate reciprocal matrix entry for parameter {knob.name}")
        if not np.isfinite([knob.initial, knob.minimum, knob.maximum]).all():
            raise ValueError(f"parameter {knob.name} contains non-finite bounds/value")
        if knob.minimum > knob.maximum:
            raise ValueError(f"parameter {knob.name} min exceeds max")
        if not (knob.minimum <= knob.initial <= knob.maximum):
            raise ValueError(f"parameter {knob.name} initial value lies outside bounds")
        seen_names.add(knob.name)
        seen_entries.add(key)
        knobs.append(knob)

    omega = np.asarray(spec["omega"], dtype=float)
    if omega.ndim != 1 or len(omega) < 2 or not np.all(np.isfinite(omega)):
        raise ValueError("omega must be a finite one-dimensional array with >=2 samples")
    s11 = _complex_array(spec["s11"], "s11", len(omega))
    s21 = _complex_array(spec["s21"], "s21", len(omega))

    raw_opt = spec.get("optimizer", {})
    if not isinstance(raw_opt, Mapping):
        raise ValueError("optimizer must be an object")
    opt = AdamConfig(
        iterations=int(raw_opt.get("iterations", 1200)),
        learning_rate=float(raw_opt.get("learning_rate", 0.015)),
        beta1=float(raw_opt.get("beta1", 0.9)),
        beta2=float(raw_opt.get("beta2", 0.999)),
        epsilon=float(raw_opt.get("epsilon", 1e-8)),
    )
    opt.validate()
    return nodes, knobs, omega, s11, s21, opt


def tune_filter_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Fit one constrained reciprocal matrix to measured complex S parameters."""
    nodes, knobs, omega, target_s11, target_s21, opt = parse_filter_spec(spec)
    parameters = [k.parameter() for k in knobs]
    x = np.asarray([k.initial for k in knobs], dtype=float)
    lower = np.asarray([k.minimum for k in knobs], dtype=float)
    upper = np.asarray([k.maximum for k in knobs], dtype=float)
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    loss_trace: list[float] = []

    initial_loss, initial_grad = complex_response_loss_and_gradient(
        x,
        n=nodes,
        parameters=parameters,
        omega=omega,
        target_s11=target_s11,
        target_s21=target_s21,
    )

    for t in range(1, opt.iterations + 1):
        loss, grad = complex_response_loss_and_gradient(
            x,
            n=nodes,
            parameters=parameters,
            omega=omega,
            target_s11=target_s11,
            target_s21=target_s21,
        )
        loss_trace.append(float(loss))
        m = opt.beta1 * m + (1.0 - opt.beta1) * grad
        v = opt.beta2 * v + (1.0 - opt.beta2) * (grad * grad)
        mhat = m / (1.0 - opt.beta1 ** t)
        vhat = v / (1.0 - opt.beta2 ** t)
        x = np.clip(
            x - opt.learning_rate * mhat / (np.sqrt(vhat) + opt.epsilon),
            lower,
            upper,
        )

    final_loss, final_grad = complex_response_loss_and_gradient(
        x,
        n=nodes,
        parameters=parameters,
        omega=omega,
        target_s11=target_s11,
        target_s21=target_s21,
    )
    fitted_matrix = matrix_from_parameters(nodes, parameters, x)
    fitted_s11, fitted_s21 = generalized_scattering(fitted_matrix, omega)

    return {
        "name": str(spec.get("name", "filter-fit")),
        "model": "explicit-port",
        "nodes": nodes,
        "parameter_order": [k.name for k in knobs],
        "initial_values": [float(k.initial) for k in knobs],
        "final_values": [float(y) for y in x],
        "parameters": [
            {
                "name": k.name,
                "i": int(k.i),
                "j": int(k.j),
                "initial": float(k.initial),
                "final": float(x[q]),
                "min": float(k.minimum),
                "max": float(k.maximum),
                "initial_gradient": float(initial_grad[q]),
                "final_gradient": float(final_grad[q]),
            }
            for q, k in enumerate(knobs)
        ],
        "initial_loss": float(initial_loss),
        "final_loss": float(final_loss),
        "loss_reduction_factor": float(initial_loss / max(final_loss, 1e-300)),
        "optimizer": {
            "iterations": int(opt.iterations),
            "learning_rate": float(opt.learning_rate),
            "beta1": float(opt.beta1),
            "beta2": float(opt.beta2),
            "epsilon": float(opt.epsilon),
        },
        "matrix": fitted_matrix.tolist(),
        "omega": omega.tolist(),
        "measured_s11": {"real": np.real(target_s11).tolist(), "imag": np.imag(target_s11).tolist()},
        "measured_s21": {"real": np.real(target_s21).tolist(), "imag": np.imag(target_s21).tolist()},
        "fitted_s11": {"real": np.real(fitted_s11).tolist(), "imag": np.imag(fitted_s11).tolist()},
        "fitted_s21": {"real": np.real(fitted_s21).tolist(), "imag": np.imag(fitted_s21).tolist()},
        "loss_trace_every_25": [float(loss_trace[i]) for i in range(0, len(loss_trace), 25)],
    }
