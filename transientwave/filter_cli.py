"""Command-line interface for reciprocal coupling-matrix filter tuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .filter_tuning import parse_filter_spec, tune_filter_spec


def _load_json(path: str) -> dict[str, Any]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("filter specification must be a JSON object")
    return obj


def _summary(result: dict[str, Any]) -> str:
    names = result["parameter_order"]
    values = result["final_values"]
    pairs = ", ".join(f"{name}={value:+.8g}" for name, value in zip(names, values))
    return (
        f"{result['name']}: loss {result['initial_loss']:.6e} -> "
        f"{result['final_loss']:.6e} "
        f"({result['loss_reduction_factor']:.3e}x reduction)\n"
        f"{pairs}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="twc-filter",
        description="Fit a constrained reciprocal coupling matrix to measured complex S parameters.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="fit matrix parameters to measured S11/S21 JSON")
    fit.add_argument("spec", help="input JSON specification")
    fit.add_argument("-o", "--output", help="write full result JSON here")
    fit.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the specification without running optimization",
    )
    fit.add_argument(
        "--compact",
        action="store_true",
        help="when writing JSON, omit pretty indentation",
    )

    args = parser.parse_args(argv)
    if args.command != "fit":
        parser.error("unknown command")

    try:
        spec = _load_json(args.spec)
        if args.validate_only:
            nodes, knobs, omega, _s11, _s21, opt = parse_filter_spec(spec)
            print(
                f"valid explicit-port filter spec: nodes={nodes}, "
                f"knobs={len(knobs)}, samples={len(omega)}, iterations={opt.iterations}"
            )
            return 0

        result = tune_filter_spec(spec)
        print(_summary(result))
        if args.output:
            text = json.dumps(result, indent=None if args.compact else 2)
            Path(args.output).write_text(text + "\n", encoding="utf-8")
            print(f"wrote {args.output}")
        return 0
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
