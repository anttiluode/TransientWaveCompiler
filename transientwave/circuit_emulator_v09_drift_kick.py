"""TW-1A v0.9 kick-drift with post-cancellation drift switch residuals."""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .circuit_emulator_v05_edge_thermal_fast import _draw_reciprocal_noise
from .circuit_emulator_v07_active_summing import recommend_sense_gain
from .circuit_emulator_v08_common_diff import _eval_pair
from .circuit_emulator_v09_kick_drift import (
    KickDriftInterpreter,
    TW1AKickDriftConfig,
    TW1AKickDriftTile,
    copy_circuit_disorder as _copy_kd_disorder,
)
from .emulator import _rms
from .order_contrast import OrderContrastTrainingResult, _sync_theta, contrast_gradient


Array = np.ndarray


@dataclass(frozen=True)
class TW1ADriftKickConfig(TW1AKickDriftConfig):
    drift_kick_common_rms_fraction: float = 0.0
    drift_kick_diff_rms_fraction: float = 0.0
    drift_kick_seed_salt: int = 0xD21C9

    def validate(self) -> None:
        super().validate()
        for name in ("drift_kick_common_rms_fraction", "drift_kick_diff_rms_fraction"):
            v=float(getattr(self,name))
            if not np.isfinite(v) or v < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")


class TW1ADriftKickTile(TW1AKickDriftTile):
    def __init__(self, manifest: dict[str, Any], config: TW1ADriftKickConfig | None=None, *, sense_gain: float=1.0):
        cfg=TW1ADriftKickConfig(prev_ratio_calibration=False) if config is None else config
        cfg.validate(); super().__init__(manifest,cfg,sense_gain=sense_gain); self.config: TW1ADriftKickConfig
        seed=(int(cfg.seed)*1_000_121+int(cfg.drift_kick_seed_salt)) & 0xFFFFFFFFFFFFFFFF
        rng=np.random.default_rng(seed)
        self.drift_kick_common_unit=rng.normal(size=self.nodes)
        self.drift_kick_diff_unit=rng.normal(size=self.nodes)

    def drift_kick_node_vector(self, lane: str) -> Array:
        fs=float(self.config.state_full_scale)
        common=float(self.config.drift_kick_common_rms_fraction)*self.drift_kick_common_unit
        diff=float(self.config.drift_kick_diff_rms_fraction)*self.drift_kick_diff_unit
        sign=1.0 if lane.upper() in {"A","C"} else -1.0
        return fs*(common+0.5*sign*diff)

    def clone(self, *, seed: int | None=None) -> "TW1ADriftKickTile":
        cfg=self.config if seed is None else replace(self.config,seed=seed)
        out=TW1ADriftKickTile(self.manifest,cfg,sense_gain=self.sense_gain)
        out.theta=self.theta.copy(); out.fixed_Q=self.fixed_Q.copy(); out._rebuild_programmed_Q()
        if seed is None or seed==self.config.seed: copy_circuit_disorder(self,out)
        return out


def copy_circuit_disorder(src: TW1ADriftKickTile, dst: TW1ADriftKickTile) -> None:
    _copy_kd_disorder(src,dst)
    dst.drift_kick_common_unit=src.drift_kick_common_unit.copy()
    dst.drift_kick_diff_unit=src.drift_kick_diff_unit.copy()
    dst._rebuild_programmed_Q()


