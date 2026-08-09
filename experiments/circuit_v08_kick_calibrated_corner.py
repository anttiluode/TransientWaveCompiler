"""Fresh preregistered v0.8 gate with 0.5% kick-cancellation measurement error."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_common_diff_corner import config_for as v08_formal_config
from transientwave.circuit_emulator_v08_site_ratio import (
    TW1ACommonDiffSiteTile,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task


SEEDS = list(range(2200, 2210))


def config_for(seed: int):
    # Preserve every v0.8 formal value except the preregistered 4x improvement
    # in foreground kick-cancellation measurement accuracy and use a fresh tile
    # seed range.
    return replace(
        v08_formal_config(seed),
        edge_charge_cancellation_error_std=0.005,
        seed=190_000 + seed,
    )


def audit_fabrication(manifest, cfg):
    tile = TW1ACommonDiffSiteTile(manifest, cfg, sense_gain=1.0)
    fs = np.asarray(tile.edge_cap_levels[:, -1], dtype=float)
    return {
        "all_monotonic": bool(np.all(tile.edge_codebook_monotonic)),
        "all_site_scales_positive": bool(tile.edge_site_ratio_valid),
        "all_headroom": bool(np.all(fs >= 0.25)),
        "minimum_edge_full_scale": float(np.min(fs)),
        "maximum_edge_full_scale": float(np.max(fs)),
        "minimum_site_scale": float(np.min(tile.edge_site_ratio_scale)),
        "maximum_site_scale": float(np.max(tile.edge_site_ratio_scale)),
        "minimum_codebook_step": float(np.min(tile.edge_codebook_steps)),
        "kick_common_rms_fraction": float(np.sqrt(np.mean(tile.edge_injection_common**2)) / cfg.state_full_scale),
        "kick_diff_rms_fraction": float(np.sqrt(np.mean(tile.edge_injection_diff**2)) / cfg.state_full_scale),
    }


def main() -> None:
    rows=[]; fabrication_pass=True
    for seed in SEEDS:
        task=compile_temporal_order_task(seed); cfg=config_for(seed); fab=audit_fabrication(task["target"],cfg)
        fab_ok=bool(fab["all_monotonic"] and fab["all_site_scales_positive"] and fab["all_headroom"])
        fabrication_pass = fabrication_pass and fab_ok
        print(f"seed={seed} mono={fab['all_monotonic']} positive={fab['all_site_scales_positive']} headroom={fab['all_headroom']} FSmin={fab['minimum_edge_full_scale']:.6f} kickC={fab['kick_common_rms_fraction']:.3e} kickD={fab['kick_diff_rms_fraction']:.3e}",flush=True)
        if not fab_ok:
            rows.append({"seed":seed,"fabrication":fab,"sense_gain":None,"improvement":None,"placement_gap":None,"initial_contrast":None,"final_exact":None,"final_shuffled":None,"final_win":False}); continue
        result,gain=run_order_contrast_training(task,cfg,iterations=30,step_size=0.20)
        row={"seed":seed,"fabrication":fab,"sense_gain":gain,"improvement":result.exact_improvement,"placement_gap":result.placement_gap,"initial_contrast":result.exact_contrast[0],"final_exact":result.exact_contrast[-1],"final_shuffled":result.shuffled_contrast[-1],"final_win":result.exact_contrast[-1]>result.shuffled_contrast[-1]}
        rows.append(row); print(f"  PGA={gain:g} DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} C={row['final_exact']:+.6f} Cshuffle={row['final_shuffled']:+.6f}",flush=True)

    learned=[r for r in rows if r["improvement"] is not None]
    if len(learned)==10:
        imp=[float(r["improvement"]) for r in learned]; gaps=[float(r["placement_gap"]) for r in learned]
        n10=sum(x>=0.10 for x in imp); wins=sum(bool(r["final_win"]) for r in learned)
        med_imp=float(statistics.median(imp)); med_gap=float(statistics.median(gaps)); min_imp=float(min(imp)); min_gap=float(min(gaps))
    else:
        n10=wins=0; med_imp=med_gap=min_imp=min_gap=None
    qualified=bool(fabrication_pass and len(learned)==10 and n10==10 and wins==10 and med_imp is not None and med_imp>=0.30 and med_gap is not None and med_gap>=0.25)
    summary={"qualified":qualified,"fabrication_pass":fabrication_pass,"fabricated_tiles_pass":sum(bool(r["fabrication"]["all_monotonic"] and r["fabrication"]["all_site_scales_positive"] and r["fabrication"]["all_headroom"]) for r in rows),"fabricated_tiles_total":len(rows),"improve_ge_0p10":n10,"final_wins":wins,"median_improvement":med_imp,"minimum_improvement":min_imp,"median_placement_gap":med_gap,"minimum_placement_gap":min_gap,"minimum_edge_full_scale":float(min(r["fabrication"]["minimum_edge_full_scale"] for r in rows)),"mean_kick_common_rms_fraction":float(np.mean([r["fabrication"]["kick_common_rms_fraction"] for r in rows])),"mean_kick_diff_rms_fraction":float(np.mean([r["fabrication"]["kick_diff_rms_fraction"] for r in rows]))}
    print("summary",summary,flush=True)
    Path("circuit-v08-kick-calibrated-corner.json").write_text(json.dumps({"experiment":"tw1a-v08-kick-calibrated-formal-gate","preregistration":"docs/CIRCUIT_V08_KICK_CALIBRATED_PREREG.md","seeds":SEEDS,"cancellation_error_std":0.005,"common_floor_std":config_for(SEEDS[0]).edge_charge_residual_common_floor_std,"differential_floor_std":config_for(SEEDS[0]).edge_charge_residual_differential_floor_std,"iterations":30,"step_size":0.20,"config":config_for(SEEDS[0]).__dict__,"summary":summary,"runs":rows},indent=2)+"\n",encoding="utf-8")
    if not qualified: raise SystemExit(1)

if __name__=="__main__": main()
