"""Generic computer-side tuning for explicit-port reciprocal coupling matrices."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from .filter_units import resonator_frequency_diagnosis
from .generalized_coupling_matrix import (
    complex_response_loss_and_gradient,
    generalized_scattering,
)
from .measurement_aware_filter import (
    lossy_scattering_with_derivatives,
    measurement_aware_loss_and_gradient,
    measurement_aware_response,
)


@dataclass(frozen=True)
class FilterKnob:
    name: str
    i: int
    j: int
    initial: float
    minimum: float
    maximum: float
    nominal: float | None = None

    def parameter(self) -> MatrixParameter:
        return MatrixParameter(int(self.i), int(self.j), str(self.name))


@dataclass(frozen=True)
class BoundedScalar:
    name: str
    initial: float
    minimum: float
    maximum: float
    unit: str

    @property
    def free(self) -> bool:
        return self.maximum > self.minimum


@dataclass(frozen=True)
class MeasurementNuisanceConfig:
    resonator_loss: BoundedScalar
    phi11: BoundedScalar
    tau11: BoundedScalar
    phi21: BoundedScalar
    tau21: BoundedScalar

    def ordered(self) -> tuple[BoundedScalar, ...]:
        return (
            self.resonator_loss,
            self.phi11,
            self.tau11,
            self.phi21,
            self.tau21,
        )

    @property
    def enabled(self) -> bool:
        return any(item.free or item.initial != 0.0 for item in self.ordered())


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


def _bounded_scalar(
    raw: Mapping[str, Any],
    name: str,
    *,
    default_initial: float = 0.0,
    default_minimum: float = 0.0,
    default_maximum: float = 0.0,
    unit: str,
    nonnegative: bool = False,
) -> BoundedScalar:
    item = raw.get(name, {})
    if item is None:
        item = {}
    if not isinstance(item, Mapping):
        raise ValueError(f"nuisance.{name} must be an object")
    value = BoundedScalar(
        name=name,
        initial=float(item.get("initial", default_initial)),
        minimum=float(item.get("min", default_minimum)),
        maximum=float(item.get("max", default_maximum)),
        unit=unit,
    )
    if not np.isfinite([value.initial, value.minimum, value.maximum]).all():
        raise ValueError(f"nuisance.{name} contains non-finite bounds/value")
    if value.minimum > value.maximum:
        raise ValueError(f"nuisance.{name} min exceeds max")
    if not (value.minimum <= value.initial <= value.maximum):
        raise ValueError(f"nuisance.{name} initial value lies outside bounds")
    if nonnegative and value.minimum < 0:
        raise ValueError(f"nuisance.{name} must be nonnegative")
    return value


def parse_measurement_nuisance(spec: Mapping[str, Any]) -> MeasurementNuisanceConfig:
    """Parse optional joint measurement/model nuisance parameters.

    Missing nuisance entries are fixed at zero. This keeps existing lossless
    JSON specifications fully backward compatible while allowing any subset of
    the five v0.5 nuisance variables to be fitted.
    """
    raw = spec.get("nuisance", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ValueError("nuisance must be an object")
    allowed = {"resonator_loss", "phi11", "tau11", "phi21", "tau21"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown nuisance field(s): {', '.join(unknown)}")
    return MeasurementNuisanceConfig(
        resonator_loss=_bounded_scalar(
            raw, "resonator_loss", unit="normalized", nonnegative=True
        ),
        phi11=_bounded_scalar(raw, "phi11", unit="radian"),
        tau11=_bounded_scalar(raw, "tau11", unit="radian_per_normalized_omega"),
        phi21=_bounded_scalar(raw, "phi21", unit="radian"),
        tau21=_bounded_scalar(raw, "tau21", unit="radian_per_normalized_omega"),
    )


def _measurement_omega_mapping(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    source = spec.get("measurement_source")
    if not isinstance(source, Mapping):
        return None
    mapping = source.get("omega_mapping")
    if not isinstance(mapping, Mapping):
        return None
    mode = str(mapping.get("mode", ""))
    if mode not in {"linear", "bandpass"}:
        return None
    return dict(mapping)


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
        raw_nominal = item.get("nominal")
        nominal = None if raw_nominal is None else float(raw_nominal)
        knob = FilterKnob(
            name=str(item["name"]),
            i=int(item["i"]),
            j=int(item["j"]),
            initial=float(item["initial"]),
            minimum=float(item["min"]),
            maximum=float(item["max"]),
            nominal=nominal,
        )
        if not knob.name or knob.name in seen_names:
            raise ValueError(f"parameter names must be unique and non-empty: {knob.name!r}")
        if not (0 <= knob.i < nodes and 0 <= knob.j < nodes):
            raise ValueError(f"parameter {knob.name} endpoint out of range")
        key = tuple(sorted((knob.i, knob.j)))
        if key in seen_entries:
            raise ValueError(f"duplicate reciprocal matrix entry for parameter {knob.name}")
        values_to_check = [knob.initial, knob.minimum, knob.maximum]
        if knob.nominal is not None:
            values_to_check.append(knob.nominal)
        if not np.isfinite(values_to_check).all():
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
    parse_measurement_nuisance(spec)
    return nodes, knobs, omega, s11, s21, opt


def _run_adam(
    x: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    opt: AdamConfig,
    objective,
) -> tuple[np.ndarray, float, np.ndarray, float, np.ndarray, list[float]]:
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    loss_trace: list[float] = []
    initial_loss, initial_grad = objective(x)

    for t in range(1, opt.iterations + 1):
        loss, grad = objective(x)
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

    final_loss, final_grad = objective(x)
    return x, float(initial_loss), initial_grad, float(final_loss), final_grad, loss_trace


def _diagnosis(
    knobs: Sequence[FilterKnob],
    fitted: np.ndarray,
    omega_mapping: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for knob, value in zip(knobs, fitted):
        if knob.nominal is None:
            continue
        delta = float(value - knob.nominal)
        relative_percent = None
        if abs(knob.nominal) > 1e-15:
            relative_percent = float(100.0 * delta / knob.nominal)
        is_resonator = knob.i == knob.j
        row: dict[str, Any] = {
            "name": knob.name,
            "i": int(knob.i),
            "j": int(knob.j),
            "kind": "resonator_detuning" if is_resonator else "reciprocal_coupling",
            "nominal": float(knob.nominal),
            "fitted": float(value),
            "deviation_normalized": delta,
            "deviation_percent": relative_percent,
        }
        if is_resonator:
            row.update(
                resonator_frequency_diagnosis(
                    float(knob.nominal),
                    float(value),
                    omega_mapping,
                )
            )
        rows.append(row)
    return rows


def tune_filter_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Fit one constrained reciprocal matrix to measured complex S parameters.

    If ``spec["nuisance"]`` is absent, this is the original lossless fitter.
    If nuisance fields are supplied, the physical matrix is optimized jointly
    with uniform resonator loss and/or S11/S21 linear phase nuisance.

    Optional per-knob ``nominal`` values do not affect optimization. They turn
    the recovered matrix into a diagnosis relative to the intended design.
    """
    nodes, knobs, omega, target_s11, target_s21, opt = parse_filter_spec(spec)
    nuisance = parse_measurement_nuisance(spec)
    parameters = [k.parameter() for k in knobs]
    matrix_initial = np.asarray([k.initial for k in knobs], dtype=float)
    matrix_lower = np.asarray([k.minimum for k in knobs], dtype=float)
    matrix_upper = np.asarray([k.maximum for k in knobs], dtype=float)

    nuisance_items = nuisance.ordered()
    if nuisance.enabled:
        x0 = np.concatenate(
            [matrix_initial, np.asarray([item.initial for item in nuisance_items], dtype=float)]
        )
        lower = np.concatenate(
            [matrix_lower, np.asarray([item.minimum for item in nuisance_items], dtype=float)]
        )
        upper = np.concatenate(
            [matrix_upper, np.asarray([item.maximum for item in nuisance_items], dtype=float)]
        )

        def objective(x: np.ndarray):
            return measurement_aware_loss_and_gradient(
                x,
                n=nodes,
                parameters=parameters,
                omega=omega,
                measured_s11=target_s11,
                measured_s21=target_s21,
            )

        x, initial_loss, initial_grad, final_loss, final_grad, loss_trace = _run_adam(
            x0, lower, upper, opt=opt, objective=objective
        )
        matrix_values = x[: len(knobs)]
        nuisance_values = x[len(knobs):]
        fitted_s11, fitted_s21 = measurement_aware_response(
            matrix_values,
            n=nodes,
            parameters=parameters,
            omega=omega,
            resonator_loss=float(nuisance_values[0]),
            phi11=float(nuisance_values[1]),
            tau11=float(nuisance_values[2]),
            phi21=float(nuisance_values[3]),
            tau21=float(nuisance_values[4]),
        )
        physical_s11, physical_s21, *_ = lossy_scattering_with_derivatives(
            matrix_from_parameters(nodes, parameters, matrix_values),
            omega,
            parameters,
            float(nuisance_values[0]),
        )
    else:
        x0 = matrix_initial.copy()

        def objective(x: np.ndarray):
            return complex_response_loss_and_gradient(
                x,
                n=nodes,
                parameters=parameters,
                omega=omega,
                target_s11=target_s11,
                target_s21=target_s21,
            )

        matrix_values, initial_loss, initial_grad, final_loss, final_grad, loss_trace = _run_adam(
            x0, matrix_lower, matrix_upper, opt=opt, objective=objective
        )
        nuisance_values = np.zeros(5, dtype=float)
        fitted_matrix_lossless = matrix_from_parameters(nodes, parameters, matrix_values)
        fitted_s11, fitted_s21 = generalized_scattering(fitted_matrix_lossless, omega)
        physical_s11, physical_s21 = fitted_s11, fitted_s21

    fitted_matrix = matrix_from_parameters(nodes, parameters, matrix_values)
    p = len(knobs)
    nuisance_initial_grad = initial_grad[p:] if nuisance.enabled else np.zeros(5, dtype=float)
    nuisance_final_grad = final_grad[p:] if nuisance.enabled else np.zeros(5, dtype=float)
    omega_mapping = _measurement_omega_mapping(spec)
    diagnosis = _diagnosis(knobs, matrix_values, omega_mapping)

    return {
        "name": str(spec.get("name", "filter-fit")),
        "model": "explicit-port",
        "nodes": nodes,
        "measurement_model": "joint-nuisance" if nuisance.enabled else "lossless",
        "measurement_source": spec.get("measurement_source"),
        "parameter_order": [k.name for k in knobs],
        "initial_values": [float(k.initial) for k in knobs],
        "final_values": [float(y) for y in matrix_values],
        "parameters": [
            {
                "name": k.name,
                "i": int(k.i),
                "j": int(k.j),
                "initial": float(k.initial),
                "final": float(matrix_values[q]),
                "nominal": None if k.nominal is None else float(k.nominal),
                "deviation_from_nominal": None if k.nominal is None else float(matrix_values[q] - k.nominal),
                "min": float(k.minimum),
                "max": float(k.maximum),
                "initial_gradient": float(initial_grad[q]),
                "final_gradient": float(final_grad[q]),
            }
            for q, k in enumerate(knobs)
        ],
        "diagnosis": diagnosis,
        "nuisance": {
            "enabled": bool(nuisance.enabled),
            "order": [item.name for item in nuisance_items],
            "parameters": [
                {
                    "name": item.name,
                    "initial": float(item.initial),
                    "final": float(nuisance_values[q]),
                    "min": float(item.minimum),
                    "max": float(item.maximum),
                    "unit": item.unit,
                    "free": bool(item.free),
                    "initial_gradient": float(nuisance_initial_grad[q]),
                    "final_gradient": float(nuisance_final_grad[q]),
                }
                for q, item in enumerate(nuisance_items)
            ],
        },
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
        "physical_s11": {
            "real": np.real(physical_s11).tolist(),
            "imag": np.imag(physical_s11).tolist(),
        },
        "physical_s21": {
            "real": np.real(physical_s21).tolist(),
            "imag": np.imag(physical_s21).tolist(),
        },
        "loss_trace_every_25": [float(loss_trace[i]) for i in range(0, len(loss_trace), 25)],
    }
