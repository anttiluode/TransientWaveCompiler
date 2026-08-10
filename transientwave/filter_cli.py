"""Command-line interface for reciprocal coupling-matrix filter tuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .filter_tuning import (
    parse_filter_spec,
    parse_measurement_nuisance,
    tune_filter_spec,
)
from .touchstone import (
    inject_touchstone_measurement,
    read_touchstone_2port,
)


def _load_json(path: str) -> dict[str, Any]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("filter specification must be a JSON object")
    return obj


def _write_json(path: str, obj: dict[str, Any], *, compact: bool) -> None:
    text = json.dumps(obj, indent=None if compact else 2)
    Path(path).write_text(text + "\n", encoding="utf-8")


def _summary(result: dict[str, Any]) -> str:
    names = result["parameter_order"]
    values = result["final_values"]
    pairs = ", ".join(f"{name}={value:+.8g}" for name, value in zip(names, values))
    lines = [
        (
            f"{result['name']}: loss {result['initial_loss']:.6e} -> "
            f"{result['final_loss']:.6e} "
            f"({result['loss_reduction_factor']:.3e}x reduction)"
        ),
        pairs,
    ]
    nuisance = result.get("nuisance", {})
    if nuisance.get("enabled"):
        nuisance_pairs = ", ".join(
            f"{item['name']}={item['final']:+.8g}"
            for item in nuisance.get("parameters", [])
            if item.get("free")
        )
        if nuisance_pairs:
            lines.append(f"nuisance: {nuisance_pairs}")
    return "\n".join(lines)


def _add_compact_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--compact",
        action="store_true",
        help="when writing JSON, omit pretty indentation",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="twc-filter",
        description="Diagnose constrained reciprocal coupling matrices from complex S parameters.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="fit matrix and optional nuisance parameters to S11/S21 JSON")
    fit.add_argument("spec", help="input JSON specification")
    fit.add_argument("-o", "--output", help="write full result JSON here")
    fit.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the specification without running optimization",
    )
    _add_compact_flag(fit)

    inspect_s2p = sub.add_parser(
        "inspect-s2p",
        help="inspect a 2-port Touchstone S-parameter file without fitting",
    )
    inspect_s2p.add_argument("s2p", help="input .s2p / Touchstone file")

    prepare_s2p = sub.add_parser(
        "prepare-s2p",
        help="inject a Touchstone trace into a topology JSON using an explicit Omega mapping",
    )
    prepare_s2p.add_argument("topology", help="JSON containing model/nodes/parameters and optional nuisance")
    prepare_s2p.add_argument("s2p", help="input .s2p / Touchstone file")
    prepare_s2p.add_argument(
        "--center-hz",
        type=float,
        required=True,
        help="frequency mapped to Omega=0",
    )
    prepare_s2p.add_argument(
        "--scale-hz",
        type=float,
        required=True,
        help="nonzero scale in Omega=(f-center_hz)/scale_hz; may be negative",
    )
    prepare_s2p.add_argument("-o", "--output", required=True, help="write fit-ready JSON here")
    _add_compact_flag(prepare_s2p)

    args = parser.parse_args(argv)

    try:
        if args.command == "inspect-s2p":
            data = read_touchstone_2port(args.s2p)
            print(
                f"{args.s2p}: samples={data.samples}, "
                f"frequency_hz={data.frequency_hz[0]:.9g}..{data.frequency_hz[-1]:.9g}, "
                f"format={data.data_format}, order={data.data_order}, "
                f"reference_ohm={data.reference_ohm:.9g}, version={data.version}"
            )
            return 0

        if args.command == "prepare-s2p":
            topology = _load_json(args.topology)
            data = read_touchstone_2port(args.s2p)
            prepared = inject_touchstone_measurement(
                topology,
                data,
                center_hz=args.center_hz,
                scale_hz=args.scale_hz,
                source=str(args.s2p),
            )
            # Validate the generated object immediately so a bad topology or
            # normalization never gets written as a supposedly fit-ready file.
            parse_filter_spec(prepared)
            _write_json(args.output, prepared, compact=args.compact)
            print(
                f"prepared {args.output}: samples={data.samples}, "
                f"Omega={prepared['omega'][0]:+.6g}..{prepared['omega'][-1]:+.6g}"
            )
            return 0

        if args.command == "fit":
            spec = _load_json(args.spec)
            if args.validate_only:
                nodes, knobs, omega, _s11, _s21, opt = parse_filter_spec(spec)
                nuisance = parse_measurement_nuisance(spec)
                free_nuisance = sum(item.free for item in nuisance.ordered())
                model = "joint-nuisance" if nuisance.enabled else "lossless"
                print(
                    f"valid explicit-port filter spec: nodes={nodes}, "
                    f"knobs={len(knobs)}, samples={len(omega)}, iterations={opt.iterations}, "
                    f"measurement_model={model}, free_nuisance={free_nuisance}"
                )
                return 0

            result = tune_filter_spec(spec)
            print(_summary(result))
            if args.output:
                _write_json(args.output, result, compact=args.compact)
                print(f"wrote {args.output}")
            return 0

        parser.error("unknown command")
        return 2
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
