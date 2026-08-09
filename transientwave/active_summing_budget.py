"""Process-parameterized C1 feedback, thermal, area and energy budgets.

Nothing in this module is a foundry claim. It converts explicit assumptions
into auditable numbers so MIM density, SRAM-cell area, state voltage, topology
factor, amplifier targets and time/area trades can be changed without rewriting
prose.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


K_B = 1.380649e-23


def state_capacitance_for_ktc(base_fraction: float, voltage_full_scale: float, *, temperature_k: float=300.0, topology_noise_factor: float=1.0) -> float:
    b=float(base_fraction); v=float(voltage_full_scale); t=float(temperature_k); f=float(topology_noise_factor)
    if b<=0 or v<=0 or t<=0 or f<=0: raise ValueError("thermal sizing arguments must be positive")
    return f*K_B*t/(b*v)**2


def thermal_capacitance_ratio(reference_b: float, candidate_b: float) -> float:
    b0=float(reference_b); b1=float(candidate_b)
    if b0<=0 or b1<=0 or not math.isfinite(b0) or not math.isfinite(b1): raise ValueError("thermal bases must be finite and positive")
    return (b0/b1)**2


def averaged_echo_ideal_cap_energy_ratio(reference_b: float,candidate_b: float,repeats_per_update: int)->float:
    m=int(repeats_per_update)
    if m<1: raise ValueError("repeats_per_update must be >=1")
    return m*thermal_capacitance_ratio(reference_b,candidate_b)


def v08_known_cap_factor(*, nodes:int=64, reverse_contexts:int=2, temporal_generations:int=2, edge_count:int=112, edge_full_scale:float=0.265, reusable_self_full_scale:float=1.5)->float:
    """Known provisioned-capacitance multiple of Cstate for qualified v0.8."""
    return float(nodes*reverse_contexts*temporal_generations + edge_count*edge_full_scale + nodes*reusable_self_full_scale)


def kick_drift_known_cap_factor(*, nodes:int=64, reverse_contexts:int=2, state_vectors_per_context:int=2, edge_count:int=112, edge_full_scale:float=0.265, kick_self_full_scale:float=0.125, drift_sample_cap_over_cstate:float=1.0)->float:
    """Known v0.9 kick-drift capacitor multiple before active-circuit overhead.

    Counts Z/P state banks, reciprocal edge banks, one residual-self bank per
    node and one reusable drift sample capacitor per physical node.  It does
    not count OTA, LCC/credit, dummies, calibration caps, references or routing.
    """
    vals=(nodes,reverse_contexts,state_vectors_per_context,edge_count)
    if any(int(v)<1 for v in vals): raise ValueError("resource counts must be positive")
    if edge_full_scale<0 or kick_self_full_scale<0 or drift_sample_cap_over_cstate<0: raise ValueError("cap ratios must be nonnegative")
    return float(nodes*reverse_contexts*state_vectors_per_context + edge_count*edge_full_scale + nodes*kick_self_full_scale + nodes*drift_sample_cap_over_cstate)


def architecture_cap_area_ratio(*, reference_factor:float, candidate_factor:float, reference_b:float, candidate_b:float)->float:
    """Known-cap area ratio including both topology factor and kT/C scaling."""
    if reference_factor<=0 or candidate_factor<0: raise ValueError("cap factors must be positive/nonnegative")
    return float(candidate_factor/reference_factor)*thermal_capacitance_ratio(reference_b,candidate_b)


def feedback_factor(total_input_cap_over_cstate: float)->float:
    load=float(total_input_cap_over_cstate)
    if load<0 or not math.isfinite(load): raise ValueError("normalized input capacitance must be finite and nonnegative")
    return 1.0/(1.0+load)


def finite_dc_gain_error(open_loop_gain:float,beta:float)->float:
    a0=float(open_loop_gain); b=float(beta)
    if a0<=0 or not 0<b<=1: raise ValueError("A0 must be positive and beta in (0,1]")
    return 1.0/(1.0+a0*b)


def required_open_loop_gain(max_fractional_error:float,beta:float)->float:
    err=float(max_fractional_error); b=float(beta)
    if not 0<err<1 or not 0<b<=1: raise ValueError("error and beta must lie in (0,1)")
    return (1.0/err-1.0)/b


def settling_error(gbw_hz:float,beta:float,aperture_s:float)->float:
    g=float(gbw_hz); b=float(beta); t=float(aperture_s)
    if g<=0 or t<=0 or not 0<b<=1: raise ValueError("GBW/aperture must be positive and beta in (0,1]")
    return math.exp(-2.0*math.pi*g*b*t)


def required_gbw(max_settling_error:float,beta:float,aperture_s:float)->float:
    err=float(max_settling_error); b=float(beta); t=float(aperture_s)
    if not 0<err<1 or not 0<b<=1 or t<=0: raise ValueError("invalid settling budget")
    return -math.log(err)/(2.0*math.pi*b*t)


def edge_parallel_beta(*,degree:int=4,edge_full_scale:float=0.255)->float: return feedback_factor(int(degree)*float(edge_full_scale))
def edge_colored_beta(*,edge_full_scale:float=0.255)->float: return feedback_factor(float(edge_full_scale))
def self_packet_beta(*,self_full_scale:float=3.0,slices:int=1)->float:
    if int(slices)<1: raise ValueError("slices must be >=1")
    return feedback_factor(float(self_full_scale)/int(slices))


def capacitor_area_mm2(total_cap_f:float,mim_density_ff_per_um2:float)->float:
    c=float(total_cap_f); d=float(mim_density_ff_per_um2)
    if c<0 or d<=0: raise ValueError("capacitance must be nonnegative and density positive")
    return (c/1e-15)/d/1e6


def sram_tape_area_mm2(nodes:int,steps:int,bits_per_state:int,sram_cell_area_um2:float)->float:
    if min(int(nodes),int(steps),int(bits_per_state))<1: raise ValueError("nodes, steps and bits must be positive")
    return int(nodes)*int(steps)*int(bits_per_state)*float(sram_cell_area_um2)/1e6


def tape_crossover_steps(analog_area_mm2:float,*,nodes:int,bits_per_state:int,sram_cell_area_um2:float)->float:
    denom=int(nodes)*int(bits_per_state)*float(sram_cell_area_um2)
    if analog_area_mm2<0 or denom<=0: raise ValueError("invalid crossover arguments")
    return float(analog_area_mm2)*1e6/denom


def capacitor_switch_energy_j(cap_f:float,voltage_step:float)->float:
    c=float(cap_f); v=float(voltage_step)
    if c<0: raise ValueError("capacitance must be nonnegative")
    return 0.5*c*v*v


@dataclass(frozen=True)
class CostAssumptions:
    nodes:int=64; reverse_contexts:int=2; temporal_generations:int=2; bits_per_digital_state:int=8
    mim_density_ff_per_um2:float=1.0; sram_cell_area_um2:float=2.5; voltage_full_scale:float=1.0
    temperature_k:float=300.0; topology_noise_factor:float=1.0
    @property
    def differential_state_registers(self)->int: return self.nodes*self.reverse_contexts*self.temporal_generations


def state_cap_area_summary(base_fraction:float,assumptions:CostAssumptions=CostAssumptions())->dict[str,float]:
    cstate=state_capacitance_for_ktc(base_fraction,assumptions.voltage_full_scale,temperature_k=assumptions.temperature_k,topology_noise_factor=assumptions.topology_noise_factor)
    total=cstate*assumptions.differential_state_registers; area=capacitor_area_mm2(total,assumptions.mim_density_ff_per_um2)
    cross=tape_crossover_steps(area,nodes=assumptions.nodes,bits_per_state=assumptions.bits_per_digital_state,sram_cell_area_um2=assumptions.sram_cell_area_um2)
    return {"cstate_f":cstate,"state_registers":float(assumptions.differential_state_registers),"total_state_cap_f":total,"state_cap_area_mm2":area,"tape_crossover_steps_state_caps_only":cross}
