"""Aggregate preregistered v0.7 multi-state topology-diagnosis cells."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--output", default="published-filter-multistate-v07-summary.json")
    a = ap.parse_args()

    paths = sorted(Path(a.root).rglob("published-filter-multistate-v07-*.json"))
    paths = [path for path in paths if not path.name.endswith("summary.json")]
    if len(paths) != 15:
        raise SystemExit(f"expected 15 cell JSON files, found {len(paths)}")
    cells = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    top1 = sum(bool(cell["discovery"]["top1_clause"]) for cell in cells)
    top3 = sum(bool(cell["discovery"]["top3_clause"]) for cell in cells)
    recovery = sum(bool(cell["stage3_augmented"]["recovery_clause"]) for cell in cells)
    discovery_primary = bool(top1 >= 12 and top3 == 15)
    recovery_primary = bool(recovery >= 12)
    strong = bool(top1 == 15 and recovery == 15)

    ranks = [int(cell["discovery"]["true_edge_rank"]) for cell in cells]
    stage1_rmse = [float(cell["stage1_wrong_topology"]["matrix_rmse"]) for cell in cells]
    stage3_rmse = [float(cell["stage3_augmented"]["base_matrix_rmse"]) for cell in cells]
    losses = [float(cell["stage3_augmented"]["loss_reduction_factor_vs_stage1"]) for cell in cells]
    parasitic_errors = [
        float(cell["stage3_augmented"]["parasitic_abs_error"])
        for cell in cells
        if cell["stage3_augmented"]["parasitic_abs_error"] is not None
    ]

    by_case = {}
    for case_id in sorted({int(cell["case_id"]) for cell in cells}):
        group = [cell for cell in cells if int(cell["case_id"]) == case_id]
        by_case[str(case_id)] = {
            "hidden_edge": group[0]["truth"]["hidden_edge"],
            "hidden_edge_value": group[0]["truth"]["hidden_edge_value"],
            "top1": sum(bool(cell["discovery"]["top1_clause"]) for cell in group),
            "top3": sum(bool(cell["discovery"]["top3_clause"]) for cell in group),
            "recovery": sum(bool(cell["stage3_augmented"]["recovery_clause"]) for cell in group),
            "true_ranks": [int(cell["discovery"]["true_edge_rank"]) for cell in group],
        }

    summary = {
        "experiment": "published-filter-multistate-topology-v07",
        "cells": len(cells),
        "top1_count": int(top1),
        "top3_count": int(top3),
        "recovery_count": int(recovery),
        "discovery_primary_pass": discovery_primary,
        "recovery_primary_pass": recovery_primary,
        "strong_15_of_15_label": strong,
        "median_true_edge_rank": float(np.median(ranks)),
        "max_true_edge_rank": int(max(ranks)),
        "median_stage1_wrong_topology_matrix_rmse": float(np.median(stage1_rmse)),
        "median_stage3_base_matrix_rmse": float(np.median(stage3_rmse)),
        "median_stage3_loss_reduction_factor_vs_stage1": float(np.median(losses)),
        "median_parasitic_abs_error_when_selected_true": (
            float(np.median(parasitic_errors)) if parasitic_errors else None
        ),
        "by_case": by_case,
        "cells_detail": [
            {
                "case_id": int(cell["case_id"]),
                "start_id": cell["start_id"],
                "hidden_edge": cell["truth"]["hidden_edge"],
                "hidden_edge_value": cell["truth"]["hidden_edge_value"],
                "true_edge_rank": int(cell["discovery"]["true_edge_rank"]),
                "selected_edge": cell["discovery"]["selected_edge"],
                "top1": bool(cell["discovery"]["top1_clause"]),
                "top3": bool(cell["discovery"]["top3_clause"]),
                "recovery": bool(cell["stage3_augmented"]["recovery_clause"]),
                "stage1_matrix_rmse": float(cell["stage1_wrong_topology"]["matrix_rmse"]),
                "stage3_matrix_rmse": float(cell["stage3_augmented"]["base_matrix_rmse"]),
                "parasitic_abs_error": cell["stage3_augmented"]["parasitic_abs_error"],
                "loss_reduction_factor": float(cell["stage3_augmented"]["loss_reduction_factor_vs_stage1"]),
            }
            for cell in cells
        ],
    }
    Path(a.output).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
