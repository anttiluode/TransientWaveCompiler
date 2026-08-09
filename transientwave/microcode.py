"""High-level TW-1 controller command stream generation.

This is intentionally not a binary ISA encoder. It is the stable semantic command
stream that a concrete device driver/RTL controller can lower further.
"""
from __future__ import annotations

from typing import Any


def inference_microcode(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    T = int(manifest["steps"])
    output = manifest["objective"]["port"]
    return [
        {"op": "RESET_STATE"},
        {"op": "SET_MODE", "mode": "FORWARD"},
        {"op": "RUN", "ticks": T, "port_schedule": "forward"},
        {"op": "READ_OBJECTIVE", "port": output},
    ]


def training_microcode(manifest: dict[str, Any], terminal_snapshot: bool = False) -> list[dict[str, Any]]:
    T = int(manifest["steps"])
    output = manifest["objective"]["port"]

    code: list[dict[str, Any]] = [
        {"op": "CREDIT_CLEAR", "target": "all"},
        {"op": "RESET_STATE"},
        {"op": "SET_MODE", "mode": "FORWARD"},
        {"op": "RUN", "ticks": T, "port_schedule": "forward"},
        {"op": "READ_OBJECTIVE", "port": output},
        {"op": "FREEZE"},
    ]

    if terminal_snapshot:
        code.append({"op": "SNAPSHOT_TERMINAL"})

    code += [
        {"op": "SET_MODE", "mode": "REVERSE_PLUS"},
        {"op": "CREDIT_PHASE", "sign": "PLUS"},
        {"op": "MIRROR_ARM"},
        {"op": "RUN", "ticks": T, "port_schedule": "error_plus_reverse"},
    ]

    if terminal_snapshot:
        code += [
            {"op": "RESTORE_TERMINAL"},
        ]
    else:
        code += [
            {"op": "RESET_STATE"},
            {"op": "SET_MODE", "mode": "FORWARD"},
            {"op": "RUN", "ticks": T, "port_schedule": "forward"},
            {"op": "FREEZE"},
        ]

    code += [
        {"op": "SET_MODE", "mode": "REVERSE_MINUS"},
        {"op": "CREDIT_PHASE", "sign": "MINUS"},
        {"op": "MIRROR_ARM"},
        {"op": "RUN", "ticks": T, "port_schedule": "error_minus_reverse"},
        {"op": "READ_CREDIT", "target": "all"},
    ]

    return code


def attach_microcode(manifest: dict[str, Any], terminal_snapshot: bool = False) -> dict[str, Any]:
    out = dict(manifest)
    out["microcode"] = {
        "inference": inference_microcode(manifest),
        "training": training_microcode(manifest, terminal_snapshot=terminal_snapshot),
        "terminal_snapshot": bool(terminal_snapshot),
    }
    return out
