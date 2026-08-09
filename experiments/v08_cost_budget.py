"""Assumption-explicit v0.8 capacitor subtotal and SRAM-tape crossover report.

This extends the earlier state-cap-only cost sheet with the now-supported edge
and reusable two-slice self capacitor banks. It still intentionally excludes
OTA, credit-integrator, switch, control, routing and calibration overhead.
"""
from __future__ import annotations

import json
from pathlib import Path

from transientwave.active_summing_budget import (
    CostAssumptions,
    capacitor_area_mm2,
    sram_tape_area_mm2,
    state_capacitance_for_ktc,
    tape_crossover_steps,
)


B_VALUES = [1e-5, 3e-5]
VFS_VALUES = [0.5, 1.0, 2.0]
MIM_DENSITY = 1.0       # fF/um^2, illustrative only
SRAM_CELL_AREA = 2.5    # um^2/bit, illustrative only
NODES = 64
STATE_REGS = 256
EDGE_COUNT = 112
EDGE_FS = 0.265
SELF_REUSABLE_BANK_FS = 1.5
BITS_PER_TAPE_STATE = 8
TAPE_STEPS = [210, 500, 1000, 2000, 5000, 10000, 20000]


def main() -> None:
    rows = []
    print("KNOWN CAPACITOR SUBTOTAL (excludes OTA/credit/control/routing)")
    for b in B_VALUES:
        for vfs in VFS_VALUES:
            cstate = state_capacitance_for_ktc(b, vfs, temperature_k=300.0)
            state_cap = STATE_REGS * cstate
            edge_cap = EDGE_COUNT * EDGE_FS * cstate
            self_cap = NODES * SELF_REUSABLE_BANK_FS * cstate
            total = state_cap + edge_cap + self_cap
            state_area = capacitor_area_mm2(state_cap, MIM_DENSITY)
            edge_area = capacitor_area_mm2(edge_cap, MIM_DENSITY)
            self_area = capacitor_area_mm2(self_cap, MIM_DENSITY)
            total_area = capacitor_area_mm2(total, MIM_DENSITY)
            cross = tape_crossover_steps(
                total_area,
                nodes=NODES,
                bits_per_state=BITS_PER_TAPE_STATE,
                sram_cell_area_um2=SRAM_CELL_AREA,
            )
            row = {
                "b": b,
                "effective_vfs_v": vfs,
                "cstate_f": cstate,
                "state_cap_f": state_cap,
                "edge_bank_cap_f": edge_cap,
                "reusable_self_bank_cap_f": self_cap,
                "known_cap_total_f": total,
                "state_cap_area_mm2": state_area,
                "edge_bank_area_mm2": edge_area,
                "self_bank_area_mm2": self_area,
                "known_cap_area_mm2": total_area,
                "known_cap_tape_crossover_steps": cross,
            }
            rows.append(row)
            print(
                f"b={b:.0e} VFS={vfs:g}V Cstate={cstate*1e12:8.3f}pF | "
                f"state={state_area:7.3f} edge={edge_area:7.3f} "
                f"self={self_area:7.3f} total={total_area:7.3f}mm2 | "
                f"tape crossover~{cross:8.0f} ticks"
            )

    print("\nILLUSTRATIVE 8-bit SRAM TAPE")
    tape = []
    for t in TAPE_STEPS:
        area = sram_tape_area_mm2(NODES, t, BITS_PER_TAPE_STATE, SRAM_CELL_AREA)
        tape.append({"steps": t, "area_mm2": area})
        print(f"T={t:6d} area={area:8.3f}mm2")

    out = {
        "status": "assumption-explicit-not-foundry-qualified",
        "architecture": {
            "state_registers": STATE_REGS,
            "physical_edges": EDGE_COUNT,
            "edge_full_scale": EDGE_FS,
            "self_reusable_bank_full_scale_per_node": SELF_REUSABLE_BANK_FS,
            "self_slices": 2,
            "self_working_timing": "20ns transfer + 10ns reset + 20ns transfer, plus nonoverlap",
        },
        "assumptions": {
            "temperature_k": 300.0,
            "mim_density_ff_per_um2": MIM_DENSITY,
            "sram_cell_area_um2": SRAM_CELL_AREA,
            "digital_bits_per_tape_state": BITS_PER_TAPE_STATE,
            "excluded": [
                "OTA area and bias power",
                "credit integrators / square detector",
                "dummy and calibration capacitors",
                "switch area",
                "clock/control SRAM",
                "routing/guard rings",
                "ADC/DAC references and buffers",
            ],
        },
        "known_cap_scenarios": rows,
        "tape_scenarios": tape,
    }
    Path("v08-cost-budget.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
