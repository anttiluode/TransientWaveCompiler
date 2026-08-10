"""Post-hoc microscope: is the v0.6 m25 alias physical or nuisance-driven?"""
from __future__ import annotations

import json

import numpy as np

from published_cross_coupled_filter_v03 import OMEGA, PARAMETERS
from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.identifiability import (
    _explicit_port_lossy_channels_with_derivatives,
    _realify_matrix,
    _realify_vector,
    orthogonal_novelty_fraction,
)
from transientwave.topology_discovery import absent_reciprocal_edges


STAGE1_VALUES = np.array(
    [
        1.0200565592719817,
        -0.8644024611067477,
        0.7486562052179283,
        -0.8786320205338013,
        1.020359910890014,
        -0.1687616053091747,
        0.0004825375987860725,
    ],
    dtype=float,
)
LOSS = 0.020037341295245672


def blocks(candidate: MatrixParameter, channels: tuple[str, ...]):
    matrix = matrix_from_parameters(6, PARAMETERS, STAGE1_VALUES)
    all_parameters = [*PARAMETERS, candidate]
    response, deriv, dloss = _explicit_port_lossy_channels_with_derivatives(
        matrix, OMEGA, all_parameters, LOSS, channels
    )
    physical = np.concatenate(
        [deriv[ch][:, : len(PARAMETERS)] for ch in channels], axis=0
    )
    g = np.concatenate([deriv[ch][:, -1] for ch in channels])
    loss_col = np.concatenate([dloss[ch] for ch in channels])[:, None]

    nuisance_cols = [loss_col]
    offset = 0
    rows = len(OMEGA) * len(channels)
    # Build explicit phase nuisance columns in the same channel stacking order.
    for ch in channels:
        phi = np.zeros(rows, dtype=complex)
        tau = np.zeros(rows, dtype=complex)
        sl = slice(offset, offset + len(OMEGA))
        phi[sl] = 1j * response[ch]
        tau[sl] = 1j * OMEGA * response[ch]
        nuisance_cols.extend([phi[:, None], tau[:, None]])
        offset += len(OMEGA)
    nuisance = np.concatenate(nuisance_cols, axis=1)
    return physical, nuisance, g


def metric(j_complex, g_complex):
    return orthogonal_novelty_fraction(
        _realify_matrix(j_complex), _realify_vector(g_complex)
    )


def inspect_candidate(candidate: MatrixParameter, channels: tuple[str, ...]):
    physical, nuisance, g = blocks(candidate, channels)
    physical_metric = metric(physical, g)
    physical_loss_metric = metric(np.concatenate([physical, nuisance[:, :1]], axis=1), g)
    full_metric = metric(np.concatenate([physical, nuisance], axis=1), g)

    jr = _realify_matrix(physical)
    gr = _realify_vector(g)
    coeff, *_ = np.linalg.lstsq(jr, gr, rcond=1e-10)
    residual = gr - jr @ coeff
    return {
        "candidate": [int(candidate.i), int(candidate.j)],
        "channels": list(channels),
        "physical_only": physical_metric,
        "physical_plus_loss": physical_loss_metric,
        "physical_plus_all_channel_phase_nuisance": full_metric,
        "physical_lstsq_coefficients": {
            parameter.name: float(value)
            for parameter, value in zip(PARAMETERS, coeff)
        },
        "physical_lstsq_relative_residual": float(
            np.linalg.norm(residual) / max(np.linalg.norm(gr), 1e-300)
        ),
    }


def main():
    truth = MatrixParameter(2, 5, "m25")
    out = {
        "experiment": "filter-identifiability-gauge-microscope",
        "qualifying_benchmark": False,
        "source": "v0.6 case 4303 / start A wrong-topology optimum",
        "m25_s11_s21": inspect_candidate(truth, ("s11", "s21")),
        "m25_s11_s21_s22": inspect_candidate(truth, ("s11", "s21", "s22")),
    }

    scan = []
    for candidate in absent_reciprocal_edges(6, PARAMETERS):
        item = inspect_candidate(candidate, ("s11", "s21"))
        scan.append(
            {
                "candidate": item["candidate"],
                "physical_only_novelty": item["physical_only"]["novelty_fraction"],
                "full_novelty": item["physical_plus_all_channel_phase_nuisance"]["novelty_fraction"],
            }
        )
    scan.sort(key=lambda x: float(x["physical_only_novelty"]))
    out["absent_edge_physical_alias_scan"] = scan

    print(json.dumps(out, indent=2))
    with open("filter-identifiability-gauge-microscope.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
