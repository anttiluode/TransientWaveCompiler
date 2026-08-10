"""Post-hoc v0.6 failure microscope: conditionally refit one candidate edge.

This script is deliberately NOT a qualifying benchmark. It uses the already
inspected v0.6 failure case 4303 to determine whether the failure is local
probe blindness or deeper response ambiguity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import PARAMETERS, STARTS
from published_filter_parasitic_topology_v06 import (
    PROBE_BOUND,
    make_measurement,
    matrix_rmse,
    stage1_fit,
    stage3_fit,
)
from transientwave.coupled_resonator_filter import MatrixParameter
from transientwave.topology_discovery import score_missing_reciprocal_edges


CASE_ID = 4303
CANDIDATES = {
    "02": (0, 2),
    "03": (0, 3),
    "04": (0, 4),
    "13": (1, 3),
    "15": (1, 5),
    "24": (2, 4),
    "25": (2, 5),
    "35": (3, 5),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=["A", "C", "D"], required=True)
    ap.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    a = ap.parse_args()

    measured11, measured21, _clean11, _clean21, hidden_parameter, hidden_value, _truth_nuisance = make_measurement(CASE_ID)
    stage1, stage1_trace = stage1_fit(STARTS[a.start], measured11, measured21)
    nuisance1 = stage1[7:]

    all_scores = score_missing_reciprocal_edges(
        stage1[:7],
        n=6,
        parameters=PARAMETERS,
        omega=__import__("published_cross_coupled_filter_v03").OMEGA,
        measured_s11=measured11,
        measured_s21=measured21,
        resonator_loss=float(nuisance1[0]),
        phi11=float(nuisance1[1]),
        tau11=float(nuisance1[2]),
        phi21=float(nuisance1[3]),
        tau21=float(nuisance1[4]),
        max_abs_probe=PROBE_BOUND,
    )
    pair = CANDIDATES[a.candidate]
    score = next(item for item in all_scores if (item.i, item.j) == pair)
    candidate = MatrixParameter(pair[0], pair[1], f"candidate_m{pair[0]}{pair[1]}")

    _parameters, stage3, stage3_trace = stage3_fit(
        stage1,
        candidate,
        score.proposed_value,
        measured11,
        measured21,
    )

    truth_pair = tuple(sorted((hidden_parameter.i, hidden_parameter.j)))
    out = {
        "experiment": "published-filter-parasitic-v06-conditional-microscope",
        "qualifying_benchmark": False,
        "case_id": CASE_ID,
        "start_id": a.start,
        "truth_edge": list(truth_pair),
        "truth_value": float(hidden_value),
        "candidate_edge": list(pair),
        "candidate_is_truth": bool(pair == truth_pair),
        "stage1_loss": float(stage1_trace[-1]),
        "stage1_base_matrix_rmse": matrix_rmse(stage1[:7]),
        "local_probe_rank": int([(x.i, x.j) for x in all_scores].index(pair) + 1),
        "local_probe_value": float(score.proposed_value),
        "local_probe_loss": float(score.probe_loss),
        "conditional_final_loss": float(stage3_trace[-1]),
        "conditional_base_matrix_rmse": matrix_rmse(stage3[:7]),
        "conditional_candidate_value": float(stage3[7]),
        "conditional_loss_reduction_vs_stage1": float(stage1_trace[-1] / max(stage3_trace[-1], 1e-300)),
    }
    path = Path(f"v06-conditional-{a.start}-{a.candidate}.json")
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
