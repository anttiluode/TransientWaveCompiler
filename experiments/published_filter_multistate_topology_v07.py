"""Preregistered v0.7 multi-state hidden-edge diagnosis benchmark."""
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
from transientwave.measurement_aware_filter import measurement_aware_response, wrap_phase_error
from transientwave.multistate_filter import (
    FilterMeasurementState,
    multistate_loss_and_gradient,
    multistate_responses,
    score_missing_reciprocal_edges_multistate,
)


ALLOWED_STARTS = ["A", "C", "D"]
LOSS_TARGET = 0.020
SWEEPS = 8
AMP_SIGMA = 0.005
PHASE_SIGMA_RAD = np.deg2rad(0.5)
ITERATIONS = 3000
LR = 0.010
PROBE_BOUND = 0.12

CASES = {
    4400: ((2, 5), -0.032),
    4401: ((1, 5), +0.028),
    4402: ((0, 3), -0.026),
    4403: ((3, 5), +0.033),
    4404: ((0, 4), -0.022),
}

# (state name, optional known diagonal node, fixed diagonal value)
STATE_SPECS = [
    ("BASE", None, 0.0),
    ("R1_UP", 1, +0.080),
    ("R2_DOWN", 2, -0.070),
    ("R4_UP", 4, +0.060),
]

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


def state_nuisance_truth(case_id: int, state_index: int) -> np.ndarray:
    """Frozen deterministic nuisance truth, independent of optimizer start."""
    rng = np.random.default_rng(np.random.SeedSequence([int(case_id), int(state_index), 707]))
    return np.array(
        [
            LOSS_TARGET,
            np.deg2rad(rng.uniform(-12.0, +12.0)),
            rng.uniform(-0.050, +0.050),
            np.deg2rad(rng.uniform(-12.0, +12.0)),
            rng.uniform(-0.050, +0.050),
        ],
        dtype=float,
    )


def make_measurement_states(case_id: int):
    edge, hidden_value = CASES[int(case_id)]
    hidden_parameter = MatrixParameter(edge[0], edge[1], f"hidden_m{edge[0]}{edge[1]}")
    true_shared_parameters = [*PARAMETERS, hidden_parameter]
    true_shared_values = np.concatenate([TARGET_VALUES, np.asarray([hidden_value], dtype=float)])

    states: list[FilterMeasurementState] = []
    clean_responses: list[tuple[np.ndarray, np.ndarray]] = []
    nuisance_truths: list[np.ndarray] = []
    fixed_descriptions = []

    for state_index, (name, node, fixed_value) in enumerate(STATE_SPECS):
        if node is None:
            fixed_parameters: tuple[MatrixParameter, ...] = ()
            fixed_values = np.asarray([], dtype=float)
        else:
            fixed_parameters = (MatrixParameter(node, node, f"known_d{node}_{name}"),)
            fixed_values = np.asarray([fixed_value], dtype=float)

        local_parameters = [*true_shared_parameters, *fixed_parameters]
        local_values = np.concatenate([true_shared_values, fixed_values])
        nuisance = state_nuisance_truth(case_id, state_index)
        clean11, clean21 = measurement_aware_response(
            local_values,
            n=6,
            parameters=local_parameters,
            omega=OMEGA,
            resonator_loss=float(nuisance[0]),
            phi11=float(nuisance[1]),
            tau11=float(nuisance[2]),
            phi21=float(nuisance[3]),
            tau21=float(nuisance[4]),
        )
        root = np.random.SeedSequence([int(case_id), int(state_index), 1707])
        a, b = root.spawn(2)
        measured11 = noisy_average(clean11, np.random.default_rng(a))
        measured21 = noisy_average(clean21, np.random.default_rng(b))
        states.append(
            FilterMeasurementState(
                name=name,
                fixed_parameters=fixed_parameters,
                fixed_values=fixed_values,
                measured_s11=measured11,
                measured_s21=measured21,
            )
        )
        clean_responses.append((clean11, clean21))
        nuisance_truths.append(nuisance)
        fixed_descriptions.append(
            {
                "name": name,
                "diagonal_node": node,
                "diagonal_value": float(fixed_value),
            }
        )
    return (
        states,
        clean_responses,
        nuisance_truths,
        hidden_parameter,
        float(hidden_value),
        fixed_descriptions,
    )


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


