"""Tune a published fourth-order cross-coupled filter with four transmission zeros."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.generalized_coupling_matrix import (
    complex_response_loss_and_gradient,
    generalized_response_error_metrics,
    generalized_scattering,
)


PARAMETERS = [
    MatrixParameter(0, 1, "mS1"),
    MatrixParameter(1, 2, "m12"),
    MatrixParameter(2, 3, "m23"),
    MatrixParameter(3, 4, "m34"),
    MatrixParameter(4, 5, "m4L"),
    MatrixParameter(1, 4, "m14"),
    MatrixParameter(0, 5, "mSL"),
]
TARGET_VALUES = np.array([1.02, -0.86, 0.77, -0.86, 1.02, -0.19, 0.0005], dtype=float)
TARGET_M = matrix_from_parameters(6, PARAMETERS, TARGET_VALUES)
OMEGA = np.unique(
    np.concatenate([np.linspace(-30.0, 30.0, 601), np.linspace(-3.0, 3.0, 601)])
)
TARGET_S11, TARGET_S21 = generalized_scattering(TARGET_M, OMEGA)
STARTS = {
    "A": np.array([0.80, -0.60, 0.95, -1.05, 1.15, -0.05, +0.020], dtype=float),
    "B": np.array([1.18, -1.05, 0.55, -0.65, 0.82, -0.35, -0.015], dtype=float),
    "C": np.array([0.70, -0.45, 0.50, -0.50, 0.75, +0.10, +0.030], dtype=float),
    "D": np.array([1.25, -1.15, 1.00, -1.10, 1.25, -0.40, -0.025], dtype=float),
    "E": np.array([0.92, -0.72, 0.90, -0.73, 1.12,  0.00, +0.010], dtype=float),
}
LOWER = np.array([0.40, -1.50, 0.20, -1.50, 0.40, -0.70, -0.05], dtype=float)
UPPER = np.array([1.50, -0.20, 1.30, -0.20, 1.50, +0.40, +0.05], dtype=float)
ITERATIONS = 2000
LR = 0.015
BETA1 = 0.9
BETA2 = 0.999
EPS = 1e-8


def loss_grad(x: np.ndarray) -> tuple[float, np.ndarray]:
    return complex_response_loss_and_gradient(
        x,
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        target_s11=TARGET_S11,
        target_s21=TARGET_S21,
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
        if t == 1 or t % 200 == 0:
            print(
                f"  iter={t:04d} loss={loss:.9e} values="
                + np.array2string(x, precision=7, separator=", "),
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
    final_m = matrix_from_parameters(6, PARAMETERS, final)
    metrics = generalized_response_error_metrics(final_m, TARGET_M, OMEGA)
    reduction = float(initial_loss / max(final_loss, 1e-300))
    overall_rmse = float(np.sqrt(np.mean((final - TARGET_VALUES) ** 2)))
    main_rmse = float(np.sqrt(np.mean((final[:5] - TARGET_VALUES[:5]) ** 2)))
    cross_error = float(abs(final[5] - TARGET_VALUES[5]))
    source_load_error = float(abs(final[6] - TARGET_VALUES[6]))

    response_pass = bool(
        final_loss <= 1e-6
        and reduction >= 1e4
        and metrics["max_complex_s11_error"] <= 0.01
        and metrics["max_complex_s21_error"] <= 0.01
    )
    knob_pass = bool(
        response_pass
        and overall_rmse <= 0.01
        and main_rmse <= 0.01
        and cross_error <= 0.01
        and source_load_error <= 0.0005
    )
    exact = bool(
        knob_pass and overall_rmse <= 0.003 and source_load_error <= 0.0002
    )
    final_s11, final_s21 = generalized_scattering(final_m, OMEGA)

    result = {
        "experiment": "published-cross-coupled-filter-v03",
        "preregistration": "docs/BENCHMARK_PUBLISHED_CROSS_COUPLED_FILTER_V03_PREREG.md",
        "source": {
            "authors": "Shuang Li, Shengxian Li, Jianrong Yuan",
            "journal": "Electronics 12(11), 2539 (2023)",
            "doi": "10.3390/electronics12112539",
        },
        "parameter_order": [p.name for p in PARAMETERS],
        "start_id": a.start,
        "start_values": start.tolist(),
        "target_values": TARGET_VALUES.tolist(),
        "final_values": final.tolist(),
        "initial_complex_response_loss": float(initial_loss),
        "final_complex_response_loss": final_loss,
        "loss_reduction_factor": reduction,
        "overall_parameter_rmse": overall_rmse,
        "main_path_rmse": main_rmse,
        "cross_coupling_abs_error": cross_error,
        "source_load_abs_error": source_load_error,
        "metrics": metrics,
        "iterations": ITERATIONS,
        "learning_rate": LR,
        "response_pass": response_pass,
        "topology_knob_recovery_pass": knob_pass,
        "exact_cross_coupled_recovery": exact,
        "omega": OMEGA.tolist(),
        "target_s11_real": np.real(TARGET_S11).tolist(),
        "target_s11_imag": np.imag(TARGET_S11).tolist(),
        "target_s21_real": np.real(TARGET_S21).tolist(),
        "target_s21_imag": np.imag(TARGET_S21).tolist(),
        "final_s11_real": np.real(final_s11).tolist(),
        "final_s11_imag": np.imag(final_s11).tolist(),
        "final_s21_real": np.real(final_s21).tolist(),
        "final_s21_imag": np.imag(final_s21).tolist(),
        "loss_trace_every_50": [float(losses[i]) for i in range(0, len(losses), 50)],
    }
    print(
        f"FINAL start={a.start} values={final.tolist()} loss={final_loss:.9e} "
        f"reduction={reduction:.3e} rmse={overall_rmse:.9e} main_rmse={main_rmse:.9e} "
        f"m14err={cross_error:.9e} mSLerr={source_load_error:.9e} "
        f"maxCS11={metrics['max_complex_s11_error']:.9e} "
        f"maxCS21={metrics['max_complex_s21_error']:.9e} "
        f"response_pass={response_pass} knob_pass={knob_pass} exact={exact}",
        flush=True,
    )
    Path(f"published-cross-coupled-filter-v03-{a.start}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
