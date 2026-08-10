"""Aggregate the post-hoc candidate-conditioned v0.6 failure microscope."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--output", default="v06-conditional-summary.json")
    a = ap.parse_args()

    paths = sorted(Path(a.root).rglob("v06-conditional-*.json"))
    paths = [path for path in paths if not path.name.endswith("summary.json")]
    if len(paths) != 24:
        raise SystemExit(f"expected 24 candidate cells, found {len(paths)}")
    cells = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    starts = {}
    truth_top1 = 0
    for start in ["A", "C", "D"]:
        group = [cell for cell in cells if cell["start_id"] == start]
        group.sort(key=lambda cell: cell["conditional_final_loss"])
        ranking = [tuple(cell["candidate_edge"]) for cell in group]
        truth = tuple(group[0]["truth_edge"])
        rank = ranking.index(truth) + 1
        truth_cell = next(cell for cell in group if tuple(cell["candidate_edge"]) == truth)
        if rank == 1:
            truth_top1 += 1
        starts[start] = {
            "conditional_ranking": [list(pair) for pair in ranking],
            "truth_rank": rank,
            "truth_candidate_value": truth_cell["conditional_candidate_value"],
            "truth_candidate_final_loss": truth_cell["conditional_final_loss"],
            "truth_candidate_base_matrix_rmse": truth_cell["conditional_base_matrix_rmse"],
            "local_truth_rank": truth_cell["local_probe_rank"],
            "best_candidate_final_loss": group[0]["conditional_final_loss"],
            "second_candidate_final_loss": group[1]["conditional_final_loss"],
            "best_to_second_loss_ratio": group[0]["conditional_final_loss"] / max(group[1]["conditional_final_loss"], 1e-300),
        }

    summary = {
        "experiment": "published-filter-parasitic-v06-conditional-microscope",
        "qualifying_benchmark": False,
        "already_inspected_case": 4303,
        "truth_edge": [2, 5],
        "truth_value": -0.025,
        "truth_top1_after_conditional_refit": truth_top1,
        "starts": starts,
    }
    Path(a.output).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
