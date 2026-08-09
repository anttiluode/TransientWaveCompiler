"""Reversible manifest -> concrete TW-1A logical hardware mapping."""
from __future__ import annotations

from typing import Any

import numpy as np

from .backend import TW1AGridBackend, direct_grid_route
from .compiler import CompileError, compile_program
from .ir import Program


def compile_tw1a(program: Program, backend: TW1AGridBackend | None = None) -> dict[str, Any]:
    """Compile a WaveProgram all the way to the strict TW-1A 8x8 grid backend."""
    b = TW1AGridBackend() if backend is None else backend
    manifest = compile_program(program)

    if len(program.ports) > b.ports:
        raise CompileError(
            "E401 PHYSICAL_PORT_LIMIT",
            f"TW-1A backend exposes {b.ports} ports; program requests {len(program.ports)}",
        )

    Q = np.asarray(manifest["Q"], dtype=float)
    try:
        routing = direct_grid_route(Q, b)
    except ValueError as exc:
        text = str(exc)
        code = "E411 PHYSICAL_COEFFICIENT" if "outside backend range" in text else "E410 ROUTING_FAILURE"
        raise CompileError(code, text) from exc

    allowed = b.allowed_edge_set()
    physical_id = {edge: k for k, edge in enumerate(b.physical_edges())}
    trainable_map = []
    for e in manifest["trainable_edges"]:
        pair = tuple(sorted((int(e["edge"][0]), int(e["edge"][1]))))
        if pair not in allowed:
            raise CompileError(
                "E412 TRAINABLE_EDGE_UNROUTABLE",
                f"trainable edge {pair} is not a direct physical TW-1A grid edge",
            )
        rec = dict(e)
        rec["physical_edge"] = physical_id[pair]
        trainable_map.append(rec)

    manifest["backend"] = "tw1a-8x8-v0"
    manifest["physical"] = {
        **routing,
        "trainable_edge_map": trainable_map,
        "coefficient_limits": {
            "q_edge_min": b.q_edge_min,
            "q_edge_max": b.q_edge_max,
            "q_diag_min": b.q_diag_min,
            "q_diag_max": b.q_diag_max,
        },
    }
    manifest["resources"]["active_propagation_edges"] = routing["active_edges"]
    manifest["resources"]["physical_edge_capacity"] = routing["physical_edge_capacity"]
    manifest["resources"]["unused_physical_edges"] = routing["unused_physical_edges"]
    manifest["resources"]["physical_ports"] = b.ports
    return manifest
