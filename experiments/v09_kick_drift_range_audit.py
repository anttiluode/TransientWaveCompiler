"""Audit exact (Z,P) state range on trained spent v0.8 bodies 2300..2309."""
from __future__ import annotations

import json
import math
from pathlib import Path
import statistics

import numpy as np

from circuit_v08_self_thermal_corner import config_for
from transientwave.circuit_emulator_v08_self_thermal import (
    CommonDiffSelfThermalInterpreter,
    _make_pair,
    run_order_contrast_training,
)
from transientwave.order_benchmarks import compile_temporal_order_task
from transientwave.order_contrast import _sync_theta


SEEDS = list(range(2300, 2310))


class RangeTrackingInterpreter(CommonDiffSelfThermalInterpreter):
    """Exactly v0.8 deterministic dynamics, with CUR-PREV range telemetry."""

    def __init__(self, tile):
        super().__init__(tile)
        self.peak = {
            "forward_z": 0.0,
            "forward_p": 0.0,
            "reverse_c_z": 0.0,
            "reverse_c_p": 0.0,
            "reverse_d_z": 0.0,
            "reverse_d_p": 0.0,
        }

    def _record_pair(self, current, previous, zkey, pkey):
        cur = np.asarray(current, dtype=float)
        prev = np.asarray(previous, dtype=float)
        self.peak[zkey] = max(self.peak[zkey], float(np.max(np.abs(cur))))
        self.peak[pkey] = max(
            self.peak[pkey], float(np.max(np.abs(cur - prev)))
        )

    def _run_forward(self, *, stochastic: bool):
        # Range audit intentionally observes deterministic trajectories after
        # the stochastic learner has selected final parameters.
        if stochastic:
            raise ValueError("range audit requires deterministic execution")
        self._reset_lane_a()
        self._record_pair(self.a_current, self.a_previous, "forward_z", "forward_p")
        self_coeff, edge_matrix, edge_amounts = self.tile.physical_components()
        inj_a = self.tile.edge_injection_node_vector("A", edge_amounts)
        src = self._forward_source_schedule()
        trace = np.zeros(self.tile.steps, dtype=float)

        for k in range(self.tile.steps):
            x = self.tile.retention * self.a_current
            xm1 = self.tile.retention * self.a_previous
            nxt = (
                self_coeff * x
                + edge_matrix @ x
                - self.tile.prev_ratio_gain * xm1
                + src[k]
                + inj_a
            )
            self.a_previous, self.a_current = x, self._clip(nxt)
            self._record_pair(self.a_current, self.a_previous, "forward_z", "forward_p")
            trace[k] = self._sense(self.a_current)

        self.forward_trace = trace
        return self_coeff, edge_matrix, edge_amounts, inj_a

    def _run_lockstep_reverse(
        self,
        self_coeff,
        edge_matrix,
        edge_amounts,
        *,
        stochastic: bool,
    ):
        if stochastic:
            raise ValueError("range audit requires deterministic execution")
        if self.error_schedule is None:
            raise RuntimeError("reverse requires error schedule")

        src_fwd = self._forward_source_schedule()
        qerr = self.error_schedule
        inj_c = self.tile.edge_injection_node_vector("A", edge_amounts)
        inj_d = self.tile.edge_injection_node_vector("B", edge_amounts)
        edge_matrix_c, edge_matrix_d = self.tile.lane_edge_matrices(edge_amounts)

        acc = np.zeros(len(self.tile.trainable), dtype=float)
        plus_sum = np.zeros_like(acc)
        minus_sum = np.zeros_like(acc)
        credit_ret = math.exp(-self.tile.config.credit_accumulator_leakage)

        self._record_pair(self.a_current, self.a_previous, "reverse_c_z", "reverse_c_p")
        self._record_pair(self.b_current, self.b_previous, "reverse_d_z", "reverse_d_p")

        for j in range(1, self.tile.steps + 1):
            dc = self.tile.edge_difference_vector(self.a_current)
            dd = self.tile.edge_difference_vector(self.b_current)
            dplus = dc + dd
            dminus = dc - dd
            pplus = self._lcc_square(dplus)
            pminus = self._lcc_square(dminus)
            plus_sum += pplus
            minus_sum += pminus
            acc = credit_ret * acc + 0.25 * (pplus - pminus)

            if j == self.tile.steps:
                continue

            source_index = self.tile.steps - j
            common_source = src_fwd[source_index]
            diff_error = qerr[source_index]

            cx = self.tile.retention * self.a_current
            cp = self.tile.retention * self.a_previous
            dx = self.tile.retention * self.b_current
            dp = self.tile.retention * self.b_previous

            next_c = (
                self_coeff * cx
                + edge_matrix_c @ cx
                - self.tile.prev_ratio_gain * cp
                + common_source
                + inj_c
            )
            next_d = (
                self_coeff * dx
                + edge_matrix_d @ dx
                - self.tile.prev_ratio_gain * dp
                + diff_error
                + inj_d
            )

            self.a_previous, self.a_current = cx, self._clip(next_c)
            self.b_previous, self.b_current = dx, self._clip(next_d)
            self._record_pair(self.a_current, self.a_previous, "reverse_c_z", "reverse_c_p")
            self._record_pair(self.b_current, self.b_previous, "reverse_d_z", "reverse_d_p")

        self.plus_energy = plus_sum
        self.minus_energy = minus_sum
        return acc


