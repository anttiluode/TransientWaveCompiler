"""Tune resonator detuning and couplings of the published three-resonator filter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from transientwave.coupled_resonator_filter import (
    MatrixParameter,
    magnitude_response_loss_and_parameter_gradient,
    matrix_from_parameters,
    response_error_metrics,
    scattering,
)


PARAMETERS = [
    MatrixParameter(0, 0, "d1"),
    MatrixParameter(1, 1, "d2"),
    MatrixParameter(2, 2, "d3"),
    MatrixParameter(0, 1, "m12"),
    MatrixParameter(1, 2, "m23"),
    MatrixParameter(0, 2, "m13"),
]
TARGET_VALUES = np.array([0.0, 0.0, 0.0, 0.6, 0.6, 0.2], dtype=float)
TARGET_M = matrix_from_parameters(3, PARAMETERS, TARGET_VALUES)
GAMMA = np.linspace(-2.5, 2.5, 401)
TARGET_S11, TARGET_S21 = scattering(TARGET_M, GAMMA, r_in=1.0, r_out=1.0)
STARTS = {
    "A": np.array([+0.30, -0.20, +0.15, 0.35, 0.82, -0.05], dtype=float),
    "B": np.array([-0.25, +0.35, -0.10, 0.85, 0.35, +0.45], dtype=float),
    "C": np.array([+0.40, +0.10, -0.30, 0.30, 0.30, +0.50], dtype=float),
    "D": np.array([-0.45, +0.20, +0.35, 1.00, 0.75, -0.30], dtype=float),
    "E": np.array([+0.15, -0.40, +0.25, 0.45, 1.00,  0.00], dtype=float),
}
LOWER = np.array([-0.80, -0.80, -0.80, 0.05, 0.05, -0.60], dtype=float)
UPPER = np.array([+0.80, +0.80, +0.80, 1.20, 1.20, +0.80], dtype=float)
ITERATIONS = 1200
LR = 0.025
BETA1 = 0.9
BETA2 = 0.999
EPS = 1e-8


def loss_grad(x: np.ndarray) -> tuple[float, np.ndarray]:
    return magnitude_response_loss_and_parameter_gradient(
        x,
        n=3,
        parameters=PARAMETERS,
        gamma=GAMMA,
        target_s11=TARGET_S11,
        target_s21=TARGET_S21,
        r_in=1.0,
        r_out=1.0,
    )


def optimize(start: np.ndarray) -> tuple[np.ndarray, list[float]]:
    x = np.asarray(start, dtype=float).copy()
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    losses: list[float] = []
    for t in range(1, ITERATIONS + 1):
        loss, grad = loss_grad(x)
        losses.append(float(loss))
        m = BETA1 * m + (1.0 - BETA1) * grad
        v = BETA2 * v + (1.0 - BETA2) * (grad * grad)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        x = np.clip(x - LR * mhat / (np.sqrt(vhat) + EPS), LOWER, UPPER)
        if t == 1 or t % 100 == 0:
            print(
                f"  iter={t:04d} loss={loss:.9e} values="
                + np.array2string(x, precision=6, separator=", "),
                flush=True,
            )
    final_loss, _ = loss_grad(x)
    losses.append(float(final_loss))
    return x, losses


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=sorted(STARTS), required=True)
    a = ap.parse_args()
    start = STARTS[a.start]
    initial_loss, _ = loss_grad(start)
    print(f"start={a.start} initial={start.tolist()} loss={initial_loss:.9e}", flush=True)

    final, losses = optimize(start)
    final_loss = float(losses[-1])
    final_m = matrix_from_parameters(3, PARAMETERS, final)
    metrics = response_error_metrics(final_m, TARGET_M, GAMMA, r_in=1.0, r_out=1.0)
    overall_rmse = float(np.sqrt(np.mean((final - TARGET_VALUES) ** 2)))
    detuning_rmse = float(np.sqrt(np.mean((final[:3] - TARGET_VALUES[:3]) ** 2)))
    coupling_rmse = float(np.sqrt(np.mean((final[3:] - TARGET_VALUES[3:]) ** 2)))
    reduction = float(initial_loss / max(final_loss, 1e-300))
    final_s11, final_s21 = scattering(final_m, GAMMA, r_in=1.0, r_out=1.0)

    response_pass = bool(
        final_loss <= 2e-5
        and reduction >= 1e3
        and metrics["max_s11_magnitude_error"] <= 0.02
        and metrics["max_s21_magnitude_error"] <= 0.02
    )
    knob_pass = bool(
        response_pass
        and overall_rmse <= 0.03
        and detuning_rmse <= 0.03
        and coupling_rmse <= 0.03
    )
    exact = bool(knob_pass and overall_rmse <= 0.01)

    result = {
        "experiment": "published-coupled-filter-v02-six-knob",
        "preregistration": "docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_PREREG.md",
        "source": {
            "authors": "S. Gruszczynski and K. Wincza",
            "journal": "Electronics 11(8), 1250 (2022)",
            "doi": "10.3390/electronics11081250",
        },
        "parameter_order": [p.name for p in PARAMETERS],
        "start_id": a.start,
        "start_values": start.tolist(),
        "target_values": TARGET_VALUES.tolist(),
        "final_values": final.tolist(),
        "initial_response_loss": float(initial_loss),
        "final_response_loss": final_loss,
        "loss_reduction_factor": reduction,
        "overall_parameter_rmse": overall_rmse,
        "detuning_rmse": detuning_rmse,
        "coupling_rmse": coupling_rmse,
        "metrics": metrics,
        "iterations": ITERATIONS,
        "learning_rate": LR,
        "response_pass": response_pass,
        "six_knob_recovery_pass": knob_pass,
        "exact_six_knob_recovery": exact,
        "gamma": GAMMA.tolist(),
        "target_s11_magnitude": np.abs(TARGET_S11).tolist(),
        "target_s21_magnitude": np.abs(TARGET_S21).tolist(),
        "final_s11_magnitude": np.abs(final_s11).tolist(),
        "final_s21_magnitude": np.abs(final_s21).tolist(),
        "loss_trace_every_25": [float(losses[i]) for i in range(0, len(losses), 25)],
    }
    print(
        f"FINAL start={a.start} values={final.tolist()} loss={final_loss:.9e} "
        f"reduction={reduction:.3e} overall_rmse={overall_rmse:.9e} "
        f"detune_rmse={detuning_rmse:.9e} coupling_rmse={coupling_rmse:.9e} "
        f"maxS11={metrics['max_s11_magnitude_error']:.9e} "
        f"maxS21={metrics['max_s21_magnitude_error']:.9e} "
        f"response_pass={response_pass} knob_pass={knob_pass} exact={exact}",
        flush=True,
    )
    Path(f"published-coupled-filter-v02-{a.start}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
