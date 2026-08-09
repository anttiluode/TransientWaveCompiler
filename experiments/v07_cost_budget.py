"""Print an assumption-explicit TW-1A v0.7 area/timing budget."""
from __future__ import annotations

import json
from pathlib import Path

from transientwave.active_summing_budget import (
    CostAssumptions,
    capacitor_area_mm2,
    edge_colored_beta,
    edge_parallel_beta,
    finite_dc_gain_error,
    required_gbw,
    required_open_loop_gain,
    self_packet_beta,
    sram_tape_area_mm2,
    state_cap_area_summary,
)


THERMAL_B = [1e-5, 3e-5]
VFS = [0.5, 1.0, 2.0]
TOPOLOGY_FACTORS = [1.0, 2.0]
MIM_DENSITY = 1.0  # fF/um^2, illustrative only
SRAM_CELL_AREA = 2.5  # um^2/bit, illustrative only
TAPE_STEPS = [210, 500, 1000, 2000, 10000]
EDGE_FS = 0.255
EDGE_COUNT = 112


def main() -> None:
    out = {
        "status": "assumption-explicit-not-foundry-qualified",
        "thermal": [],
        "tape": [],
        "feedback": {},
        "edge_cap_area": [],
    }

    print("STATE CAP THERMAL/AREA SCENARIOS")
    for b in THERMAL_B:
        for vfs in VFS:
            for topo in TOPOLOGY_FACTORS:
                a = CostAssumptions(
                    voltage_full_scale=vfs,
                    topology_noise_factor=topo,
                    mim_density_ff_per_um2=MIM_DENSITY,
                    sram_cell_area_um2=SRAM_CELL_AREA,
                )
                s = state_cap_area_summary(b, a)
                row = {"b": b, "vfs": vfs, "topology_factor": topo, **s}
                out["thermal"].append(row)
                print(
                    f"b={b:.0e} VFS={vfs:g} topo={topo:g} "
                    f"Cstate={s['cstate_f']*1e12:8.3f} pF "
                    f"state-area={s['state_cap_area_mm2']:7.3f} mm2 "
                    f"statecap/tape-cross={s['tape_crossover_steps_state_caps_only']:8.0f} ticks"
                )

    print("\nDIGITAL TAPE AREA SCENARIOS")
    for steps in TAPE_STEPS:
        area = sram_tape_area_mm2(64, steps, 8, SRAM_CELL_AREA)
        row = {"steps": steps, "bits": 64 * steps * 8, "area_mm2": area}
        out["tape"].append(row)
        print(f"T={steps:5d} bits={row['bits']:8d} area={area:7.3f} mm2")

    # Edge capacitor bank area depends on Cstate because Cunit/Cstate is fixed.
    # Every physical edge owns 127 unit capacitors.  This is gross capacitor
    # area before routing/dummies/common-centroid overhead.
    for b in THERMAL_B:
        a = CostAssumptions(
            voltage_full_scale=1.0,
            topology_noise_factor=1.0,
            mim_density_ff_per_um2=MIM_DENSITY,
            sram_cell_area_um2=SRAM_CELL_AREA,
        )
        s = state_cap_area_summary(b, a)
        cstate = s["cstate_f"]
        cunit = cstate * (EDGE_FS / 127.0)
        total_edge_cap = cunit * 127 * EDGE_COUNT
        edge_area = capacitor_area_mm2(total_edge_cap, MIM_DENSITY)
        row = {
            "b": b,
            "vfs": 1.0,
            "cstate_f": cstate,
            "cunit_f": cunit,
            "total_edge_cap_f": total_edge_cap,
            "edge_cap_area_mm2": edge_area,
        }
        out["edge_cap_area"].append(row)
        print(
            f"\nEDGE BANKS b={b:.0e}: Cunit={cunit*1e15:.2f} fF, "
            f"gross 112-bank cap area={edge_area:.3f} mm2"
        )

    beta_parallel = edge_parallel_beta(edge_full_scale=EDGE_FS)
    beta_colored = edge_colored_beta(edge_full_scale=EDGE_FS)
    beta_self = self_packet_beta(self_full_scale=3.0, slices=1)
    beta_self4 = self_packet_beta(self_full_scale=3.0, slices=4)
    aperture = 20e-9
    settle_target = 1e-3
    feedback_rows = {}
    for name, beta in (
        ("four_max_edges_parallel", beta_parallel),
        ("four_color_edge_schedule", beta_colored),
        ("self_direct_plusminus3", beta_self),
        ("self_four_slices", beta_self4),
    ):
        feedback_rows[name] = {
            "beta": beta,
            "gbw_for_0p1pct_20ns_hz": required_gbw(settle_target, beta, aperture),
            "a0_for_0p1pct_static": required_open_loop_gain(1e-3, beta),
            "static_error_at_a0_1e5": finite_dc_gain_error(1e5, beta),
        }
    out["feedback"] = feedback_rows

    print("\nFEEDBACK / OTA FIRST-ORDER TARGETS")
    for name, r in feedback_rows.items():
        print(
            f"{name:26s} beta={r['beta']:.4f} "
            f"GBW@0.1%,20ns={r['gbw_for_0p1pct_20ns_hz']/1e6:7.1f} MHz "
            f"A0@0.1%={r['a0_for_0p1pct_static']:8.0f} "
            f"err(A0=1e5)={r['static_error_at_a0_1e5']:.2e}"
        )

    out["assumptions"] = {
        "mim_density_ff_per_um2": MIM_DENSITY,
        "sram_cell_area_um2": SRAM_CELL_AREA,
        "digital_bits_per_state": 8,
        "analog_differential_state_registers": 256,
        "physical_edges": EDGE_COUNT,
        "edge_full_scale": EDGE_FS,
        "aperture_s": aperture,
        "settling_error_target": settle_target,
        "note": "OTA/credit-integrator/control/routing area and energy are intentionally excluded.",
    }

    Path("v07-cost-budget.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