def audit_one_manifest(tile, label):
    interp = RangeTrackingInterpreter(tile)
    interp.execute(stochastic_forward=False)
    fs = float(tile.config.state_full_scale)
    norm = {k: float(v / fs) for k, v in interp.peak.items()}
    return {
        "label": label,
        "state_full_scale": fs,
        "absolute": interp.peak,
        "fraction_of_state_fs": norm,
        "peak_z_fraction": max(norm["forward_z"], norm["reverse_c_z"], norm["reverse_d_z"]),
        "peak_p_fraction": max(norm["forward_p"], norm["reverse_c_p"], norm["reverse_d_p"]),
    }


def main() -> None:
    rows=[]
    for seed in SEEDS:
        task=compile_temporal_order_task(seed)
        cfg=config_for(seed)
        result,gain=run_order_contrast_training(task,cfg,iterations=30,step_size=0.20)

        target,distractor=_make_pair(task,cfg,gain,seed_offset=0)
        target.theta=np.asarray(result.final_theta,dtype=float).copy()
        target._rebuild_programmed_Q()
        _sync_theta(target,distractor)

        ta=audit_one_manifest(target,"target")
        da=audit_one_manifest(distractor,"distractor")
        peak_p=max(ta["peak_p_fraction"],da["peak_p_fraction"])
        peak_z=max(ta["peak_z_fraction"],da["peak_z_fraction"])
        row={
            "seed":seed,
            "training_improvement":float(result.exact_improvement),
            "target":ta,
            "distractor":da,
            "peak_z_fraction":peak_z,
            "peak_p_fraction":peak_p,
            "p_over_z_peak":float(peak_p/max(peak_z,1e-30)),
        }
        rows.append(row)
        print(
            f"{seed}: peakZ={peak_z:.6f} FS peakP={peak_p:.6f} FS "
            f"P/Z={row['p_over_z_peak']:.6f} trainDelta={row['training_improvement']:+.6f}",
            flush=True,
        )

    p=[r["peak_p_fraction"] for r in rows]
    z=[r["peak_z_fraction"] for r in rows]
    worst=float(max(p))
    if worst <= 1.0:
        classification="same_range_plausible"
    elif worst <= 1.25:
        classification="modest_p_headroom"
    elif worst <= 1.5:
        classification="material_p_headroom"
    else:
        classification="not_storage_neutral_in_range"
    summary={
        "maximum_peak_p_fraction":worst,
        "median_peak_p_fraction":float(statistics.median(p)),
        "maximum_peak_z_fraction":float(max(z)),
        "median_peak_z_fraction":float(statistics.median(z)),
        "classification":classification,
    }
    print("summary",summary,flush=True)
    Path("v09-kick-drift-range-audit.json").write_text(
        json.dumps({"experiment":"v09-kick-drift-trained-state-range","seeds":SEEDS,"summary":summary,"runs":rows},indent=2)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__": main()