class DriftKickInterpreter(KickDriftInterpreter):
    tile: TW1ADriftKickTile

    def _run_forward(self, *, stochastic: bool):
        self._reset_lane_a(); kself,edge_matrix,edge_amounts=self.tile.physical_components()
        inj=self.tile.edge_injection_node_vector("A",edge_amounts); src=self._forward_source_schedule()
        trace=np.zeros(self.tile.steps,dtype=float); esig=self.tile.edge_thermal_sigma_fraction(edge_amounts)
        qdrift=self.tile.drift_kick_node_vector("C")
        for k in range(self.tile.steps):
            z=self.tile.retention*self.a_current; p=self.tile.retention*self.a_previous
            pn=p+kself*z+edge_matrix@z+src[k]+inj
            if stochastic and self.tile.config.edge_ktc_base_fraction>0: pn += _draw_reciprocal_noise(self.tile,esig)
            if stochastic and self.tile.config.self_ktc_base_fraction>0: pn += self.tile.draw_self_thermal_noise(kself)
            pn=self._clip_p(pn); zn=z+pn+qdrift
            if stochastic and self.tile.config.drift_ktc_base_fraction>0: zn += self.tile.draw_drift_thermal_noise()
            self.a_previous,self.a_current=pn,self._clip(zn); trace[k]=self._sense(self.a_current)
        self.forward_trace=trace; return kself,edge_matrix,edge_amounts,inj

    def _clone_and_mirror(self, error_schedule: Array, *, stochastic: bool) -> None:
        z=self.a_current.copy(); p=self.a_previous.copy()
        zm=z-p+self.tile.drift_kick_node_vector("C")
        if stochastic and self.tile.config.drift_ktc_base_fraction>0: zm += self.tile.draw_drift_thermal_noise()
        self.a_current=self._clip(zm); self.a_previous=self._clip_p(-p)
        qT=np.asarray(error_schedule[self.tile.steps],dtype=float)
        self.b_current=self._clip(qT.copy()); self.b_previous=self._clip_p(qT.copy())

    def _run_lockstep_reverse(self,kself: Array,edge_matrix: Array,edge_amounts: Array,*,stochastic: bool) -> Array:
        if self.error_schedule is None: raise RuntimeError("reverse requires error schedule")
        src=self._forward_source_schedule(); qerr=self.error_schedule
        injc=self.tile.edge_injection_node_vector("A",edge_amounts); injd=self.tile.edge_injection_node_vector("B",edge_amounts)
        emc,emd=self.tile.lane_edge_matrices(edge_amounts); esig=self.tile.edge_thermal_sigma_fraction(edge_amounts)
        qc=self.tile.drift_kick_node_vector("C"); qd=self.tile.drift_kick_node_vector("D")
        acc=np.zeros(len(self.tile.trainable)); plus=np.zeros_like(acc); minus=np.zeros_like(acc)
        cret=math.exp(-self.tile.config.credit_accumulator_leakage)
        for j in range(1,self.tile.steps+1):
            dc=self.tile.edge_difference_vector(self.a_current); dd=self.tile.edge_difference_vector(self.b_current)
            pp=self._lcc_square(dc+dd); pm=self._lcc_square(dc-dd)
            plus += pp; minus += pm; acc=cret*acc+0.25*(pp-pm)
            if j==self.tile.steps: continue
            idx=self.tile.steps-j
            cz=self.tile.retention*self.a_current; cp=self.tile.retention*self.a_previous
            dz=self.tile.retention*self.b_current; dp=self.tile.retention*self.b_previous
            cpn=cp+kself*cz+emc@cz+src[idx]+injc
            dpn=dp+kself*dz+emd@dz+qerr[idx]+injd
            if stochastic and self.tile.config.edge_ktc_base_fraction>0:
                cpn += _draw_reciprocal_noise(self.tile,esig); dpn += _draw_reciprocal_noise(self.tile,esig)
            if stochastic and self.tile.config.self_ktc_base_fraction>0:
                cpn += self.tile.draw_self_thermal_noise(kself); dpn += self.tile.draw_self_thermal_noise(kself)
            cpn=self._clip_p(cpn); dpn=self._clip_p(dpn)
            czn=cz+cpn+qc; dzn=dz+dpn+qd
            if stochastic and self.tile.config.drift_ktc_base_fraction>0:
                czn += self.tile.draw_drift_thermal_noise(); dzn += self.tile.draw_drift_thermal_noise()
            self.a_previous,self.a_current=cpn,self._clip(czn)
            self.b_previous,self.b_current=dpn,self._clip(dzn)
        self.plus_energy=plus; self.minus_energy=minus; return acc


def _make_pair(task,config,sense_gain,*,seed_offset):
    tc=replace(config,seed=int(config.seed)+seed_offset); dc=replace(config,seed=int(config.seed)+seed_offset+1)
    t=TW1ADriftKickTile(task["target"],tc,sense_gain=sense_gain); d=TW1ADriftKickTile(task["distractor"],dc,sense_gain=sense_gain)
    copy_circuit_disorder(t,d); _sync_theta(t,d); return t,d


def run_order_contrast_training(task,config:TW1ADriftKickConfig,*,sense_gain:float|None=None,iterations:int=30,step_size:float=0.20,normalize_rms:bool=True,include_shuffle:bool=True,shuffle_seed:int=1729,eps:float=1e-30):
    gain=recommend_sense_gain(task,config) if sense_gain is None else float(sense_gain)
    et,ed=_make_pair(task,config,gain,seed_offset=0); st,sd=_make_pair(task,config,gain,seed_offset=100_003)
    copy_circuit_disorder(et,st); copy_circuit_disorder(et,sd); _sync_theta(et,st); _sync_theta(et,sd)
    eti=DriftKickInterpreter(et); edi=DriftKickInterpreter(ed); sti=DriftKickInterpreter(st); sdi=DriftKickInterpreter(sd)
    et0,ed0,c0=_eval_pair(eti,edi); st0,sd0,sc0=_eval_pair(sti,sdi)
    ec=[c0]; sc=[sc0]; ete=[et0]; ede=[ed0]; ste=[st0]; sde=[sd0]; mt=[]; md=[]; cr=[]
    perm=np.random.default_rng(shuffle_seed).permutation(len(et.theta))
    for _ in range(int(iterations)):
        rt=eti.execute(stochastic_forward=True); rd=edi.execute(stochastic_forward=True)
        a=float(rt["objective"]); b=float(rd["objective"])
        gc=contrast_gradient(a,b,np.asarray(rt["credits"]),np.asarray(rd["credits"]),eps=eps)
        mt.append(a); md.append(b); cr.append(_rms(gc))
        et.apply_credits(-gc,step_size=step_size,normalize_rms=normalize_rms); _sync_theta(et,ed)
        if include_shuffle:
            st.apply_credits(-gc[perm],step_size=step_size,normalize_rms=normalize_rms); _sync_theta(st,sd)
        a,b,c=_eval_pair(eti,edi); x,y,s=_eval_pair(sti,sdi)
        ete.append(a); ede.append(b); ec.append(c); ste.append(x); sde.append(y); sc.append(s)
    return OrderContrastTrainingResult(exact_contrast=ec,shuffled_contrast=sc,exact_target_energy=ete,exact_distractor_energy=ede,shuffled_target_energy=ste,shuffled_distractor_energy=sde,measured_target_energy=mt,measured_distractor_energy=md,combined_credit_rms=cr,final_theta=et.theta.copy(),final_theta_shuffled=st.theta.copy()),gain
