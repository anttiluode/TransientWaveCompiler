"""Compare naive and nuisance-aware tuning under systematic measurement mismatch."""
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
    TARGET_VALUES,
    UPPER,
)
from transientwave.generalized_coupling_matrix import complex_response_loss_and_gradient
from transientwave.measurement_aware_filter import (
    measurement_aware_loss_and_gradient,
    measurement_aware_response,
    wrap_phase_error,
)


ALLOWED_STARTS = ["A", "C", "D"]
LOSS_TARGET = 0.020
SWEEPS = 8
AMP_SIGMA = 0.005
PHASE_SIGMA_RAD = np.deg2rad(0.5)
NAIVE_ITERATIONS = 1600
NAIVE_LR = 0.015
AWARE_ITERATIONS = 3000
AWARE_LR = 0.010
NUISANCE = {
    4200: (np.deg2rad(+5.0), +0.020, np.deg2rad(-7.0), -0.015),
    4201: (np.deg2rad(-9.0), +0.035, np.deg2rad(+4.0), -0.025),
    4202: (np.deg2rad(+12.0), -0.030, np.deg2rad(-11.0), +0.040),
    4203: (np.deg2rad(-6.0), -0.045, np.deg2rad(+10.0), +0.030),
    4204: (np.deg2rad(+8.0), +0.050, np.deg2rad(-5.0), -0.045),
}


def noisy_average(clean: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    acc = np.zeros_like(clean, dtype=complex)
    for _ in range(SWEEPS):
        amp = 1.0 + rng.normal(0.0, AMP_SIGMA, size=clean.shape)
        phase = rng.normal(0.0, PHASE_SIGMA_RAD, size=clean.shape)
        acc += clean * amp * np.exp(1j * phase)
    return acc / float(SWEEPS)


def true_systematic(seed: int) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float, float]]:
    phi11, tau11, phi21, tau21 = NUISANCE[int(seed)]
    s11, s21 = measurement_aware_response(
        TARGET_VALUES,
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        resonator_loss=LOSS_TARGET,
        phi11=phi11,
        tau11=tau11,
        phi21=phi21,
        tau21=tau21,
    )
    return s11, s21, (phi11, tau11, phi21, tau21)


def make_measurement(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[float, float, float, float]]:
    clean11, clean21, nuisance = true_systematic(seed)
    root = np.random.SeedSequence(int(seed))
    a, b = root.spawn(2)
    return (
        noisy_average(clean11, np.random.default_rng(a)),
        noisy_average(clean21, np.random.default_rng(b)),
        clean11,
        clean21,
        nuisance,
    )


def adam_optimize(x0, lower, upper, iterations, lr, objective):
    x = np.asarray(x0, dtype=float).copy()
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    trace = []
    for t in range(1, int(iterations) + 1):
        loss, grad = objective(x)
        trace.append(float(loss))
        m = BETA1 * m + (1.0 - BETA1) * grad
        v = BETA2 * v + (1.0 - BETA2) * (grad * grad)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        x = np.clip(x - float(lr) * mhat / (np.sqrt(vhat) + EPS), lower, upper)
        if t == 1 or t % 400 == 0:
            print(f"    iter={t:04d} loss={loss:.9e}", flush=True)
    final_loss, _ = objective(x)
    trace.append(float(final_loss))
    return x, trace


def matrix_score(values: np.ndarray) -> dict:
    d = values - TARGET_VALUES
    return {
        "matrix_overall_rmse": float(np.sqrt(np.mean(d * d))),
        "main_path_rmse": float(np.sqrt(np.mean(d[:5] * d[:5]))),
        "cross_coupling_abs_error": float(abs(d[5])),
        "source_load_abs_error": float(abs(d[6])),
    }


def run_naive(start: np.ndarray, measured11: np.ndarray, measured21: np.ndarray) -> dict:
    def objective(x):
        return complex_response_loss_and_gradient(
            x,
            n=6,
            parameters=PARAMETERS,
            omega=OMEGA,
            target_s11=measured11,
            target_s21=measured21,
        )

    final, trace = adam_optimize(start, LOWER, UPPER, NAIVE_ITERATIONS, NAIVE_LR, objective)
    score = matrix_score(final)
    matrix_clause = bool(
        score["matrix_overall_rmse"] <= 0.010
        and score["main_path_rmse"] <= 0.010
        and score["cross_coupling_abs_error"] <= 0.010
        and score["source_load_abs_error"] <= 0.0005
    )
    return {
        "final_values": final.tolist(),
        "final_noisy_fit_loss": float(trace[-1]),
        **score,
        "matrix_clause": matrix_clause,
        "iterations": NAIVE_ITERATIONS,
        "learning_rate": NAIVE_LR,
        "loss_trace_every_50": [float(trace[i]) for i in range(0, len(trace), 50)],
    }


