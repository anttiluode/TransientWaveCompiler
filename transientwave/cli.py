"""Command-line interface for TransientWaveCompiler."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compiler import CompileError, compile_json_file


def main() -> None:
    ap = argparse.ArgumentParser(prog="twc", description="Compile WaveProgram JSON to a TW-1 manifest")
    ap.add_argument("input", help="WaveProgram JSON")
    ap.add_argument("-o", "--output", help="Output manifest JSON; defaults to stdout")
    ap.add_argument("--indent", type=int, default=2)
    args = ap.parse_args()

    try:
        manifest = compile_json_file(args.input)
    except (CompileError, ValueError, KeyError, json.JSONDecodeError) as exc:
        ap.error(str(exc))
        return

    text = json.dumps(manifest, indent=args.indent, allow_nan=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        s = manifest["stability"]
        r = manifest["resources"]
        print(
            f"compiled {manifest['program']}: {r['nodes']} nodes, "
            f"{r['trainable_edges']} trainable edges, {r['tiles']} tile(s), "
            f"eig=[{s['eigenvalue_min']:.6g},{s['eigenvalue_max']:.6g}]"
        )
    else:
        print(text)


if __name__ == "__main__":
    main()
