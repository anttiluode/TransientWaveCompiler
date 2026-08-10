"""Preregistered residual-driven discovery of one hidden reciprocal filter edge."""
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
from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.measurement_aware_filter import (
    measurement_aware_loss_and_gradient,
    measurement_aware_response,
    wrap_phase_error,
)
from transientwave.topology_discovery import score_missing_reciprocal_edges


ALLOWED_STARTS = ["A", "C", "D"]
LOSS_TARGET = 0.020
SWEEPS = 8
AMP_SIGMA = 0.005
PHASE_SIGMA_RAD = np.deg2rad(0.5)
ITERATIONS = 3000
LR = 0.010
PROBE_BOUND = 0.12

# case: ((i,j), hidden_value, (phi11, tau11, phi21, tau21))
CASES = {
    4300: ((0, 2), +0.030, (np.deg2rad(+5.0), +0.020, np.deg2rad(-7.0), -0.015)),
    4301: ((1, 3), -0.040, (np.deg2rad(-9.0), +0.035, np.deg2rad(+4.0), -0.025)),
    4302: ((2, 4), +0.035, (np.deg2rad(+12.0), -0.030, np.deg2rad(-11.0), +0.040)),
    4303: ((2, 5), -0.025, (np.deg2rad(-6.0), -0.045, np.deg2rad(+10.0), +0.030)),
    4304: ((0, 4), +0.020, (np.deg2rad(+8.0), +0.050, np.deg2rad(-5.0), -0.045)),
}

NUISANCE_LOWER = np.array([0.0, -np.pi / 2, -0.10, -np.pi / 2, -0.10], dtype=float)
NUISANCE_UPPER = np.array([0.080, +np.pi / 2, +0.10, +np.pi / 2, +0.10], dtype=float)
NUISANCE_INITIAL = np.array([0.010, 0.0, 0.0, 0.0, 0.0], dtype=float)


