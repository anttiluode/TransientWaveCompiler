"""Execute the preregistered ideal temporal-order contrast qualification."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .emulator import TW1APhysicalTileConfig
from .order_benchmarks import compile_temporal_order_task
from .order_contrast import run_order_contrast_training


SEEDS = tuple(range(840, 850))


def main() -> None:
    cfg = TW1APhysicalTileConfig(
        weight_bits=None,
        dac_bits=None,
        adc_bits=None,
        state_noise_std=0.0,
        state_full_scale=20.0,
        clip_state=False,
        leakage_rate=0.0,
        leakage_cv=0.0,
        mirror_error=0.0,
        differential_pass_drift=0.0,
        credit_offset_fraction=0.0,
        credit_noise_fraction=0.0,
        adc_full_scale=20.0,
        seed=91_000,
    )

    rows = []
    for seed in SEEDS:
        task = compile_temporal_order_task(seed)
        local_cfg = TW1APhysicalTileConfig(**{**cfg.__dict__, "seed": 91_000 + seed})
        result = run_order_contrast_training(
            task,
            local_cfg,
            iterations=40,
            step_size=0.20,
            normalize_rms=True,
            include_shuffle=True,
            shuffle_seed=191_000 + seed,
        )
        row = {
            "seed": seed,
            "leaf_a": task["metadata"]["leaf_a"],
            "leaf_b": task["metadata"]["leaf_b"],
            "leaf_a_root_distance": task["metadata"]["leaf_a_root_distance"],
            "leaf_b_root_distance": task["metadata"]["leaf_b_root_distance"],
            "leaf_pair_distance": task["metadata"]["leaf_pair_distance"],
            "initial_contrast": result.exact_contrast[0],
            "final_exact_contrast": result.exact_contrast[-1],
            "final_shuffled_contrast": result.shuffled_contrast[-1],
            "exact_improvement": result.exact_improvement,
            "shuffled_improvement": result.shuffled_improvement,
            "placement_gap": result.placement_gap,
            "initial_target_energy": result.exact_target_energy[0],
            "initial_distractor_energy": result.exact_distractor_energy[0],
            "final_target_energy": result.exact_target_energy[-1],
            "final_distractor_energy": result.exact_distractor_energy[-1],
            "credit_rms_min": float(np.min(result.combined_credit_rms)),
            "credit_rms_max": float(np.max(result.combined_credit_rms)),
            "finite": bool(
                np.all(np.isfinite(result.exact_contrast))
                and np.all(np.isfinite(result.shuffled_contrast))
                and np.all(np.isfinite(result.exact_target_energy))
                and np.all(np.isfinite(result.exact_distractor_energy))
                and np.all(np.isfinite(result.final_theta))
                and np.all(np.isfinite(result.final_theta_shuffled))
            ),
        }
        rows.append(row)
        print(
            f"seed={seed} leaves={row['leaf_a']},{row['leaf_b']} "
            f"droot={row['leaf_a_root_distance']},{row['leaf_b_root_distance']} "
            f"C0={row['initial_contrast']:+.4f} "
            f"Cexact={row['final_exact_contrast']:+.4f} "
            f"Cshuffle={row['final_shuffled_contrast']:+.4f} "
            f"dC={row['exact_improvement']:+.4f} "
            f"gap={row['placement_gap']:+.4f}",
            flush=True,
        )

    exact = np.asarray([r["exact_improvement"] for r in rows], dtype=float)
    shuffled = np.asarray([r["shuffled_improvement"] for r in rows], dtype=float)
    final_exact = np.asarray([r["final_exact_contrast"] for r in rows], dtype=float)
    final_shuffled = np.asarray([r["final_shuffled_contrast"] for r in rows], dtype=float)

    summary = {
        "seeds": list(SEEDS),
        "all_positive": bool(np.all(exact > 0.0)),
        "count_exact_ge_0p10": int(np.sum(exact >= 0.10)),
        "median_exact_improvement": float(np.median(exact)),
        "exact_final_beats_shuffle_count": int(np.sum(final_exact > final_shuffled)),
        "median_placement_gap": float(np.median(exact - shuffled)),
        "all_finite": bool(all(r["finite"] for r in rows)),
    }
    summary["qualified"] = bool(
        summary["all_positive"]
        and summary["count_exact_ge_0p10"] >= 8
        and summary["median_exact_improvement"] >= 0.15
        and summary["exact_final_beats_shuffle_count"] >= 8
        and summary["median_placement_gap"] >= 0.10
        and summary["all_finite"]
    )

    out = {
        "experiment": "tw1a_temporal_order_contrast_ideal_v01",
        "prereg": "docs/ORDER_CONTRAST_IDEAL_PREREG_V01.md",
        "config": cfg.__dict__,
        "optimizer": {"iterations": 40, "step_size": 0.20, "normalize_rms": True},
        "rows": rows,
        "summary": summary,
    }
    path = Path("runs/order_contrast_ideal_v01.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\nSUMMARY", json.dumps(summary, sort_keys=True), flush=True)
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
