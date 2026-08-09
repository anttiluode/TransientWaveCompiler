"""Same-silicon split of switch-kick cancellation residual and residual floor."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_common_diff_corner import config_for as formal_config
from transientwave.circuit_emulator_v08_common_diff import CommonDiffLockstepInterpreter, _eval_pair
from transientwave.circuit_emulator_v08_site_ratio import _make_pair, copy_circuit_disorder
from transientwave.circuit_emulator_v07_active_summing import recommend_sense_gain
from transientwave.emulator import _rms
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient

SEEDS = list(range(2100, 2110))
FOCUS = 2107
CONDITIONS = (
    ("formal", 1.0, 1.0),
    ("cancel_x0p50", 0.5, 1.0),
    ("cancel_x0p25", 0.25, 1.0),
    ("cancel_x0p10", 0.10, 1.0),
    ("floor_x0p50", 1.0, 0.5),
    ("floor_x0p25", 1.0, 0.25),
    ("floor_x0p10", 1.0, 0.10),
    ("both_x0p50", 0.5, 0.5),
    ("both_x0p25", 0.25, 0.25),
)


def _rebuild_kick(tile, s_cancel: float, s_floor: float):
    fs = float(tile.config.state_full_scale)
    cc = np.asarray(tile.edge_injection_raw_common) - np.asarray(tile.edge_injection_common_measured)
    cd = np.asarray(tile.edge_injection_raw_diff) - np.asarray(tile.edge_injection_diff_measured)
    fc = np.asarray(tile.edge_injection_common) - cc
    fd = np.asarray(tile.edge_injection_diff) - cd
    rc = s_cancel * cc + s_floor * fc
    rd = s_cancel * cd + s_floor * fd
    tile.edge_injection_common = rc.copy()
    tile.edge_injection_diff = rd.copy()
    tile.edge_injection_a = rc + rd
    tile.edge_injection_b = rc - rd
    return {
        "cancel_common": _rms(cc) / fs,
        "cancel_diff": _rms(cd) / fs,
        "floor_common": _rms(fc) / fs,
        "floor_diff": _rms(fd) / fs,
        "total_common": _rms(rc) / fs,
        "total_diff": _rms(rd) / fs,
    }


def _train(task, cfg, s_cancel, s_floor, iterations=30, step_size=0.20):
    gain = recommend_sense_gain(task, cfg)
    exact_t, exact_d = _make_pair(task, cfg, gain, seed_offset=0)
    shuffle_t, shuffle_d = _make_pair(task, cfg, gain, seed_offset=100_003)
    copy_circuit_disorder(exact_t, shuffle_t)
    copy_circuit_disorder(exact_t, shuffle_d)
    _sync_theta(exact_t, shuffle_t); _sync_theta(exact_t, shuffle_d)
    stats = _rebuild_kick(exact_t, s_cancel, s_floor)
    for tile in (exact_d, shuffle_t, shuffle_d):
        _rebuild_kick(tile, s_cancel, s_floor)
    _sync_theta(exact_t, exact_d); _sync_theta(exact_t, shuffle_t); _sync_theta(exact_t, shuffle_d)
    eti, edi = CommonDiffLockstepInterpreter(exact_t), CommonDiffLockstepInterpreter(exact_d)
    sti, sdi = CommonDiffLockstepInterpreter(shuffle_t), CommonDiffLockstepInterpreter(shuffle_d)
    et0, ed0, c0 = _eval_pair(eti, edi); st0, sd0, sc0 = _eval_pair(sti, sdi)
    ec=[c0]; sc=[sc0]; ete=[et0]; ede=[ed0]; ste=[st0]; sde=[sd0]; mt=[]; md=[]; cr=[]
    perm=np.random.default_rng(1729).permutation(len(exact_t.theta))
    for _ in range(iterations):
        rt, rd = eti.execute(stochastic_forward=True), edi.execute(stochastic_forward=True)
        et, ed = float(rt["objective"]), float(rd["objective"])
        gc=contrast_gradient(et,ed,np.asarray(rt["credits"]),np.asarray(rd["credits"]),eps=1e-30)
        mt.append(et); md.append(ed); cr.append(_rms(gc))
        exact_t.apply_credits(-gc,step_size=step_size,normalize_rms=True); _sync_theta(exact_t,exact_d)
        shuffle_t.apply_credits(-gc[perm],step_size=step_size,normalize_rms=True); _sync_theta(shuffle_t,shuffle_d)
        etv,edv,cv=_eval_pair(eti,edi); stv,sdv,scv=_eval_pair(sti,sdi)
        ete.append(etv); ede.append(edv); ec.append(cv); ste.append(stv); sde.append(sdv); sc.append(scv)
    return OrderContrastTrainingResult(exact_contrast=ec,shuffled_contrast=sc,exact_target_energy=ete,exact_distractor_energy=ede,shuffled_target_energy=ste,shuffled_distractor_energy=sde,measured_target_energy=mt,measured_distractor_energy=md,combined_credit_rms=cr,final_theta=exact_t.theta.copy(),final_theta_shuffled=shuffle_t.theta.copy()), gain, stats


def summarize(rows):
    imp=[float(r["improvement"]) for r in rows]; gaps=[float(r["placement_gap"]) for r in rows]
    focus=next(r for r in rows if r["seed"]==FOCUS)
    n10=sum(x>=0.10 for x in imp); wins=sum(bool(r["final_win"]) for r in rows)
    med_imp=float(statistics.median(imp)); med_gap=float(statistics.median(gaps))
    keys=("cancel_common","cancel_diff","floor_common","floor_diff","total_common","total_diff")
    phys={k:{"mean":float(np.mean([r["kick"][k] for r in rows])),"max":float(max(r["kick"][k] for r in rows))} for k in keys}
    return {"formal_predicate":bool(n10==10 and wins==10 and med_imp>=0.30 and med_gap>=0.25),"improve_ge_0p10":n10,"final_wins":wins,"median_improvement":med_imp,"minimum_improvement":float(min(imp)),"median_placement_gap":med_gap,"minimum_placement_gap":float(min(gaps)),"focus_2107":{"improvement":focus["improvement"],"placement_gap":focus["placement_gap"],"final_win":focus["final_win"]},"kick_fraction":phys}


def main():
    out={"experiment":"tw1a-v08-switch-kick-mechanism-split","status":"diagnostic-only-spent-2100-2109","preregistration":"docs/CIRCUIT_V08_KICK_MECHANISM_PREREG.md","conditions":[]}
    for name,sc,sf in CONDITIONS:
        print(name,sc,sf,flush=True); rows=[]
        for seed in SEEDS:
            result,gain,kick=_train(compile_temporal_order_task(seed),formal_config(seed),sc,sf)
            row={"seed":seed,"sense_gain":gain,"kick":kick,"improvement":result.exact_improvement,"placement_gap":result.placement_gap,"final_exact":result.exact_contrast[-1],"final_shuffled":result.shuffled_contrast[-1],"final_win":result.exact_contrast[-1]>result.shuffled_contrast[-1]}
            rows.append(row); print(f"  {seed}: DeltaC={row['improvement']:+.6f} gap={row['placement_gap']:+.6f} win={row['final_win']}",flush=True)
        s=summarize(rows); print("  summary",s,flush=True); out["conditions"].append({"name":name,"s_cancel":sc,"s_floor":sf,"summary":s,"runs":rows})
    Path("v08-kick-mechanism-split.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