def global_bounds(shared_lower, shared_upper, state_count: int):
    lower = np.concatenate([shared_lower] + [NUISANCE_LOWER] * state_count)
    upper = np.concatenate([shared_upper] + [NUISANCE_UPPER] * state_count)
    return lower, upper


def global_start(shared_start, state_count: int):
    return np.concatenate([np.asarray(shared_start, dtype=float)] + [NUISANCE_INITIAL] * state_count)


def stage1_fit(start, states):
    x0 = global_start(start, len(states))
    lower, upper = global_bounds(LOWER, UPPER, len(states))

    def objective(x):
        return multistate_loss_and_gradient(
            x,
            n=6,
            shared_parameters=PARAMETERS,
            omega=OMEGA,
            states=states,
        )

    return adam_optimize(x0, lower, upper, objective, "stage1")


def nuisance_blocks_from_global(x, shared_count: int, state_count: int):
    return [
        np.asarray(x[shared_count + 5 * s : shared_count + 5 * (s + 1)], dtype=float)
        for s in range(state_count)
    ]


def stage3_fit(stage1, selected: MatrixParameter, proposed, states):
    shared_parameters = [*PARAMETERS, selected]
    x0 = np.concatenate([stage1[:7], np.asarray([proposed], dtype=float), stage1[7:]])
    lower, upper = global_bounds(
        np.concatenate([LOWER, np.asarray([-PROBE_BOUND])]),
        np.concatenate([UPPER, np.asarray([+PROBE_BOUND])]),
        len(states),
    )

    def objective(x):
        return multistate_loss_and_gradient(
            x,
            n=6,
            shared_parameters=shared_parameters,
            omega=OMEGA,
            states=states,
        )

    final, trace = adam_optimize(x0, lower, upper, objective, "stage3")
    return shared_parameters, final, trace


def matrix_rmse(values):
    d = np.asarray(values, dtype=float) - TARGET_VALUES
    return float(np.sqrt(np.mean(d * d)))


