#!/usr/bin/env python3
"""Robustness of TWC measurement capability at the frozen noisy v0.7 fits.

Executes docs/NOISY_FITTED_CAPABILITY_GATE_2026-08-15.md.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import OMEGA, PARAMETERS
from published_filter_multistate_topology_v07 import STATE_SPECS
from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.identifiability import _realify_matrix, _realify_vector
from transientwave.measurement_aware_filter import lossy_scattering_with_derivatives
from transientwave.measurement_capability import conditional_candidate_information
from transientwave.topology_discovery import absent_reciprocal_edges


RCOND = 1e-10
GAUGE_03 = (0, 3)
GAUGE_25 = (2, 5)
GAUGES = {GAUGE_03, GAUGE_25}
CHANNEL_ROUTES = {
    "s11": ("s11",),
    "s21": ("s21",),
    "s11_s21": ("s11", "s21"),
}


def candidate_key(candidate: MatrixParameter) -> tuple[int, int]:
    return tuple(sorted((int(candidate.i), int(candidate.j))))


def build_fitted_blocks(
    shared_values: np.ndarray,
    nuisance_values: list[list[float]],
    candidate: MatrixParameter,
    channels: tuple[str, ...],
    state_specs,
    omega: np.ndarray = OMEGA,
):
    """Complex response tangent at one frozen v0.7 wrong-topology fitted point."""
    w = np.asarray(omega, dtype=float).reshape(-1)
    shared = np.asarray(shared_values, dtype=float)
    if shared.shape != (len(PARAMETERS),):
        raise ValueError(f"expected {len(PARAMETERS)} shared values, got {shared.shape}")
    if len(nuisance_values) < len(state_specs):
        raise ValueError("insufficient nuisance blocks for requested states")

    nstates = len(state_specs)
    nch = len(channels)
    nshared = len(PARAMETERS)
    nuisance_per_state = 5
    rows_per_state = len(w) * nch
    J = np.zeros(
        (nstates * rows_per_state, nshared + nstates * nuisance_per_state),
        dtype=complex,
    )
    g = np.zeros(nstates * rows_per_state, dtype=complex)
    state_names = []

    deriv_parameters = [*PARAMETERS, candidate]
    for sidx, (state_name, node, fixed_value) in enumerate(state_specs):
        state_names.append(str(state_name))
        nuisance = np.asarray(nuisance_values[sidx], dtype=float)
        if nuisance.shape != (5,):
            raise ValueError("each fitted nuisance block must contain five values")
        loss, phi11, tau11, phi21, tau21 = map(float, nuisance)

        if node is None:
            local_parameters = list(PARAMETERS)
            local_values = shared
        else:
            fixed = MatrixParameter(int(node), int(node), f"known_d{int(node)}_{state_name}")
            local_parameters = [*PARAMETERS, fixed]
            local_values = np.concatenate([shared, np.asarray([fixed_value], dtype=float)])
        matrix = matrix_from_parameters(6, local_parameters, local_values)

        s11, s21, deriv11, deriv21, dloss11, dloss21 = lossy_scattering_with_derivatives(
            matrix,
            w,
            deriv_parameters,
            loss,
        )
        phase11 = np.exp(1j * (phi11 + tau11 * w))
        phase21 = np.exp(1j * (phi21 + tau21 * w))
        y11 = s11 * phase11
        y21 = s21 * phase21
        deriv11 = deriv11 * phase11[:, None]
        deriv21 = deriv21 * phase21[:, None]
        dloss11 = dloss11 * phase11
        dloss21 = dloss21 * phase21

        row0 = sidx * rows_per_state
        row1 = row0 + rows_per_state
        shared_parts = []
        candidate_parts = []
        loss_parts = []
        nuisance_parts = []

        for ch in channels:
            if ch == "s11":
                shared_parts.append(deriv11[:, :nshared])
                candidate_parts.append(deriv11[:, -1])
                loss_parts.append(dloss11)
                nuisance_parts.append(
                    np.column_stack(
                        [
                            1j * y11,
                            1j * w * y11,
                            np.zeros_like(y11),
                            np.zeros_like(y11),
                        ]
                    )
                )
            elif ch == "s21":
                shared_parts.append(deriv21[:, :nshared])
                candidate_parts.append(deriv21[:, -1])
                loss_parts.append(dloss21)
                nuisance_parts.append(
                    np.column_stack(
                        [
                            np.zeros_like(y21),
                            np.zeros_like(y21),
                            1j * y21,
                            1j * w * y21,
                        ]
                    )
                )
            else:
                raise ValueError(ch)

        J[row0:row1, :nshared] = np.concatenate(shared_parts, axis=0)
        g[row0:row1] = np.concatenate(candidate_parts, axis=0)

        local = np.zeros((rows_per_state, nuisance_per_state), dtype=complex)
        local[:, 0] = np.concatenate(loss_parts, axis=0)
        local[:, 1:] = np.concatenate(nuisance_parts, axis=0)
        c0 = nshared + nuisance_per_state * sidx
        J[row0:row1, c0 : c0 + nuisance_per_state] = local

    return J, g, state_names


def information_and_residual(J: np.ndarray, g: np.ndarray):
    Jr = _realify_matrix(J)
    gr = _realify_vector(g)
    metric = conditional_candidate_information(Jr, gr, rcond=RCOND)
    beta, *_ = np.linalg.lstsq(Jr, gr, rcond=RCOND)
    residual_complex = g - J @ beta
    complex_info = float(np.sum(np.abs(residual_complex) ** 2))
    relative_agreement = abs(complex_info - metric.conditional_information) / max(
        metric.raw_candidate_energy, metric.conditional_information, 1e-300
    )
    return metric, residual_complex, float(relative_agreement)


def cumulative_rows(shared, nuisance, candidate, channels):
    rows = []
    infos = []
    for count in range(1, len(STATE_SPECS) + 1):
        J, g, names = build_fitted_blocks(
            shared, nuisance, candidate, channels, STATE_SPECS[:count]
        )
        metric, _resid, agreement = information_and_residual(J, g)
        rows.append(
            {
                "states": names,
                **metric.as_dict(),
                "complex_residual_relative_agreement": agreement,
            }
        )
        infos.append(metric.conditional_information)
    scale = max(rows[-1]["raw_candidate_energy"], rows[-1]["conditional_information"], 1.0)
    minimum_increment = float(np.min(np.diff(np.asarray(infos))))
    return rows, {
        "minimum_increment": minimum_increment,
        "tolerance": 1e-12 * scale,
        "pass": bool(minimum_increment >= -1e-12 * scale),
    }


def full_state_allocation(shared, nuisance, candidate, channels=("s11", "s21")):
    J, g, names = build_fitted_blocks(shared, nuisance, candidate, channels, STATE_SPECS)
    metric, residual, agreement = information_and_residual(J, g)
    nw = len(OMEGA)
    nch = len(channels)
    nstates = len(STATE_SPECS)
    residual = residual.reshape(nstates, nch, nw)
    energy = np.abs(residual) ** 2
    by_state = np.sum(energy, axis=(1, 2))
    total = float(np.sum(by_state))
    fractions = by_state / max(total, 1e-300)
    return {
        "metric": metric.as_dict(),
        "state_fractions": {name: float(v) for name, v in zip(names, fractions)},
        "complex_residual_relative_agreement": agreement,
    }


def analyze_candidate(shared, nuisance, candidate):
    key = candidate_key(candidate)
    cumulative, monotone = cumulative_rows(shared, nuisance, candidate, ("s11", "s21"))
    full = full_state_allocation(shared, nuisance, candidate)
    channel = {}
    for name, route in CHANNEL_ROUTES.items():
        J, g, _ = build_fitted_blocks(shared, nuisance, candidate, route, STATE_SPECS)
        metric, _r, agreement = information_and_residual(J, g)
        channel[name] = {
            **metric.as_dict(),
            "complex_residual_relative_agreement": agreement,
        }

    base = cumulative[0]
    base_dark = bool(base["information_fraction"] < 1e-10) if key in GAUGES else None
    fractions = full["state_fractions"]
    if key == GAUGE_03:
        anchor_fraction = fractions["R1_UP"]
        largest = max(fractions, key=fractions.get)
        anchor_consistent = bool(largest == "R1_UP" and anchor_fraction >= 0.80)
    elif key == GAUGE_25:
        anchor_fraction = fractions["R2_DOWN"] + fractions["R4_UP"]
        largest = max(fractions, key=fractions.get)
        anchor_consistent = bool(
            largest in {"R2_DOWN", "R4_UP"} and anchor_fraction >= 0.80
        )
    else:
        anchor_fraction = None
        largest = max(fractions, key=fractions.get)
        anchor_consistent = None

    return {
        "candidate": list(key),
        "gauge": bool(key in GAUGES),
        "base_dark_calibration": base_dark,
        "anchor_fraction": anchor_fraction,
        "largest_state": largest,
        "anchor_consistent": anchor_consistent,
        "cumulative": cumulative,
        "cumulative_monotonicity_guard": monotone,
        "full_state_allocation": full,
        "channels": channel,
    }


def load_cells(root: Path):
    cells = []
    for path in sorted(root.glob("**/published-filter-multistate-v07-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "stage1_wrong_topology" not in data:
            continue
        cells.append((path, data))
    if len(cells) != 15:
        raise RuntimeError(f"Expected 15 v0.7 cell artifacts, found {len(cells)}")
    return cells


def quantiles(values):
    x = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(x)),
        "q10": float(np.quantile(x, 0.10)),
        "median": float(np.median(x)),
        "q90": float(np.quantile(x, 0.90)),
        "max": float(np.max(x)),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results_root", type=Path)
    p.add_argument("--output", type=Path, default=Path("noisy_fitted_capability_gate.json"))
    args = p.parse_args()

    candidates = absent_reciprocal_edges(6, PARAMETERS)
    candidate_map = {candidate_key(c): c for c in candidates}
    if set(GAUGES) - set(candidate_map):
        raise RuntimeError("Gauge candidates missing from absent edge panel")

    cell_results = []
    all_guards = []
    for path, data in load_cells(args.results_root):
        stage1 = data["stage1_wrong_topology"]
        shared = np.asarray(stage1["shared_matrix_values"], dtype=float)
        nuisance = stage1["state_nuisance_values"]
        per_candidate = {}
        for key in sorted(candidate_map):
            result = analyze_candidate(shared, nuisance, candidate_map[key])
            per_candidate[f"{key[0]},{key[1]}"] = result
            all_guards.append(result["cumulative_monotonicity_guard"]["pass"])
            all_guards.append(
                result["full_state_allocation"]["complex_residual_relative_agreement"] < 1e-10
            )
        cell_results.append(
            {
                "artifact": path.name,
                "case_id": int(data["case_id"]),
                "start_id": str(data["start_id"]),
                "truth_hidden_edge": list(data["truth"]["hidden_edge"]),
                "stage1_matrix_rmse": float(stage1["matrix_rmse"]),
                "stage1_fit_loss": float(stage1["mean_measured_fit_loss"]),
                "old_true_edge_rank": int(data["discovery"]["true_edge_rank"]),
                "old_top1_clause": bool(data["discovery"]["top1_clause"]),
                "old_selected_edge": list(data["discovery"]["selected_edge"]),
                "candidates": per_candidate,
            }
        )

    # Primary gauge robustness summaries.
    gauge_summary = {}
    for key in [GAUGE_03, GAUGE_25]:
        label = f"{key[0]},{key[1]}"
        rows = [cell["candidates"][label] for cell in cell_results]
        consistent = sum(bool(r["anchor_consistent"]) for r in rows)
        base_dark = sum(bool(r["base_dark_calibration"]) for r in rows)
        gauge_summary[label] = {
            "base_dark_count": int(base_dark),
            "anchor_consistent_count": int(consistent),
            "anchor_consistent_fraction": float(consistent / len(rows)),
            "anchor_fraction_distribution": quantiles([r["anchor_fraction"] for r in rows]),
            "pass_12_of_15": bool(consistent >= 12),
        }

    # Channel stability across fitted points for every candidate.
    channel_summary = {}
    for key in sorted(candidate_map):
        label = f"{key[0]},{key[1]}"
        best = []
        s11_ratio = []
        s21_ratio = []
        for cell in cell_results:
            ch = cell["candidates"][label]["channels"]
            i11 = ch["s11"]["conditional_information"]
            i21 = ch["s21"]["conditional_information"]
            ij = ch["s11_s21"]["conditional_information"]
            best.append("s11" if i11 >= i21 else "s21")
            s11_ratio.append(i11 / max(ij, 1e-300))
            s21_ratio.append(i21 / max(ij, 1e-300))
        counts = Counter(best)
        modal, modal_count = counts.most_common(1)[0]
        channel_summary[label] = {
            "modal_better_single_channel": modal,
            "modal_agreement_count": int(modal_count),
            "modal_agreement_fraction": float(modal_count / len(best)),
            "median_s11_over_joint": float(np.median(s11_ratio)),
            "median_s21_over_joint": float(np.median(s21_ratio)),
        }

    # Non-gauge state-allocation controls.
    nongauge_summary = {}
    for key in sorted(set(candidate_map) - GAUGES):
        label = f"{key[0]},{key[1]}"
        state_values = {name: [] for name, *_ in STATE_SPECS}
        base_info_frac = []
        for cell in cell_results:
            item = cell["candidates"][label]
            for state_name, value in item["full_state_allocation"]["state_fractions"].items():
                state_values[state_name].append(value)
            base_info_frac.append(item["cumulative"][0]["information_fraction"])
        nongauge_summary[label] = {
            "state_fraction_distributions": {
                name: quantiles(values) for name, values in state_values.items()
            },
            "base_information_fraction_distribution": quantiles(base_info_frac),
        }

    failed_cells = [
        {
            "case_id": cell["case_id"],
            "start_id": cell["start_id"],
            "truth_hidden_edge": cell["truth_hidden_edge"],
            "old_true_edge_rank": cell["old_true_edge_rank"],
            "old_selected_edge": cell["old_selected_edge"],
            "gauge_03": cell["candidates"]["0,3"],
            "gauge_25": cell["candidates"]["2,5"],
        }
        for cell in cell_results
        if not cell["old_top1_clause"]
    ]

    base_calibration_pass = all(v["base_dark_count"] == 15 for v in gauge_summary.values())
    primary_pass = bool(
        base_calibration_pass
        and gauge_summary["0,3"]["pass_12_of_15"]
        and gauge_summary["2,5"]["pass_12_of_15"]
    )

    output = {
        "experiment": "noisy-fitted-capability-gate-2026-08-15",
        "source_v07_run": 31359232293,
        "cell_count": len(cell_results),
        "primary_rule": "BASE dark in 15/15 for both gauges and anchor consistency >=12/15 for both gauges",
        "gauge_summary": gauge_summary,
        "channel_summary": channel_summary,
        "nongauge_summary": nongauge_summary,
        "failed_old_v07_cells": failed_cells,
        "cell_results": cell_results,
        "all_numerical_guards_pass": bool(all(all_guards)),
        "base_calibration_pass": bool(base_calibration_pass),
        "primary_robustness_pass": primary_pass,
    }
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")

    compact = {
        "gauge_summary": gauge_summary,
        "channel_summary": channel_summary,
        "old_v07_top1_failures": len(failed_cells),
        "all_numerical_guards_pass": bool(all(all_guards)),
        "primary_robustness_pass": primary_pass,
    }
    print("NOISY_FITTED_CAPABILITY_RESULT", json.dumps(compact, separators=(",", ":")))
    print("wrote", args.output)


if __name__ == "__main__":
    main()
