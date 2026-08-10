"""Post-hoc topology-only identifiability table for the published folded filter.

This script deliberately consumes no S-parameter response, measurement noise,
or fitted optimizer state.  It uses only the declared coupling-matrix topology
and nominal matrix values to ask which absent reciprocal edges reopen an
internal similarity-rotation gauge.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import PARAMETERS, TARGET_M
from transientwave.coupled_resonator_filter import matrix_from_parameters
from transientwave.topology_gauge import (
    analyze_absent_edges_gauge,
    single_detuning_anchors_that_break_alias,
)


# Independently observed after the v0.6 failure by projecting response
# sensitivities onto the seven physical matrix columns at the compensated fit.
# This is used only as a post-hoc cross-check of the topology-only prediction.
OBSERVED_MACHINE_ZERO_PHYSICAL_ALIASES = {(0, 3), (2, 5)}
V07_ANCHOR_NODES = (1, 2, 4)


def alias_set(matrix: np.ndarray) -> set[tuple[int, int]]:
    return {
        row.candidate
        for row in analyze_absent_edges_gauge(matrix, PARAMETERS)
        if row.aliased
    }


def generic_topology_checks() -> list[dict[str, object]]:
    """Check that the alias set is stable at generic nonzero edge values."""
    rng = np.random.default_rng(20260810)
    rows = []
    for sample in range(8):
        magnitudes = rng.uniform(0.20, 1.30, size=len(PARAMETERS))
        signs = rng.choice(np.asarray([-1.0, +1.0]), size=len(PARAMETERS))
        values = magnitudes * signs
        matrix = matrix_from_parameters(6, PARAMETERS, values)
        predicted = sorted(alias_set(matrix))
        rows.append(
            {
                "sample": int(sample),
                "predicted_aliased_edges": [list(edge) for edge in predicted],
            }
        )
    return rows


def main() -> None:
    static = analyze_absent_edges_gauge(TARGET_M, PARAMETERS)
    static_aliases = {row.candidate for row in static if row.aliased}

    table = []
    for row in static:
        anchors = single_detuning_anchors_that_break_alias(
            TARGET_M,
            PARAMETERS,
            row.candidate,
        )
        anchored_v07 = analyze_absent_edges_gauge(
            TARGET_M,
            PARAMETERS,
            anchors=V07_ANCHOR_NODES,
        )
        anchored_by_edge = {item.candidate: item for item in anchored_v07}
        payload = row.as_dict()
        payload["single_detuning_anchors_that_break_alias"] = anchors
        payload["aliased_with_v07_anchor_set_R1_R2_R4"] = bool(
            anchored_by_edge[row.candidate].aliased
        )
        table.append(payload)

    generic = generic_topology_checks()
    generic_alias_sets = {
        tuple(tuple(edge) for edge in row["predicted_aliased_edges"])
        for row in generic
    }
    expected_tuple = tuple(sorted(OBSERVED_MACHINE_ZERO_PHYSICAL_ALIASES))

    out = {
        "experiment": "published-filter-topology-gauge-table",
        "qualifying_benchmark": False,
        "uses_measurement_or_sparameters": False,
        "internal_resonators": 4,
        "so_internal_dimension": 6,
        "declared_coupling_count": len(PARAMETERS),
        "absent_candidate_count": len(static),
        "nominal_topology_baseline_gauge_dimension": int(
            static[0].baseline_gauge_dimension if static else 0
        ),
        "predicted_static_aliased_edges": [list(edge) for edge in sorted(static_aliases)],
        "independently_observed_machine_zero_physical_aliases": [
            list(edge) for edge in sorted(OBSERVED_MACHINE_ZERO_PHYSICAL_ALIASES)
        ],
        "prediction_matches_response_jacobian_microscope_exactly": bool(
            static_aliases == OBSERVED_MACHINE_ZERO_PHYSICAL_ALIASES
        ),
        "candidate_table": table,
        "v07_known_detuning_anchor_nodes": list(V07_ANCHOR_NODES),
        "all_static_gauge_aliases_broken_by_v07_anchor_set": bool(
            all(
                not analyze_absent_edges_gauge(
                    TARGET_M,
                    PARAMETERS,
                    anchors=V07_ANCHOR_NODES,
                )[idx].aliased
                for idx in range(len(static))
                if static[idx].aliased
            )
        ),
        "generic_nonzero_value_checks": generic,
        "generic_alias_set_stable": bool(
            generic_alias_sets == {expected_tuple}
        ),
        "interpretation": (
            "Releasing (0,3) frees the R1<->R3 internal rotation; releasing "
            "(2,5) frees the R2<->R4 rotation. The other six absent edges do "
            "not release an internal rotation at the declared topology. Known "
            "detuning of either resonator touched by the corresponding rotation "
            "anchors that gauge."
        ),
    }

    Path("published-filter-topology-gauge-table.json").write_text(
        json.dumps(out, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
