"""Post-hoc Jacobian alias microscope for the frozen v0.6 (2,5) failure.

This is not a qualifying benchmark.  It uses the already-inspected v0.6
case 4303 / start A compensated solution to test whether the first-order
projection metric predicts the observed missing-edge invisibility, then asks
what known perturbation states and S22 would do to that local geometry.
"""
from __future__ import annotations

import json

import numpy as np

from published_cross_coupled_filter_v03 import OMEGA, PARAMETERS
from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.identifiability import multistate_candidate_identifiability
from transientwave.multistate_filter import FilterMeasurementState
from transientwave.topology_discovery import absent_reciprocal_edges


# Frozen v0.6 case 4303 / start A wrong-topology optimum from workflow
# 31357543837 artifact published-filter-parasitic-v06-A-4303.
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
STAGE1_NUISANCE = np.array(
    [
        0.020037341295245672,
        -0.10479624171203358,
        -0.044992000287096934,
        0.17454746818622244,
        0.030129842935876845,
    ],
    dtype=float,
)
TRUE_EDGE = (2, 5)
TRUE_VALUE = -0.025


def make_state(name: str, node: int | None = None, value: float = 0.0) -> FilterMeasurementState:
    zeros = np.zeros_like(OMEGA, dtype=complex)
    if node is None:
        fixed_parameters: tuple[MatrixParameter, ...] = ()
        fixed_values = np.asarray([], dtype=float)
    else:
        fixed_parameters = (MatrixParameter(node, node, f"known_d{node}_{name}"),)
        fixed_values = np.asarray([float(value)], dtype=float)
    return FilterMeasurementState(
        name=name,
        fixed_parameters=fixed_parameters,
        fixed_values=fixed_values,
        measured_s11=zeros,
        measured_s21=zeros,
    )


def score(candidate: MatrixParameter, states, channels):
    # Phase nuisance base values are immaterial to the projection under the
    # corresponding unitary row rotation.  Keep the measured v0.6 nuisance for
    # BASE and use the same loss with zero phase for hypothetical new states.
    nuisance = [STAGE1_NUISANCE]
    for _ in states[1:]:
        nuisance.append(np.array([STAGE1_NUISANCE[0], 0.0, 0.0, 0.0, 0.0]))
    return multistate_candidate_identifiability(
        STAGE1_VALUES,
        n=6,
        shared_parameters=PARAMETERS,
        candidate=candidate,
        omega=OMEGA,
        states=states,
        nuisance_blocks=nuisance,
        channels=channels,
    )


def main() -> None:
    base = [make_state("BASE")]
    v07_states = [
        make_state("BASE"),
        make_state("R1_UP", 1, +0.080),
        make_state("R2_DOWN", 2, -0.070),
        make_state("R4_UP", 4, +0.060),
    ]
    candidate = MatrixParameter(TRUE_EDGE[0], TRUE_EDGE[1], "hidden_m25")

    out: dict[str, object] = {
        "experiment": "filter-identifiability-alias-microscope",
        "qualifying_benchmark": False,
        "source_case": "v0.6 case 4303 / start A",
        "truth_edge": list(TRUE_EDGE),
        "truth_value": TRUE_VALUE,
        "single_state_s11_s21": score(candidate, base, ("s11", "s21")).as_dict(),
        "single_state_plus_s22": score(candidate, base, ("s11", "s21", "s22")).as_dict(),
        "v07_states_s11_s21": score(candidate, v07_states, ("s11", "s21")).as_dict(),
        "v07_states_plus_s22": score(candidate, v07_states, ("s11", "s21", "s22")).as_dict(),
    }

    single_perturbation_scan = []
    for node in range(1, 5):
        for value in (-0.08, +0.08):
            states = [make_state("BASE"), make_state(f"R{node}_{value:+.2f}", node, value)]
            item = score(candidate, states, ("s11", "s21")).as_dict()
            item["detuned_node"] = node
            item["detuning"] = value
            single_perturbation_scan.append(item)
    single_perturbation_scan.sort(key=lambda row: -float(row["novelty_fraction"]))
    out["single_perturbation_scan_s11_s21"] = single_perturbation_scan

    absent_scan = []
    for edge in absent_reciprocal_edges(6, PARAMETERS):
        item = score(edge, base, ("s11", "s21")).as_dict()
        item["is_truth"] = bool((item["i"], item["j"]) == TRUE_EDGE)
        absent_scan.append(item)
    absent_scan.sort(key=lambda row: float(row["novelty_fraction"]))
    out["single_state_absent_edges_low_novelty_first"] = absent_scan

    print(json.dumps(out, indent=2))
    with open("filter-identifiability-alias-microscope.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