def nuisance_error(fitted: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    return {
        "lambda_abs_error": float(abs(fitted[0] - truth[0])),
        "phi11_abs_error_deg": float(np.rad2deg(abs(wrap_phase_error(fitted[1], truth[1])))),
        "tau11_abs_error": float(abs(fitted[2] - truth[2])),
        "phi21_abs_error_deg": float(np.rad2deg(abs(wrap_phase_error(fitted[3], truth[3])))),
        "tau21_abs_error": float(abs(fitted[4] - truth[4])),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=ALLOWED_STARTS, required=True)
    ap.add_argument("--case", type=int, choices=sorted(CASES), required=True)
    a = ap.parse_args()

    (
        states,
        clean_responses,
        nuisance_truths,
        hidden_parameter,
        hidden_value,
        fixed_descriptions,
    ) = make_measurement_states(a.case)
    true_edge = tuple(sorted((hidden_parameter.i, hidden_parameter.j)))
    print(
        f"case={a.case} start={a.start} hidden_edge={true_edge} hidden_value={hidden_value:+.6f}",
        flush=True,
    )

    stage1, stage1_trace = stage1_fit(STARTS[a.start], states)
    stage1_rmse = matrix_rmse(stage1[:7])
    nuisance1 = nuisance_blocks_from_global(stage1, 7, len(states))
    print(
        f"  stage1 mean_loss={stage1_trace[-1]:.9e} matrix_rmse={stage1_rmse:.6e}",
        flush=True,
    )

    scores = score_missing_reciprocal_edges_multistate(
        stage1[:7],
        n=6,
        shared_parameters=PARAMETERS,
        omega=OMEGA,
        states=states,
        nuisance_blocks=nuisance1,
        max_abs_probe=PROBE_BOUND,
    )
    ranking = [(score.i, score.j) for score in scores]
    true_rank = ranking.index(true_edge) + 1
    selected_score = scores[0]
    selected_edge = (selected_score.i, selected_score.j)
    selected = MatrixParameter(selected_score.i, selected_score.j, f"candidate_m{selected_score.i}{selected_score.j}")
    print(
        f"  ranking top3={ranking[:3]} true_rank={true_rank} selected={selected_edge} "
        f"proposed={selected_score.proposed_value:+.6f} "
        f"probe_reduction={selected_score.relative_loss_reduction:+.4%}",
        flush=True,
    )

    stage3_parameters, stage3, stage3_trace = stage3_fit(
        stage1,
        selected,
        selected_score.proposed_value,
        states,
    )
    stage3_base_rmse = matrix_rmse(stage3[:7])
    selected_value = float(stage3[7])
    selected_is_true = bool(selected_edge == true_edge)
    parasitic_error = float(abs(selected_value - hidden_value)) if selected_is_true else None
    nuisance3 = nuisance_blocks_from_global(stage3, 8, len(states))
    nuisance_errors = [
        nuisance_error(fitted, truth)
        for fitted, truth in zip(nuisance3, nuisance_truths)
    ]

    predicted = multistate_responses(
        stage3[:8],
        n=6,
        shared_parameters=stage3_parameters,
        omega=OMEGA,
        states=states,
        nuisance_blocks=nuisance3,
    )
    hidden_clean_mses = [
        float(np.mean(np.abs(p11 - c11) ** 2 + np.abs(p21 - c21) ** 2))
        for (p11, p21), (c11, c21) in zip(predicted, clean_responses)
    ]
    mean_hidden_clean_mse = float(np.mean(hidden_clean_mses))

    nuisance_pass = all(
        err["lambda_abs_error"] <= 0.0075
        and err["phi11_abs_error_deg"] <= 3.0
        and err["phi21_abs_error_deg"] <= 3.0
        and err["tau11_abs_error"] <= 0.0075
        and err["tau21_abs_error"] <= 0.0075
        for err in nuisance_errors
    )
    top1_clause = bool(true_rank == 1)
    top3_clause = bool(true_rank <= 3)
    recovery_clause = bool(
        selected_is_true
        and stage3_base_rmse <= 0.010
        and parasitic_error is not None
        and parasitic_error <= 0.005
        and nuisance_pass
        and mean_hidden_clean_mse <= 5e-5
        and stage3_trace[-1] < stage1_trace[-1]
    )
    print(
        f"  stage3 mean_loss={stage3_trace[-1]:.9e} base_rmse={stage3_base_rmse:.6e} "
        f"selected_value={selected_value:+.6f} hidden_mse={mean_hidden_clean_mse:.6e} "
        f"TOP1={top1_clause} TOP3={top3_clause} RECOVERY={recovery_clause}",
        flush=True,
    )

    out = {
        "experiment": "published-filter-multistate-topology-v07",
        "preregistration": "docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_PREREG.md",
        "case_id": int(a.case),
        "start_id": a.start,
        "truth": {
            "base_matrix_values": TARGET_VALUES.tolist(),
            "hidden_edge": list(true_edge),
            "hidden_edge_value": float(hidden_value),
            "states": [
                {
                    **desc,
                    "nuisance": nuisance.tolist(),
                }
                for desc, nuisance in zip(fixed_descriptions, nuisance_truths)
            ],
        },
        "measurement": {
            "sweeps_per_state": SWEEPS,
            "amplitude_noise_rms_fraction": AMP_SIGMA,
            "phase_noise_rms_degrees": 0.5,
        },
        "stage1_wrong_topology": {
            "shared_matrix_values": stage1[:7].tolist(),
            "state_nuisance_values": [block.tolist() for block in nuisance1],
            "matrix_rmse": stage1_rmse,
            "mean_measured_fit_loss": float(stage1_trace[-1]),
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
            "shared_base_matrix_values": stage3[:7].tolist(),
            "selected_edge_value": selected_value,
            "base_matrix_rmse": stage3_base_rmse,
            "parasitic_abs_error": parasitic_error,
            "state_nuisance_values": [block.tolist() for block in nuisance3],
            "state_nuisance_errors": nuisance_errors,
            "nuisance_clause": bool(nuisance_pass),
            "state_hidden_clean_systematic_response_mse": hidden_clean_mses,
            "mean_hidden_clean_systematic_response_mse": mean_hidden_clean_mse,
            "mean_measured_fit_loss": float(stage3_trace[-1]),
            "loss_reduction_factor_vs_stage1": float(stage1_trace[-1] / max(stage3_trace[-1], 1e-300)),
            "recovery_clause": recovery_clause,
            "loss_trace_every_100": [float(stage3_trace[i]) for i in range(0, len(stage3_trace), 100)],
        },
    }
    path = Path(f"published-filter-multistate-v07-{a.start}-{a.case}.json")
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
