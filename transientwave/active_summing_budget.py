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


def state_capacitance_for_ktc(
    base_fraction: float,
    voltage_full_scale: float,
    *,
    temperature_k: float = 300.0,
    topology_noise_factor: float = 1.0,
) -> float:
    """Effective state capacitance in F for sqrt(f*kT/C)/VFS <= b.

    ``topology_noise_factor`` keeps differential/common-mode implementation
    uncertainty explicit. Use 1 for the scalar emulator law; larger values
    conservatively represent extra independent sampled-noise contributions.
    """
    b = float(base_fraction)
    v = float(voltage_full_scale)
    t = float(temperature_k)
    f = float(topology_noise_factor)
    if b <= 0 or v <= 0 or t <= 0 or f <= 0:
        raise ValueError("thermal sizing arguments must be positive")
    return f * K_B * t / (b * v) ** 2


def thermal_capacitance_ratio(reference_b: float, candidate_b: float) -> float:
    """Candidate/reference kT/C capacitance at fixed VFS, T and topology.

    Since C is proportional to 1/b^2,

        C_candidate / C_reference = (b_reference / b_candidate)^2.
    """
    b0 = float(reference_b)
    b1 = float(candidate_b)
    if b0 <= 0 or b1 <= 0 or not math.isfinite(b0) or not math.isfinite(b1):
        raise ValueError("thermal bases must be finite and positive")
    return (b0 / b1) ** 2


def averaged_echo_ideal_cap_energy_ratio(
    reference_b: float,
    candidate_b: float,
    repeats_per_update: int,
) -> float:
    """Ideal sampled-cap switching-work ratio for an averaging trade.

    This is deliberately only the C*V^2-like capacitor term. It assumes the
    same voltage swing and switching activity per physical echo and compares
    one reference echo/update with ``repeats_per_update`` candidate echoes.
    OTA, clock, converter, reference and credit-path energy are excluded.
    """
    m = int(repeats_per_update)
    if m < 1:
        raise ValueError("repeats_per_update must be >=1")
    return m * thermal_capacitance_ratio(reference_b, candidate_b)


def feedback_factor(total_input_cap_over_cstate: float) -> float:
    """First-order capacitive feedback factor beta=Cf/(Cf+Cin)."""
    load = float(total_input_cap_over_cstate)
    if load < 0 or not math.isfinite(load):
        raise ValueError("normalized input capacitance must be finite and nonnegative")
    return 1.0 / (1.0 + load)


def finite_dc_gain_error(open_loop_gain: float, beta: float) -> float:
    """First-order closed-loop fractional gain error 1/(1+A0*beta)."""
    a0 = float(open_loop_gain)
    b = float(beta)
    if a0 <= 0 or not 0 < b <= 1:
        raise ValueError("A0 must be positive and beta in (0,1]")
    return 1.0 / (1.0 + a0 * b)


def required_open_loop_gain(max_fractional_error: float, beta: float) -> float:
    err = float(max_fractional_error)
    b = float(beta)
    if not 0 < err < 1 or not 0 < b <= 1:
        raise ValueError("error and beta must lie in (0,1)")
    return (1.0 / err - 1.0) / b


def settling_error(gbw_hz: float, beta: float, aperture_s: float) -> float:
    """One-pole residual exp(-2*pi*GBW*beta*t)."""
    g = float(gbw_hz)
    b = float(beta)
    t = float(aperture_s)
    if g <= 0 or t <= 0 or not 0 < b <= 1:
        raise ValueError("GBW/aperture must be positive and beta in (0,1]")
    return math.exp(-2.0 * math.pi * g * b * t)


def required_gbw(max_settling_error: float, beta: float, aperture_s: float) -> float:
    err = float(max_settling_error)
    b = float(beta)
    t = float(aperture_s)
    if not 0 < err < 1 or not 0 < b <= 1 or t <= 0:
        raise ValueError("invalid settling budget")
    return -math.log(err) / (2.0 * math.pi * b * t)


def edge_parallel_beta(*, degree: int = 4, edge_full_scale: float = 0.255) -> float:
    return feedback_factor(int(degree) * float(edge_full_scale))


def edge_colored_beta(*, edge_full_scale: float = 0.255) -> float:
    """Four-color grid schedule: at most one incident edge loads a node."""
    return feedback_factor(float(edge_full_scale))


def self_packet_beta(*, self_full_scale: float = 3.0, slices: int = 1) -> float:
    """Feedback factor if the self coefficient is delivered in equal slices."""
    if int(slices) < 1:
        raise ValueError("slices must be >=1")
    return feedback_factor(float(self_full_scale) / int(slices))


def capacitor_area_mm2(total_cap_f: float, mim_density_ff_per_um2: float) -> float:
    c = float(total_cap_f)
    d = float(mim_density_ff_per_um2)
    if c < 0 or d <= 0:
        raise ValueError("capacitance must be nonnegative and density positive")
    return (c / 1e-15) / d / 1e6


def sram_tape_area_mm2(
    nodes: int,
    steps: int,
    bits_per_state: int,
    sram_cell_area_um2: float,
) -> float:
    if min(int(nodes), int(steps), int(bits_per_state)) < 1:
        raise ValueError("nodes, steps and bits must be positive")
    area = int(nodes) * int(steps) * int(bits_per_state) * float(sram_cell_area_um2)
    return area / 1e6


def tape_crossover_steps(
    analog_area_mm2: float,
    *,
    nodes: int,
    bits_per_state: int,
    sram_cell_area_um2: float,
) -> float:
    denom = int(nodes) * int(bits_per_state) * float(sram_cell_area_um2)
    if analog_area_mm2 < 0 or denom <= 0:
        raise ValueError("invalid crossover arguments")
    return float(analog_area_mm2) * 1e6 / denom


def capacitor_switch_energy_j(cap_f: float, voltage_step: float) -> float:
    """Ideal lower-bound 1/2 C dV^2 for one sampled-cap transition."""
    c = float(cap_f)
    v = float(voltage_step)
    if c < 0:
        raise ValueError("capacitance must be nonnegative")
    return 0.5 * c * v * v


@dataclass(frozen=True)
class CostAssumptions:
    nodes: int = 64
    reverse_contexts: int = 2
    temporal_generations: int = 2
    bits_per_digital_state: int = 8
    mim_density_ff_per_um2: float = 1.0
    sram_cell_area_um2: float = 2.5
    voltage_full_scale: float = 1.0
    temperature_k: float = 300.0
    topology_noise_factor: float = 1.0

    @property
    def differential_state_registers(self) -> int:
        return self.nodes * self.reverse_contexts * self.temporal_generations


def state_cap_area_summary(
    base_fraction: float,
    assumptions: CostAssumptions = CostAssumptions(),
) -> dict[str, float]:
    cstate = state_capacitance_for_ktc(
        base_fraction,
        assumptions.voltage_full_scale,
        temperature_k=assumptions.temperature_k,
        topology_noise_factor=assumptions.topology_noise_factor,
    )
    total = cstate * assumptions.differential_state_registers
    area = capacitor_area_mm2(total, assumptions.mim_density_ff_per_um2)
    cross = tape_crossover_steps(
        area,
        nodes=assumptions.nodes,
        bits_per_state=assumptions.bits_per_digital_state,
        sram_cell_area_um2=assumptions.sram_cell_area_um2,
    )
    return {
        "cstate_f": cstate,
        "state_registers": float(assumptions.differential_state_registers),
        "total_state_cap_f": total,
        "state_cap_area_mm2": area,
        "tape_crossover_steps_state_caps_only": cross,
    }