def run_aware(
    start: np.ndarray,
    measured11: np.ndarray,
    measured21: np.ndarray,
    clean11: np.ndarray,
    clean21: np.ndarray,
    truth: tuple[float, float, float, float],
) -> dict:
    x0 = np.concatenate([start, np.array([0.010, 0.0, 0.0, 0.0, 0.0])])
    lower = np.concatenate([LOWER, np.array([0.0, -np.pi / 2, -0.10, -np.pi / 2, -0.10])])
    upper = np.concatenate([UPPER, np.array([0.080, +np.pi / 2, +0.10, +np.pi / 2, +0.10])])

    def objective(x):
        return measurement_aware_loss_and_gradient(
            x,
            n=6,
            parameters=PARAMETERS,
            omega=OMEGA,
            measured_s11=measured11,
            measured_s21=measured21,
        )

    final, trace = adam_optimize(x0, lower, upper, AWARE_ITERATIONS, AWARE_LR, objective)
    matrix_values = final[:7]
    loss_value, phi11, tau11, phi21, tau21 = map(float, final[7:])
    score = matrix_score(matrix_values)
    true_phi11, true_tau11, true_phi21, true_tau21 = truth
    pred11, pred21 = measurement_aware_response(
        matrix_values,
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        resonator_loss=loss_value,
        phi11=phi11,
        tau11=tau11,
        phi21=phi21,
        tau21=tau21,
    )
    e11 = pred11 - clean11
    e21 = pred21 - clean21
    hidden_mse = float(np.mean(np.abs(e11) ** 2 + np.abs(e21) ** 2))
    max11 = float(np.max(np.abs(e11)))
    max21 = float(np.max(np.abs(e21)))
    phi11_error = abs(wrap_phase_error(phi11, true_phi11))
    phi21_error = abs(wrap_phase_error(phi21, true_phi21))
    tau11_error = abs(tau11 - true_tau11)
    tau21_error = abs(tau21 - true_tau21)
    lambda_error = abs(loss_value - LOSS_TARGET)
    aware_clause = bool(
        score["matrix_overall_rmse"] <= 0.010
        and score["main_path_rmse"] <= 0.010
        and score["cross_coupling_abs_error"] <= 0.010
        and score["source_load_abs_error"] <= 0.0005
        and lambda_error <= 0.005
        and phi11_error <= np.deg2rad(2.0)
        and phi21_error <= np.deg2rad(2.0)
        and tau11_error <= 0.005
        and tau21_error <= 0.005
        and hidden_mse <= 5e-5
    )
    return {
        "final_values": matrix_values.tolist(),
        "final_nuisance": {
            "lambda": loss_value,
            "phi11": phi11,
            "tau11": tau11,
            "phi21": phi21,
            "tau21": tau21,
        },
        "final_noisy_fit_loss": float(trace[-1]),
        **score,
        "lambda_abs_error": float(lambda_error),
        "phi11_abs_error_rad": float(phi11_error),
        "phi21_abs_error_rad": float(phi21_error),
        "phi11_abs_error_deg": float(np.rad2deg(phi11_error)),
        "phi21_abs_error_deg": float(np.rad2deg(phi21_error)),
        "tau11_abs_error": float(tau11_error),
        "tau21_abs_error": float(tau21_error),
        "hidden_systematic_response_mse": hidden_mse,
        "hidden_max_complex_s11_error": max11,
        "hidden_max_complex_s21_error": max21,
        "aware_clause": aware_clause,
        "iterations": AWARE_ITERATIONS,
        "learning_rate": AWARE_LR,
        "loss_trace_every_50": [float(trace[i]) for i in range(0, len(trace), 50)],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=ALLOWED_STARTS, required=True)
    ap.add_argument("--nuisance-id", type=int, choices=sorted(NUISANCE), required=True)
    a = ap.parse_args()

    measured11, measured21, clean11, clean21, truth = make_measurement(a.nuisance_id)
    start = STARTS[a.start]
    print(f"start={a.start} nuisance={a.nuisance_id} NAIVE", flush=True)
    naive = run_naive(start, measured11, measured21)
    print(
        f"  naive rmse={naive['matrix_overall_rmse']:.6e} mSLerr={naive['source_load_abs_error']:.6e} "
        f"clause={naive['matrix_clause']}", flush=True
    )
    print(f"start={a.start} nuisance={a.nuisance_id} AWARE", flush=True)
    aware = run_aware(start, measured11, measured21, clean11, clean21, truth)
    print(
        f"  aware rmse={aware['matrix_overall_rmse']:.6e} mSLerr={aware['source_load_abs_error']:.6e} "
        f"lambdaerr={aware['lambda_abs_error']:.6e} phase=({aware['phi11_abs_error_deg']:.3f},{aware['phi21_abs_error_deg']:.3f})deg "
        f"tau=({aware['tau11_abs_error']:.6e},{aware['tau21_abs_error']:.6e}) "
        f"hidden={aware['hidden_systematic_response_mse']:.6e} clause={aware['aware_clause']}",
        flush=True,
    )

    phi11, tau11, phi21, tau21 = truth
    out = {
        "experiment": "published-filter-systematic-nuisance-v05",
        "preregistration": "docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_PREREG.md",
        "start_id": a.start,
        "nuisance_id": int(a.nuisance_id),
        "truth": {
            "matrix_values": TARGET_VALUES.tolist(),
            "lambda": LOSS_TARGET,
            "phi11": float(phi11),
            "tau11": float(tau11),
            "phi21": float(phi21),
            "tau21": float(tau21),
        },
        "measurement": {
            "sweeps": SWEEPS,
            "amplitude_noise_rms_fraction": AMP_SIGMA,
            "phase_noise_rms_degrees": 0.5,
            "rms_complex_s11_noise_about_systematic_target": float(np.sqrt(np.mean(np.abs(measured11-clean11)**2))),
            "rms_complex_s21_noise_about_systematic_target": float(np.sqrt(np.mean(np.abs(measured21-clean21)**2))),
        },
        "naive": naive,
        "aware": aware,
    }
    Path(f"published-filter-systematic-v05-{a.start}-{a.nuisance_id}.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
