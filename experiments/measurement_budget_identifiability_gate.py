#!/usr/bin/env python3
"""Preregistered measurement-budget conditional-identifiability gate.

Executes docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_GATE_2026-08-15.md.

The experiment stays in TWC's native swept-frequency model.  It computes the
squared candidate response component that remains after the declared fitted
physical and state-specific nuisance tangent directions are allowed to
compensate.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import OMEGA, PARAMETERS, TARGET_VALUES
from published_filter_multistate_topology_v07 import LOSS_TARGET, STATE_SPECS
from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.identifiability import (
    _explicit_port_lossy_channels_with_derivatives,
    _realify_matrix,
    _realify_vector,
    orthogonal_novelty_fraction,
)
from transientwave.topology_discovery import absent_reciprocal_edges


RCOND = 1e-10
CHANNEL_ROUTES = {
    "s11": ("s11",),
    "s21": ("s21",),
    "s11_s21": ("s11", "s21"),
}
GAUGE_ALIASES = {(0, 3), (2, 5)}
TOP_K_REQUESTED = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]


def build_blocks(
    candidate: MatrixParameter,
    channels: tuple[str, ...],
    state_specs,
    omega: np.ndarray,
):
    """Build complex global J,g with shared physical + state nuisance columns."""
    w = np.asarray(omega, dtype=float).reshape(-1)
    nstates = len(state_specs)
    nch = len(channels)
    nshared = len(PARAMETERS)
    nuisance_per_state = 5
    rows_per_state = len(w) * nch
    J = np.zeros(
        (rows_per_state * nstates, nshared + nuisance_per_state * nstates),
        dtype=complex,
    )
    g = np.zeros(rows_per_state * nstates, dtype=complex)

    all_deriv_parameters = [*PARAMETERS, candidate]
    state_names = []
    for sidx, (state_name, node, fixed_value) in enumerate(state_specs):
        state_names.append(str(state_name))
        if node is None:
            local_parameters = list(PARAMETERS)
            local_values = np.asarray(TARGET_VALUES, dtype=float)
        else:
            fixed = MatrixParameter(int(node), int(node), f"known_d{int(node)}_{state_name}")
            local_parameters = [*PARAMETERS, fixed]
            local_values = np.concatenate(
                [np.asarray(TARGET_VALUES, dtype=float), np.asarray([fixed_value], dtype=float)]
            )
        matrix = matrix_from_parameters(6, local_parameters, local_values)
        response, deriv, dloss = _explicit_port_lossy_channels_with_derivatives(
            matrix,
            w,
            all_deriv_parameters,
            float(LOSS_TARGET),
            channels,
        )

        row0 = sidx * rows_per_state
        row1 = row0 + rows_per_state
        shared_parts = []
        candidate_parts = []
        loss_parts = []
        for ch in channels:
            shared_parts.append(deriv[ch][:, :nshared])
            candidate_parts.append(deriv[ch][:, -1])
            loss_parts.append(dloss[ch])
        J[row0:row1, :nshared] = np.concatenate(shared_parts, axis=0)
        g[row0:row1] = np.concatenate(candidate_parts, axis=0)

        local = np.zeros((rows_per_state, nuisance_per_state), dtype=complex)
        local[:, 0] = np.concatenate(loss_parts)
        offset = 0
        for ch in channels:
            sl = slice(offset, offset + len(w))
            y = response[ch]
            if ch == "s11":
                local[sl, 1] = 1j * y
                local[sl, 2] = 1j * w * y
            elif ch == "s21":
                local[sl, 3] = 1j * y
                local[sl, 4] = 1j * w * y
            else:
                raise ValueError(ch)
            offset += len(w)

        col0 = nshared + nuisance_per_state * sidx
        col1 = col0 + nuisance_per_state
        J[row0:row1, col0:col1] = local

    return J, g, state_names


def conditional_information(J: np.ndarray, g: np.ndarray):
    Jr = _realify_matrix(J)
    gr = _realify_vector(g)
    beta, *_ = np.linalg.lstsq(Jr, gr, rcond=RCOND)
    residual_r = gr - Jr @ beta
    info = float(residual_r @ residual_r)
    raw = float(gr @ gr)
    metric = orthogonal_novelty_fraction(Jr, gr, rcond=RCOND)
    metric_info = float(metric["residual_norm"]) ** 2
    agreement = abs(info - metric_info) / max(info, metric_info, raw, 1e-300)
    # beta is real, so apply the same coefficients to the complex row model.
    residual_c = g - J @ beta
    complex_info = float(np.sum(np.abs(residual_c) ** 2))
    complex_agreement = abs(complex_info - info) / max(info, raw, 1e-300)
    return {
        "conditional_information": info,
        "raw_candidate_norm_squared": raw,
        "novelty_fraction": float(metric["novelty_fraction"]),
        "information_fraction_of_raw": info / max(raw, 1e-300),
        "jacobian_rank": int(metric["jacobian_rank"]),
        "jacobian_columns": int(metric["jacobian_columns"]),
        "jacobian_condition": metric["jacobian_condition"],
        "projection_metric_relative_agreement": agreement,
        "complex_residual_relative_agreement": complex_agreement,
        "beta": beta,
        "complex_residual": residual_c,
    }


def monotone_guard(values, raw_reference):
    x = np.asarray(values, dtype=float)
    scale = max(float(x[-1]) if len(x) else 0.0, float(raw_reference), 1.0)
    tol = 1e-12 * scale
    minimum_increment = float(np.min(np.diff(x))) if len(x) > 1 else 0.0
    return {
        "minimum_increment": minimum_increment,
        "tolerance": tol,
        "pass": bool(minimum_increment >= -tol),
    }


def fraction_summary(energy: np.ndarray):
    e = np.asarray(energy, dtype=float)
    total = float(np.sum(e))
    if total <= 0.0:
        return [0.0 for _ in e]
    return [float(v) for v in e / total]


def support_entropy(energy):
    e = np.asarray(energy, dtype=float)
    total = float(np.sum(e))
    if total <= 0.0 or len(e) <= 1:
        return 0.0
    p = e / total
    p = p[p > 0.0]
    return float(-np.sum(p * np.log(p)) / np.log(len(e)))


def bins_for_fraction(sorted_energy, target):
    e = np.asarray(sorted_energy, dtype=float)
    total = float(np.sum(e))
    if total <= 0.0:
        return 0
    idx = int(np.searchsorted(np.cumsum(e) / total, float(target), side="left"))
    return idx + 1


def candidate_key(candidate):
    return tuple(sorted((int(candidate.i), int(candidate.j))))


def analyze_candidate(candidate: MatrixParameter):
    key = candidate_key(candidate)
    out = {
        "candidate": list(key),
        "static_gauge_alias": bool(key in GAUGE_ALIASES),
        "state_accumulation": {},
    }

    # A: cumulative known states under each channel route.
    both_cumulative = None
    for route_name, channels in CHANNEL_ROUTES.items():
        route_rows = []
        infos = []
        raw_final = None
        for nstates in range(1, len(STATE_SPECS) + 1):
            specs = STATE_SPECS[:nstates]
            J, g, names = build_blocks(candidate, channels, specs, OMEGA)
            c = conditional_information(J, g)
            infos.append(c["conditional_information"])
            raw_final = c["raw_candidate_norm_squared"]
            route_rows.append(
                {
                    "states": names,
                    "conditional_information": c["conditional_information"],
                    "raw_candidate_norm_squared": c["raw_candidate_norm_squared"],
                    "novelty_fraction": c["novelty_fraction"],
                    "information_fraction_of_raw": c["information_fraction_of_raw"],
                    "jacobian_rank": c["jacobian_rank"],
                    "jacobian_columns": c["jacobian_columns"],
                    "jacobian_condition": c["jacobian_condition"],
                    "projection_metric_relative_agreement": c[
                        "projection_metric_relative_agreement"
                    ],
                }
            )
        guard = monotone_guard(infos, raw_final)
        out["state_accumulation"][route_name] = {
            "rows": route_rows,
            "monotonicity_guard": guard,
            "final_information": float(infos[-1]),
        }
        if route_name == "s11_s21":
            both_cumulative = route_rows

    # D: machine-scale first nonzero state accumulation for gauge aliases.
    if key in GAUGE_ALIASES:
        first_nonzero = None
        for row in both_cumulative:
            if row["conditional_information"] > 1e-8 * max(
                row["raw_candidate_norm_squared"], 1e-300
            ):
                first_nonzero = row["states"]
                break
        out["first_cumulative_state_above_machine_nonzero_fraction"] = first_nonzero

    # B: full-protocol residual allocation with both channels.
    J, g, state_names = build_blocks(
        candidate, CHANNEL_ROUTES["s11_s21"], STATE_SPECS, OMEGA
    )
    full = conditional_information(J, g)
    resid = full["complex_residual"]
    nstates = len(STATE_SPECS)
    nch = 2
    nw = len(OMEGA)
    resid3 = resid.reshape(nstates, nch, nw)
    energy3 = np.abs(resid3) ** 2
    by_frequency = np.sum(energy3, axis=(0, 1))
    by_state = np.sum(energy3, axis=(1, 2))
    by_channel = np.sum(energy3, axis=(0, 2))
    order = np.argsort(-by_frequency, kind="stable")
    sorted_energy = by_frequency[order]
    n50 = bins_for_fraction(sorted_energy, 0.50)
    n90 = bins_for_fraction(sorted_energy, 0.90)
    top12 = [
        {
            "index": int(idx),
            "omega": float(OMEGA[idx]),
            "residual_energy": float(by_frequency[idx]),
            "fraction": float(by_frequency[idx] / max(np.sum(by_frequency), 1e-300)),
        }
        for idx in order[:12]
    ]
    out["full_protocol"] = {
        "conditional_information": full["conditional_information"],
        "raw_candidate_norm_squared": full["raw_candidate_norm_squared"],
        "novelty_fraction": full["novelty_fraction"],
        "information_fraction_of_raw": full["information_fraction_of_raw"],
        "projection_metric_relative_agreement": full[
            "projection_metric_relative_agreement"
        ],
        "complex_residual_relative_agreement": full[
            "complex_residual_relative_agreement"
        ],
        "state_residual_energy_fractions": {
            name: frac for name, frac in zip(state_names, fraction_summary(by_state))
        },
        "channel_residual_energy_fractions": {
            name: frac
            for name, frac in zip(CHANNEL_ROUTES["s11_s21"], fraction_summary(by_channel))
        },
        "frequency_bins_for_50pct_fixed_residual": int(n50),
        "frequency_bins_for_90pct_fixed_residual": int(n90),
        "frequency_fraction_for_50pct_fixed_residual": float(n50 / nw),
        "frequency_fraction_for_90pct_fixed_residual": float(n90 / nw),
        "normalized_frequency_support_entropy": support_entropy(by_frequency),
        "top12_frequency_bins": top12,
    }

    # C: validate nested top-residual frequency sets by fully re-projecting.
    requested = sorted(set([k for k in TOP_K_REQUESTED if k < nw] + [nw]))
    freq_rows = []
    infos = []
    full_info = float(full["conditional_information"])
    raw_ref = float(full["raw_candidate_norm_squared"])
    for k in requested:
        idx = np.sort(order[:k])
        Jk, gk, _ = build_blocks(
            candidate,
            CHANNEL_ROUTES["s11_s21"],
            STATE_SPECS,
            OMEGA[idx],
        )
        ck = conditional_information(Jk, gk)
        ik = float(ck["conditional_information"])
        infos.append(ik)
        freq_rows.append(
            {
                "k": int(k),
                "fraction_of_frequency_grid": float(k / nw),
                "conditional_information": ik,
                "fraction_of_full_information": (
                    None if full_info <= 1e-300 else float(ik / full_info)
                ),
                "novelty_fraction": ck["novelty_fraction"],
            }
        )
    out["top_residual_frequency_validation"] = {
        "rows": freq_rows,
        "monotonicity_guard": monotone_guard(infos, raw_ref),
    }
    return out


def main():
    candidates = absent_reciprocal_edges(6, PARAMETERS)
    found = {candidate_key(c) for c in candidates}
    if not GAUGE_ALIASES.issubset(found):
        raise RuntimeError(f"Gauge aliases missing from absent panel: {GAUGE_ALIASES-found}")

    results = [analyze_candidate(c) for c in candidates]
    results.sort(key=lambda x: tuple(x["candidate"]))

    all_guards = []
    for item in results:
        for route in CHANNEL_ROUTES:
            all_guards.append(item["state_accumulation"][route]["monotonicity_guard"]["pass"])
        all_guards.append(
            item["top_residual_frequency_validation"]["monotonicity_guard"]["pass"]
        )
        all_guards.append(item["full_protocol"]["projection_metric_relative_agreement"] < 1e-10)
        all_guards.append(item["full_protocol"]["complex_residual_relative_agreement"] < 1e-10)

    compact = []
    for item in results:
        base = item["state_accumulation"]["s11_s21"]["rows"][0]
        full = item["full_protocol"]
        krows = item["top_residual_frequency_validation"]["rows"]
        compact.append(
            {
                "candidate": item["candidate"],
                "gauge": item["static_gauge_alias"],
                "base_info_frac_raw": base["information_fraction_of_raw"],
                "full_info_frac_raw": full["information_fraction_of_raw"],
                "full_novelty": full["novelty_fraction"],
                "state_fractions": full["state_residual_energy_fractions"],
                "channel_fractions": full["channel_residual_energy_fractions"],
                "n90_fixed_residual": full["frequency_bins_for_90pct_fixed_residual"],
                "topk_info_fractions": {
                    str(r["k"]): r["fraction_of_full_information"] for r in krows
                },
            }
        )

    output = {
        "experiment": "measurement-budget-identifiability-gate-2026-08-15",
        "qualifying_benchmark": False,
        "model": {
            "omega_count": int(len(OMEGA)),
            "omega_min": float(np.min(OMEGA)),
            "omega_max": float(np.max(OMEGA)),
            "state_specs": [list(x) for x in STATE_SPECS],
            "loss": float(LOSS_TARGET),
            "candidate_count": len(results),
            "gauge_aliases": [list(x) for x in sorted(GAUGE_ALIASES)],
        },
        "results": results,
        "all_frozen_guards_pass": bool(all(all_guards)),
    }
    outpath = Path("measurement_budget_identifiability_gate.json")
    outpath.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("MEASUREMENT_BUDGET_RESULT", json.dumps(compact, separators=(",", ":")))
    print("ALL_GUARDS_PASS", bool(all(all_guards)))
    print("wrote", outpath)


if __name__ == "__main__":
    main()