def noisy_average(clean: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    acc = np.zeros_like(clean, dtype=complex)
    for _ in range(SWEEPS):
        amp = 1.0 + rng.normal(0.0, AMP_SIGMA, size=clean.shape)
        phase = rng.normal(0.0, PHASE_SIGMA_RAD, size=clean.shape)
        acc += clean * amp * np.exp(1j * phase)
    return acc / float(SWEEPS)


def make_measurement(case_id: int):
    edge, hidden_value, nuisance = CASES[int(case_id)]
    hidden_parameter = MatrixParameter(edge[0], edge[1], f"hidden_m{edge[0]}{edge[1]}")
    true_parameters = [*PARAMETERS, hidden_parameter]
    true_values = np.concatenate([TARGET_VALUES, np.asarray([hidden_value], dtype=float)])
    phi11, tau11, phi21, tau21 = nuisance
    clean11, clean21 = measurement_aware_response(
        true_values,
        n=6,
        parameters=true_parameters,
        omega=OMEGA,
        resonator_loss=LOSS_TARGET,
        phi11=phi11,
        tau11=tau11,
        phi21=phi21,
        tau21=tau21,
    )
    root = np.random.SeedSequence(int(case_id))
    a, b = root.spawn(2)
    measured11 = noisy_average(clean11, np.random.default_rng(a))
    measured21 = noisy_average(clean21, np.random.default_rng(b))
    return measured11, measured21, clean11, clean21, hidden_parameter, hidden_value, nuisance


def adam_optimize(x0, lower, upper, objective, label: str):
    x = np.asarray(x0, dtype=float).copy()
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    trace: list[float] = []
    for t in range(1, ITERATIONS + 1):
        loss, grad = objective(x)
        trace.append(float(loss))
        m = BETA1 * m + (1.0 - BETA1) * grad
        v = BETA2 * v + (1.0 - BETA2) * (grad * grad)
        mhat = m / (1.0 - BETA1 ** t)
        vhat = v / (1.0 - BETA2 ** t)
        x = np.clip(x - LR * mhat / (np.sqrt(vhat) + EPS), lower, upper)
        if t == 1 or t % 600 == 0:
            print(f"  {label} iter={t:04d} loss={loss:.9e}", flush=True)
    final_loss, _ = objective(x)
    trace.append(float(final_loss))
    return x, trace


def stage1_fit(start, measured11, measured21):
    x0 = np.concatenate([np.asarray(start, dtype=float), NUISANCE_INITIAL])
    lower = np.concatenate([LOWER, NUISANCE_LOWER])
    upper = np.concatenate([UPPER, NUISANCE_UPPER])

    def objective(x):
        return measurement_aware_loss_and_gradient(
            x,
            n=6,
            parameters=PARAMETERS,
            omega=OMEGA,
            measured_s11=measured11,
            measured_s21=measured21,
        )

    return adam_optimize(x0, lower, upper, objective, "stage1")


def stage3_fit(stage1, selected: MatrixParameter, proposed, measured11, measured21):
    parameters = [*PARAMETERS, selected]
    x0 = np.concatenate([stage1[:7], np.asarray([proposed], dtype=float), stage1[7:]])
    lower = np.concatenate([LOWER, np.asarray([-PROBE_BOUND]), NUISANCE_LOWER])
    upper = np.concatenate([UPPER, np.asarray([+PROBE_BOUND]), NUISANCE_UPPER])

    def objective(x):
        return measurement_aware_loss_and_gradient(
            x,
            n=6,
            parameters=parameters,
            omega=OMEGA,
            measured_s11=measured11,
            measured_s21=measured21,
        )

    final, trace = adam_optimize(x0, lower, upper, objective, "stage3")
    return parameters, final, trace


def matrix_rmse(values):
    d = np.asarray(values, dtype=float) - TARGET_VALUES
    return float(np.sqrt(np.mean(d * d)))


def nuisance_errors(values, truth):
    loss_value, phi11, tau11, phi21, tau21 = map(float, values)
    true_phi11, true_tau11, true_phi21, true_tau21 = truth
    return {
        "lambda_abs_error": float(abs(loss_value - LOSS_TARGET)),
        "phi11_abs_error_rad": float(abs(wrap_phase_error(phi11, true_phi11))),
        "phi21_abs_error_rad": float(abs(wrap_phase_error(phi21, true_phi21))),
        "phi11_abs_error_deg": float(np.rad2deg(abs(wrap_phase_error(phi11, true_phi11)))),
        "phi21_abs_error_deg": float(np.rad2deg(abs(wrap_phase_error(phi21, true_phi21)))),
        "tau11_abs_error": float(abs(tau11 - true_tau11)),
        "tau21_abs_error": float(abs(tau21 - true_tau21)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=ALLOWED_STARTS, required=True)
    ap.add_argument("--case", type=int, choices=sorted(CASES), required=True)
    a = ap.parse_args()

    measured11, measured21, clean11, clean21, hidden_parameter, hidden_value, truth_nuisance = make_measurement(a.case)
    true_edge = tuple(sorted((hidden_parameter.i, hidden_parameter.j)))
    print(
        f"case={a.case} start={a.start} hidden_edge={true_edge} hidden_value={hidden_value:+.6f}",
        flush=True,
    )

    stage1, stage1_trace = stage1_fit(STARTS[a.start], measured11, measured21)
    stage1_rmse = matrix_rmse(stage1[:7])
    print(
        f"  stage1 loss={stage1_trace[-1]:.9e} matrix_rmse={stage1_rmse:.6e}",
        flush=True,
    )

    nuisance1 = stage1[7:]
    scores = score_missing_reciprocal_edges(
        stage1[:7],
        n=6,
        parameters=PARAMETERS,
        omega=OMEGA,
        measured_s11=measured11,
        measured_s21=measured21,
        resonator_loss=float(nuisance1[0]),
        phi11=float(nuisance1[1]),
        tau11=float(nuisance1[2]),
        phi21=float(nuisance1[3]),
        tau21=float(nuisance1[4]),
        max_abs_probe=PROBE_BOUND,
    )
    ranking = [(score.i, score.j) for score in scores]
    true_rank = ranking.index(true_edge) + 1
    selected_score = scores[0]
    selected_edge = (selected_score.i, selected_score.j)
    selected = MatrixParameter(selected_score.i, selected_score.j, f"candidate_m{selected_score.i}{selected_score.j}")
    print(
        f"  ranking top3={ranking[:3]} true_rank={true_rank} "
        f"selected={selected_edge} proposed={selected_score.proposed_value:+.6f} "
        f"probe_reduction={selected_score.relative_loss_reduction:+.4%}",
        flush=True,
    )

    augmented_parameters, stage3, stage3_trace = stage3_fit(
        stage1,
        selected,
        selected_score.proposed_value,
        measured11,
        measured21,
    )
    stage3_base_rmse = matrix_rmse(stage3[:7])
    selected_value = float(stage3[7])
    selected_is_true = bool(selected_edge == true_edge)
    parasitic_error = float(abs(selected_value - hidden_value)) if selected_is_true else float("inf")
    nuisance3 = stage3[8:]
    nerr = nuisance_errors(nuisance3, truth_nuisance)

    pred11, pred21 = measurement_aware_response(
        stage3[:8],
        n=6,
        parameters=augmented_parameters,
        omega=OMEGA,
        resonator_loss=float(nuisance3[0]),
        phi11=float(nuisance3[1]),
        tau11=float(nuisance3[2]),
        phi21=float(nuisance3[3]),
        tau21=float(nuisance3[4]),
    )
    hidden_mse = float(np.mean(np.abs(pred11 - clean11) ** 2 + np.abs(pred21 - clean21) ** 2))
    top1_clause = bool(true_rank == 1)
    top3_clause = bool(true_rank <= 3)
    recovery_clause = bool(
        selected_is_true
        and stage3_base_rmse <= 0.010
        and parasitic_error <= 0.005
        and nerr["lambda_abs_error"] <= 0.005
        and nerr["phi11_abs_error_deg"] <= 2.0
        and nerr["phi21_abs_error_deg"] <= 2.0
        and nerr["tau11_abs_error"] <= 0.005
        and nerr["tau21_abs_error"] <= 0.005
        and hidden_mse <= 5e-5
        and stage3_trace[-1] < stage1_trace[-1]
    )
    print(
        f"  stage3 loss={stage3_trace[-1]:.9e} base_rmse={stage3_base_rmse:.6e} "
        f"selected_value={selected_value:+.6f} hidden_mse={hidden_mse:.6e} "
        f"TOP1={top1_clause} TOP3={top3_clause} RECOVERY={recovery_clause}",
        flush=True,
    )

    out = {
        "experiment": "published-filter-parasitic-topology-v06",
        "preregistration": "docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_PREREG.md",
        "case_id": int(a.case),
        "start_id": a.start,
        "truth": {
            "base_matrix_values": TARGET_VALUES.tolist(),
            "hidden_edge": list(true_edge),
            "hidden_edge_value": float(hidden_value),
            "lambda": LOSS_TARGET,
            "phi11": float(truth_nuisance[0]),
            "tau11": float(truth_nuisance[1]),
            "phi21": float(truth_nuisance[2]),
            "tau21": float(truth_nuisance[3]),
        },
        "measurement": {
            "sweeps": SWEEPS,
            "amplitude_noise_rms_fraction": AMP_SIGMA,
            "phase_noise_rms_degrees": 0.5,
            "rms_complex_s11_noise_about_systematic_target": float(np.sqrt(np.mean(np.abs(measured11-clean11)**2))),
            "rms_complex_s21_noise_about_systematic_target": float(np.sqrt(np.mean(np.abs(measured21-clean21)**2))),
        },
        "stage1_wrong_topology": {
            "matrix_values": stage1[:7].tolist(),
            "nuisance_values": stage1[7:].tolist(),
            "matrix_rmse": stage1_rmse,
            "measured_fit_loss": float(stage1_trace[-1]),
            "loss_trace_every_100": [float(stage1_trace[i]) for i in range(0, len(stage1_trace), 100)],
        },
        "discovery": {
            "true_edge_rank": int(true_rank),
            "top1_clause": top1_clause,
            "top3_clause": top3_clause,
            "selected_edge": list(selected_edge),
            "selected_probe_value": float(selected_score.proposed_value),
            "scores": [score.as_dict() for score in scores],
        },
        "stage3_augmented": {
            "selected_edge_is_true": selected_is_true,
            "base_matrix_values": stage3[:7].tolist(),
            "selected_edge_value": selected_value,
            "base_matrix_rmse": stage3_base_rmse,
            "parasitic_abs_error": parasitic_error if np.isfinite(parasitic_error) else None,
            "nuisance_values": nuisance3.tolist(),
            **nerr,
            "hidden_systematic_response_mse": hidden_mse,
            "measured_fit_loss": float(stage3_trace[-1]),
            "loss_reduction_factor_vs_stage1": float(stage1_trace[-1] / max(stage3_trace[-1], 1e-300)),
            "recovery_clause": recovery_clause,
            "loss_trace_every_100": [float(stage3_trace[i]) for i in range(0, len(stage3_trace), 100)],
        },
    }
    path = Path(f"published-filter-parasitic-v06-{a.start}-{a.case}.json")
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
