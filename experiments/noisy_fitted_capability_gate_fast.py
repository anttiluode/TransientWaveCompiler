#!/usr/bin/env python3
"""Cached implementation of the frozen noisy fitted-point capability gate.

Scientifically identical to ``noisy_fitted_capability_gate.py``.  The only
change is computational: all declared absent-edge derivatives are evaluated in
one scattering pass per fitted state and then reused for candidate projections.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from published_cross_coupled_filter_v03 import OMEGA, PARAMETERS
from published_filter_multistate_topology_v07 import STATE_SPECS
from transientwave.coupled_resonator_filter import MatrixParameter, matrix_from_parameters
from transientwave.identifiability import _realify_matrix, _realify_vector
from transientwave.measurement_aware_filter import lossy_scattering_with_derivatives
from transientwave.measurement_capability import conditional_candidate_information
from transientwave.topology_discovery import absent_reciprocal_edges

RCOND = 1e-10
GAUGE_03 = (0, 3)
GAUGE_25 = (2, 5)
GAUGES = {GAUGE_03, GAUGE_25}
CHANNEL_ROUTES = {"s11": ("s11",), "s21": ("s21",), "s11_s21": ("s11", "s21")}


def key(c):
    return tuple(sorted((int(c.i), int(c.j))))


def load_cells(root: Path):
    cells = []
    for path in sorted(root.glob("**/published-filter-multistate-v07-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "stage1_wrong_topology" in data:
            cells.append((path, data))
    if len(cells) != 15:
        raise RuntimeError(f"Expected 15 v0.7 cell artifacts, found {len(cells)}")
    return cells


def quantiles(values):
    x = np.asarray(values, dtype=float)
    return {k: float(v) for k, v in zip(
        ["min", "q10", "median", "q90", "max"], np.quantile(x, [0, .1, .5, .9, 1])
    )}


def precompute_states(shared, nuisance_values, candidates):
    """One matrix inverse/derivative sweep per state for ALL candidates."""
    w = np.asarray(OMEGA, dtype=float)
    deriv_parameters = [*PARAMETERS, *candidates]
    out = []
    for sidx, (state_name, node, fixed_value) in enumerate(STATE_SPECS):
        nuisance = np.asarray(nuisance_values[sidx], dtype=float)
        loss, phi11, tau11, phi21, tau21 = map(float, nuisance)
        if node is None:
            local_parameters = list(PARAMETERS)
            local_values = np.asarray(shared, dtype=float)
        else:
            fixed = MatrixParameter(int(node), int(node), f"known_d{int(node)}_{state_name}")
            local_parameters = [*PARAMETERS, fixed]
            local_values = np.concatenate([np.asarray(shared, dtype=float), [float(fixed_value)]])
        matrix = matrix_from_parameters(6, local_parameters, local_values)
        s11, s21, d11, d21, dl11, dl21 = lossy_scattering_with_derivatives(
            matrix, w, deriv_parameters, loss
        )
        p11 = np.exp(1j * (phi11 + tau11 * w))
        p21 = np.exp(1j * (phi21 + tau21 * w))
        y11, y21 = s11 * p11, s21 * p21
        out.append({
            "name": str(state_name),
            "y11": y11,
            "y21": y21,
            "d11": d11 * p11[:, None],
            "d21": d21 * p21[:, None],
            "dl11": dl11 * p11,
            "dl21": dl21 * p21,
        })
    return out


def build_blocks(cache, candidate_col, channels, nstates):
    nw = len(OMEGA)
    nshared = len(PARAMETERS)
    nrows_state = nw * len(channels)
    J = np.zeros((nrows_state * nstates, nshared + 5 * nstates), complex)
    g = np.zeros(nrows_state * nstates, complex)
    names = []
    w = np.asarray(OMEGA, dtype=float)
    for sidx, state in enumerate(cache[:nstates]):
        names.append(state["name"])
        pieces_j, pieces_g, pieces_local = [], [], []
        for ch in channels:
            if ch == "s11":
                pieces_j.append(state["d11"][:, :nshared])
                pieces_g.append(state["d11"][:, candidate_col])
                pieces_local.append(np.column_stack([
                    state["dl11"], 1j * state["y11"], 1j * w * state["y11"],
                    np.zeros(nw, complex), np.zeros(nw, complex)
                ]))
            elif ch == "s21":
                pieces_j.append(state["d21"][:, :nshared])
                pieces_g.append(state["d21"][:, candidate_col])
                pieces_local.append(np.column_stack([
                    state["dl21"], np.zeros(nw, complex), np.zeros(nw, complex),
                    1j * state["y21"], 1j * w * state["y21"]
                ]))
            else:
                raise ValueError(ch)
        r0, r1 = sidx * nrows_state, (sidx + 1) * nrows_state
        J[r0:r1, :nshared] = np.concatenate(pieces_j, axis=0)
        g[r0:r1] = np.concatenate(pieces_g, axis=0)
        c0 = nshared + 5 * sidx
        J[r0:r1, c0:c0 + 5] = np.concatenate(pieces_local, axis=0)
    return J, g, names


def info_residual(J, g):
    Jr, gr = _realify_matrix(J), _realify_vector(g)
    metric = conditional_candidate_information(Jr, gr, rcond=RCOND)
    beta, *_ = np.linalg.lstsq(Jr, gr, rcond=RCOND)
    rc = g - J @ beta
    ci = float(np.sum(np.abs(rc) ** 2))
    agree = abs(ci - metric.conditional_information) / max(
        metric.raw_candidate_energy, metric.conditional_information, 1e-300
    )
    return metric, rc, float(agree)


def analyze(cache, candidate, candidate_col):
    ckey = key(candidate)
    cumulative, infos = [], []
    for nstates in range(1, 5):
        J, g, names = build_blocks(cache, candidate_col, ("s11", "s21"), nstates)
        m, _r, agree = info_residual(J, g)
        cumulative.append({"states": names, **m.as_dict(), "complex_residual_relative_agreement": agree})
        infos.append(m.conditional_information)
    scale = max(cumulative[-1]["raw_candidate_energy"], cumulative[-1]["conditional_information"], 1.0)
    monotone = {
        "minimum_increment": float(np.min(np.diff(infos))),
        "tolerance": 1e-12 * scale,
        "pass": bool(np.min(np.diff(infos)) >= -1e-12 * scale),
    }

    J, g, names = build_blocks(cache, candidate_col, ("s11", "s21"), 4)
    m, rc, agree = info_residual(J, g)
    e = np.abs(rc.reshape(4, 2, len(OMEGA))) ** 2
    by_state = np.sum(e, axis=(1, 2))
    fr = by_state / max(float(np.sum(by_state)), 1e-300)
    state_fractions = {name: float(v) for name, v in zip(names, fr)}
    full = {"metric": m.as_dict(), "state_fractions": state_fractions,
            "complex_residual_relative_agreement": agree}

    channels = {}
    for rname, route in CHANNEL_ROUTES.items():
        Jc, gc, _ = build_blocks(cache, candidate_col, route, 4)
        cm, _cr, ca = info_residual(Jc, gc)
        channels[rname] = {**cm.as_dict(), "complex_residual_relative_agreement": ca}

    base_dark = bool(cumulative[0]["information_fraction"] < 1e-10) if ckey in GAUGES else None
    largest = max(state_fractions, key=state_fractions.get)
    if ckey == GAUGE_03:
        af = state_fractions["R1_UP"]
        consistent = bool(largest == "R1_UP" and af >= .80)
    elif ckey == GAUGE_25:
        af = state_fractions["R2_DOWN"] + state_fractions["R4_UP"]
        consistent = bool(largest in {"R2_DOWN", "R4_UP"} and af >= .80)
    else:
        af, consistent = None, None
    return {
        "candidate": list(ckey), "gauge": ckey in GAUGES,
        "base_dark_calibration": base_dark, "anchor_fraction": af,
        "largest_state": largest, "anchor_consistent": consistent,
        "cumulative": cumulative, "cumulative_monotonicity_guard": monotone,
        "full_state_allocation": full, "channels": channels,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_root", type=Path)
    ap.add_argument("--output", type=Path, default=Path("noisy_fitted_capability_gate.json"))
    args = ap.parse_args()

    candidates = sorted(absent_reciprocal_edges(6, PARAMETERS), key=key)
    cmap = {key(c): c for c in candidates}
    nshared = len(PARAMETERS)
    ccol = {key(c): nshared + idx for idx, c in enumerate(candidates)}
    cells, guards = [], []
    for path, data in load_cells(args.results_root):
        s1 = data["stage1_wrong_topology"]
        cache = precompute_states(s1["shared_matrix_values"], s1["state_nuisance_values"], candidates)
        pc = {}
        for c in candidates:
            k = key(c)
            r = analyze(cache, c, ccol[k])
            pc[f"{k[0]},{k[1]}"] = r
            guards += [r["cumulative_monotonicity_guard"]["pass"],
                       r["full_state_allocation"]["complex_residual_relative_agreement"] < 1e-10]
        cells.append({
            "artifact": path.name, "case_id": int(data["case_id"]), "start_id": str(data["start_id"]),
            "truth_hidden_edge": list(data["truth"]["hidden_edge"]),
            "stage1_matrix_rmse": float(s1["matrix_rmse"]),
            "stage1_fit_loss": float(s1["mean_measured_fit_loss"]),
            "old_true_edge_rank": int(data["discovery"]["true_edge_rank"]),
            "old_top1_clause": bool(data["discovery"]["top1_clause"]),
            "old_selected_edge": list(data["discovery"]["selected_edge"]), "candidates": pc,
        })

    gs = {}
    for k in [GAUGE_03, GAUGE_25]:
        label = f"{k[0]},{k[1]}"; rows = [c["candidates"][label] for c in cells]
        consistent = sum(bool(r["anchor_consistent"]) for r in rows)
        dark = sum(bool(r["base_dark_calibration"]) for r in rows)
        gs[label] = {"base_dark_count": dark, "anchor_consistent_count": consistent,
                     "anchor_consistent_fraction": consistent/15,
                     "anchor_fraction_distribution": quantiles([r["anchor_fraction"] for r in rows]),
                     "pass_12_of_15": consistent >= 12}

    cs = {}
    for k in sorted(cmap):
        label = f"{k[0]},{k[1]}"; best=[]; r11=[]; r21=[]
        for cell in cells:
            ch=cell["candidates"][label]["channels"]
            i11=ch["s11"]["conditional_information"]; i21=ch["s21"]["conditional_information"]
            ij=ch["s11_s21"]["conditional_information"]
            best.append("s11" if i11 >= i21 else "s21")
            r11.append(i11/max(ij,1e-300)); r21.append(i21/max(ij,1e-300))
        count=Counter(best); modal,n=count.most_common(1)[0]
        cs[label]={"modal_better_single_channel":modal,"modal_agreement_count":n,
                   "modal_agreement_fraction":n/15,"median_s11_over_joint":float(np.median(r11)),
                   "median_s21_over_joint":float(np.median(r21))}

    ng={}
    for k in sorted(set(cmap)-GAUGES):
        label=f"{k[0]},{k[1]}"; sv={name:[] for name,*_ in STATE_SPECS}; bi=[]
        for cell in cells:
            item=cell["candidates"][label]
            for n,v in item["full_state_allocation"]["state_fractions"].items(): sv[n].append(v)
            bi.append(item["cumulative"][0]["information_fraction"])
        ng[label]={"state_fraction_distributions":{n:quantiles(v) for n,v in sv.items()},
                   "base_information_fraction_distribution":quantiles(bi)}

    fails=[]
    for cell in cells:
        if not cell["old_top1_clause"]:
            fails.append({"case_id":cell["case_id"],"start_id":cell["start_id"],
                          "truth_hidden_edge":cell["truth_hidden_edge"],"old_true_edge_rank":cell["old_true_edge_rank"],
                          "old_selected_edge":cell["old_selected_edge"],
                          "gauge_03":cell["candidates"]["0,3"],"gauge_25":cell["candidates"]["2,5"]})
    basepass=all(v["base_dark_count"]==15 for v in gs.values())
    primary=bool(basepass and gs["0,3"]["pass_12_of_15"] and gs["2,5"]["pass_12_of_15"])
    out={"experiment":"noisy-fitted-capability-gate-2026-08-15","source_v07_run":31359232293,
         "cell_count":15,"primary_rule":"BASE dark in 15/15 for both gauges and anchor consistency >=12/15 for both gauges",
         "gauge_summary":gs,"channel_summary":cs,"nongauge_summary":ng,"failed_old_v07_cells":fails,
         "cell_results":cells,"all_numerical_guards_pass":bool(all(guards)),
         "base_calibration_pass":basepass,"primary_robustness_pass":primary}
    args.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print("NOISY_FITTED_CAPABILITY_RESULT",json.dumps({"gauge_summary":gs,"channel_summary":cs,
          "old_v07_top1_failures":len(fails),"all_numerical_guards_pass":bool(all(guards)),
          "primary_robustness_pass":primary},separators=(",",":")))
    print("wrote",args.output)

if __name__ == "__main__": main()
