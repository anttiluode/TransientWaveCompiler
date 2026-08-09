"""Strict WaveProgram -> TW-1A hardware manifest command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compiler import CompileError
from .ir import program_from_dict
from .physical import compile_tw1a


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="twc-tw1a",
        description="Compile WaveProgram JSON through the strict TW-1A 8x8 hardware backend",
    )
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        manifest = compile_tw1a(program_from_dict(data))
    except (CompileError, ValueError, KeyError, json.JSONDecodeError) as exc:
        ap.error(str(exc))
        return

    text = json.dumps(manifest, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        p = manifest["physical"]
        print(
            f"TW-1A routed {manifest['program']}: "
            f"{manifest['resources']['nodes']} nodes, {p['active_edges']}/{p['physical_edge_capacity']} propagation edges"
        )
    else:
        print(text)


if __name__ == "__main__":
    main()
