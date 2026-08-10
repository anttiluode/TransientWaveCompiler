"""Command-line interface for reciprocal coupling-matrix filter tuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .filter_analysis import compare_fit_result_ensembles, summarize_fit_results
from .filter_tuning import (
    parse_filter_spec,
    parse_measurement_nuisance,
    tune_filter_spec,
)
from .touchstone import (
    inject_touchstone_bandpass_measurement,
    inject_touchstone_measurement,
    read_touchstone_2port,
)


def _load_json(path: str) -> dict[str, Any]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("filter specification/result must be a JSON object")
    return obj


def _load_many(paths: list[str]) -> list[dict[str, Any]]:
    if not paths:
        raise ValueError("at least one result JSON is required")
    return [_load_json(path) for path in paths]


def _write_json(path: str, obj: dict[str, Any], *, compact: bool) -> None:
    text = json.dumps(obj, indent=None if compact else 2)
    Path(path).write_text(text + "\n", encoding="utf-8")


def _format_hz(value: float) -> str:
    a = abs(value)
    if a >= 1e9:
        return f"{value / 1e9:+.6g} GHz"
    if a >= 1e6:
        return f"{value / 1e6:+.6g} MHz"
    if a >= 1e3:
        return f"{value / 1e3:+.6g} kHz"
    return f"{value:+.6g} Hz"


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

    diagnosis_parts = []
    for row in result.get("diagnosis", []):
        part = f"{row['name']}={row['deviation_normalized']:+.6g} from nominal"
        if row.get("deviation_percent") is not None:
            part += f" ({row['deviation_percent']:+.3f}%)"
        if row.get("resonance_deviation_hz") is not None:
            part += f" [resonance {_format_hz(float(row['resonance_deviation_hz']))}]"
        diagnosis_parts.append(part)
    if diagnosis_parts:
        lines.append("diagnosis: " + "; ".join(diagnosis_parts))
    return "\n".join(lines)


def _ensemble_summary_text(summary: dict[str, Any]) -> str:
    lines = [f"runs={summary['runs']}"]
    for row in summary["physical_parameters"]:
        lines.append(
            f"{row['name']}: mean={row['mean']:+.8g} std={row['std']:.3e} "
            f"range={row['range']:.3e}"
        )
    if summary["nuisance_parameters"]:
        lines.append("nuisance:")
        for row in summary["nuisance_parameters"]:
            lines.append(
                f"  {row['name']}: mean={row['mean']:+.8g} std={row['std']:.3e} "
                f"range={row['range']:.3e}"
            )
    return "\n".join(lines)


def _comparison_text(result: dict[str, Any]) -> str:
    lines = [
        f"baseline_runs={result['baseline_runs']} perturbed_runs={result['perturbed_runs']}",
        "physical shifts:",
    ]
    for row in result["physical_shifts"]:
        ratio = row["shift_over_baseline_std"]
        ratio_text = "inf/undefined" if ratio is None else f"{ratio:.3g}x baseline_std"
        lines.append(
            f"  {row['name']}: shift={row['mean_shift']:+.8g} "
            f"rank[{row['kind']}]={row['absolute_shift_rank_within_kind']} "
            f"({ratio_text})"
        )
    if result["nuisance_shifts"]:
        lines.append("nuisance shifts:")
        for row in result["nuisance_shifts"]:
            lines.append(f"  {row['name']}: shift={row['mean_shift']:+.8g}")
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
        help="inject a Touchstone trace into a topology JSON with an explicit Omega normalization",
    )
    prepare_s2p.add_argument("topology", help="JSON containing model/nodes/parameters and optional nuisance")
    prepare_s2p.add_argument("s2p", help="input .s2p / Touchstone file")
    prepare_s2p.add_argument(
        "--center-hz",
        type=float,
        required=True,
        help="filter center frequency mapped to Omega=0",
    )
    normalization = prepare_s2p.add_mutually_exclusive_group(required=True)
    normalization.add_argument(
        "--bandwidth-hz",
        type=float,
        help="use classical bandpass Omega=(f0/BW)*(f/f0-f0/f)",
    )
    normalization.add_argument(
        "--scale-hz",
        type=float,
        help="use linear Omega=(f-center_hz)/scale_hz; scale may be negative",
    )
    prepare_s2p.add_argument(
        "--omega-sign",
        type=float,
        choices=[-1.0, 1.0],
        default=1.0,
        help="sign convention for --bandwidth-hz normalization (default +1)",
    )
    prepare_s2p.add_argument("-o", "--output", required=True, help="write fit-ready JSON here")
    _add_compact_flag(prepare_s2p)

    summarize = sub.add_parser(
        "summarize-results",
        help="summarize repeatability across independently fitted sweep result JSON files",
    )
    summarize.add_argument("results", nargs="+", help="fit result JSON files from repeated sweeps")
    summarize.add_argument("-o", "--output", help="write ensemble summary JSON here")
    _add_compact_flag(summarize)

    compare = sub.add_parser(
        "compare-results",
        help="compare baseline and deliberately perturbed fit-result ensembles",
    )
    compare.add_argument(
        "--baseline",
        nargs="+",
        required=True,
        help="baseline fit result JSON files (shell globs may expand here)",
    )
    compare.add_argument(
        "--perturbed",
        nargs="+",
        required=True,
        help="perturbed fit result JSON files",
    )
    compare.add_argument("-o", "--output", help="write comparison JSON here")
    _add_compact_flag(compare)

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
            if args.bandwidth_hz is not None:
                prepared = inject_touchstone_bandpass_measurement(
                    topology,
                    data,
                    center_hz=args.center_hz,
                    bandwidth_hz=args.bandwidth_hz,
                    omega_sign=args.omega_sign,
                    source=str(args.s2p),
                )
            else:
                prepared = inject_touchstone_measurement(
                    topology,
                    data,
                    center_hz=args.center_hz,
                    scale_hz=args.scale_hz,
                    source=str(args.s2p),
                )
            parse_filter_spec(prepared)
            _write_json(args.output, prepared, compact=args.compact)
            mapping = prepared["measurement_source"]["omega_mapping"]["mode"]
            print(
                f"prepared {args.output}: samples={data.samples}, mapping={mapping}, "
                f"Omega={prepared['omega'][0]:+.6g}..{prepared['omega'][-1]:+.6g}"
            )
            return 0

        if args.command == "summarize-results":
            result = summarize_fit_results(_load_many(args.results))
            print(_ensemble_summary_text(result))
            if args.output:
                _write_json(args.output, result, compact=args.compact)
                print(f"wrote {args.output}")
            return 0

        if args.command == "compare-results":
            result = compare_fit_result_ensembles(
                _load_many(args.baseline),
                _load_many(args.perturbed),
            )
            print(_comparison_text(result))
            if args.output:
                _write_json(args.output, result, compact=args.compact)
                print(f"wrote {args.output}")
            return 0

        if args.command == "fit":
            spec = _load_json(args.spec)
            if args.validate_only:
                nodes, knobs, omega, _s11, _s21, opt = parse_filter_spec(spec)
                nuisance = parse_measurement_nuisance(spec)
                free_nuisance = sum(item.free for item in nuisance.ordered())
                model = "joint-nuisance" if nuisance.enabled else "lossless"
                nominal_count = sum(knob.nominal is not None for knob in knobs)
                print(
                    f"valid explicit-port filter spec: nodes={nodes}, "
                    f"knobs={len(knobs)}, samples={len(omega)}, iterations={opt.iterations}, "
                    f"measurement_model={model}, free_nuisance={free_nuisance}, "
                    f"nominal_knobs={nominal_count}"
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
