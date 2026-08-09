"""Tune the published v0.3 matrix from repeated noisy complex S measurements."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import (
    BETA1,
    BETA2,
    EPS,
    LOWER,
    OMEGA,
    PARAMETERS,
    STARTS,
    TARGET_M,
    TARGET_S11,
    TARGET_S21,
    TARGET_VALUES,
    UPPER,
)
from transientwave.coupled_resonator_filter import matrix_from_parameters
from transientwave.generalized_coupling_matrix import (
    complex_response_loss_and_gradient,
    generalized_response_error_metrics,
)


MEASUREMENT_SEEDS = [4100, 4101, 4102, 4103, 4104]
ALLOWED_STARTS = ["A", "C", "D"]
SWEEPS = 8
AMP_SIGMA = 0.005
PHASE_SIGMA_RAD = np.deg2rad(0.5)
ITERATIONS = 1200
LR = 0.015


def noisy_average(clean: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    acc = np.zeros_like(clean, dtype=complex)
    for _ in range(SWEEPS):
        amp = 1.0 + rng.normal(0.0, AMP_SIGMA, size=clean.shape)
        phase = rng.normal(0.0, PHASE_SIGMA_RAD, size=clean.shape)
        acc += clean * amp * np.exp(1j * phase)
    return acc / float(SWEEPS)


def make_measurement(seed: int) -> tuple[np.ndarray, np.ndarray]:
    # Separate derived streams make S11/S21 draws independent while retaining
    # deterministic measurement reproduction from one frozen benchmark seed.
    root = np.random.SeedSequence(int(seed))
    a, b = root.spawn(2)
    return (
        noisy_average(TARGET_S11, np.random.default_rng(a)),
        noisy_average(TARGET_S21, np.random.default_rng(b)),
    )


def loss_grad(x: np.ndarray, measured_s11: np.ndarray, measured_s21: np.ndarray) -> tuple[float, np.ndarray]:
    return complex_response_loss_and_gradient(
        x,
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        target_s11=measured_s11,
        target_s21=measured_s21,
    )


def optimize(start: np.ndarray, measured_s11: np.ndarray, measured_s21: np.ndarray) -> tuple[np.ndarray, list[float]]:
    x = np.asarray(start, dtype=float).copy()
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    losses: list[float] = []
    for t in range(1, ITERATIONS + 1):
        loss, grad = loss_grad(x, measured_s11, measured_s21)
        losses.append(float(loss))
        m = BETA1 * m + (1.0 - BETA1) * grad
        v = BETA2 * v + (1.0 - BETA2) * (grad * grad)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        x = np.clip(x - LR * mhat / (np.sqrt(vhat) + EPS), LOWER, UPPER)
        if t == 1 or t % 200 == 0:
            print(
                f"  iter={t:04d} noisy_loss={loss:.9e} values="
                + np.array2string(x, precision=7, separator=", "),
                flush=True,
            )
    final_loss, _ = loss_grad(x, measured_s11, measured_s21)
    losses.append(float(final_loss))
    return x, losses


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=ALLOWED_STARTS, required=True)
    ap.add_argument("--measurement-seed", type=int, choices=MEASUREMENT_SEEDS, required=True)
    a = ap.parse_args()

    measured_s11, measured_s21 = make_measurement(a.measurement_seed)
    noise_s11 = float(np.sqrt(np.mean(np.abs(measured_s11 - TARGET_S11) ** 2)))
    noise_s21 = float(np.sqrt(np.mean(np.abs(measured_s21 - TARGET_S21) ** 2)))
    start = STARTS[a.start]
    initial_loss, _ = loss_grad(start, measured_s11, measured_s21)
    print(
        f"start={a.start} meas_seed={a.measurement_seed} "
        f"noise_rms_s11={noise_s11:.9e} noise_rms_s21={noise_s21:.9e} "
        f"initial_noisy_loss={initial_loss:.9e}",
        flush=True,
    )

    final, losses = optimize(start, measured_s11, measured_s21)
    final_noisy_loss = float(losses[-1])
    final_m = matrix_from_parameters(6, PARAMETERS, final)
    clean_metrics = generalized_response_error_metrics(final_m, TARGET_M, OMEGA)
    clean_loss, _ = complex_response_loss_and_gradient(
        final,
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        target_s11=TARGET_S11,
        target_s21=TARGET_S21,
    )
    overall_rmse = float(np.sqrt(np.mean((final - TARGET_VALUES) ** 2)))
    main_rmse = float(np.sqrt(np.mean((final[:5] - TARGET_VALUES[:5]) ** 2)))
    cross_error = float(abs(final[5] - TARGET_VALUES[5]))
    source_load_error = float(abs(final[6] - TARGET_VALUES[6]))

    response_clause = bool(
        clean_loss <= 5e-5
        and clean_metrics["max_complex_s11_error"] <= 0.03
        and clean_metrics["max_complex_s21_error"] <= 0.03
    )
    knob_clause = bool(
        overall_rmse <= 0.015
        and main_rmse <= 0.015
        and cross_error <= 0.015
        and source_load_error <= 0.001
    )

    result = {
        "experiment": "published-filter-noisy-measurement-v04",
        "preregistration": "docs/BENCHMARK_PUBLISHED_FILTER_NOISY_MEASUREMENT_V04_PREREG.md",
        "start_id": a.start,
        "measurement_seed": int(a.measurement_seed),
        "sweeps": SWEEPS,
        "amplitude_noise_rms_fraction": AMP_SIGMA,
        "phase_noise_rms_degrees": 0.5,
        "measured_target_rms_complex_s11_error": noise_s11,
        "measured_target_rms_complex_s21_error": noise_s21,
        "initial_noisy_fit_loss": float(initial_loss),
        "final_noisy_fit_loss": final_noisy_loss,
        "clean_hidden_target_loss": float(clean_loss),
        "target_values": TARGET_VALUES.tolist(),
        "final_values": final.tolist(),
        "overall_parameter_rmse": overall_rmse,
        "main_path_rmse": main_rmse,
        "cross_coupling_abs_error": cross_error,
        "source_load_abs_error": source_load_error,
        "clean_metrics": clean_metrics,
        "response_clause": response_clause,
        "knob_clause": knob_clause,
        "full_run_pass": bool(response_clause and knob_clause),
        "iterations": ITERATIONS,
        "learning_rate": LR,
        "loss_trace_every_50": [float(losses[i]) for i in range(0, len(losses), 50)],
    }
    print(
        f"FINAL start={a.start} meas={a.measurement_seed} values={final.tolist()} "
        f"noisy_loss={final_noisy_loss:.9e} clean_loss={clean_loss:.9e} "
        f"rmse={overall_rmse:.9e} main={main_rmse:.9e} "
        f"m14err={cross_error:.9e} mSLerr={source_load_error:.9e} "
        f"maxCS11={clean_metrics['max_complex_s11_error']:.9e} "
        f"maxCS21={clean_metrics['max_complex_s21_error']:.9e} "
        f"response={response_clause} knob={knob_clause}",
        flush=True,
    )
    Path(f"published-filter-noisy-v04-{a.start}-{a.measurement_seed}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
