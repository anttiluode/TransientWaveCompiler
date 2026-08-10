"""Analysis utilities for repeated real-filter diagnosis runs.

The fitter intentionally writes one self-contained JSON result per sweep. This
module treats those result files as an ensemble so a physical experiment can
ask the questions that matter operationally:

- are inferred physical parameters repeatable across untouched sweeps?
- which parameters move after a deliberate physical perturbation?
- did measurement nuisance move instead of the physical matrix?
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class EnsembleParameter:
    name: str
    kind: str
    values: np.ndarray


def _parameter_map(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = result.get("parameters")
    if not isinstance(raw, list) or not raw:
        raise ValueError("fit result has no parameter list")
    mapped: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("fit result parameter entry must be an object")
        name = str(item["name"])
        if name in mapped:
            raise ValueError(f"duplicate result parameter name: {name}")
        mapped[name] = dict(item)
    return mapped


def _nuisance_map(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    nuisance = result.get("nuisance", {})
    if not isinstance(nuisance, Mapping):
        return {}
    raw = nuisance.get("parameters", [])
    if not isinstance(raw, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name", ""))
        if name:
            mapped[name] = dict(item)
    return mapped


def _same_parameter_schema(results: Sequence[Mapping[str, Any]]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    if not results:
        raise ValueError("at least one fit result is required")
    first = _parameter_map(results[0])
    names = list(first)
    for index, result in enumerate(results[1:], start=2):
        current = _parameter_map(result)
        if list(current) != names:
            raise ValueError(f"fit result {index} parameter order/schema does not match the first result")
        for name in names:
            if (int(current[name]["i"]), int(current[name]["j"])) != (
                int(first[name]["i"]),
                int(first[name]["j"]),
            ):
                raise ValueError(f"fit result {index} endpoints differ for parameter {name}")
    return names, first


def _stats(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("ensemble values must be a non-empty finite vector")
    ddof = 1 if values.size > 1 else 0
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=ddof)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "range": float(np.max(values) - np.min(values)),
        "median": float(np.median(values)),
    }


def summarize_fit_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize one repeated-measurement ensemble of fit results."""
    names, schema = _same_parameter_schema(results)
    physical = []
    for name in names:
        values = np.asarray([float(_parameter_map(result)[name]["final"]) for result in results])
        i, j = int(schema[name]["i"]), int(schema[name]["j"])
        row = {
            "name": name,
            "i": i,
            "j": j,
            "kind": "resonator_detuning" if i == j else "reciprocal_coupling",
            "samples": int(len(values)),
            "values": values.tolist(),
            **_stats(values),
        }
        nominal = schema[name].get("nominal")
        if nominal is not None:
            row["nominal"] = float(nominal)
            row["mean_deviation_from_nominal"] = float(row["mean"] - float(nominal))
        physical.append(row)

    nuisance_names = list(_nuisance_map(results[0]))
    nuisance = []
    for name in nuisance_names:
        values = []
        compatible = True
        for result in results:
            mapped = _nuisance_map(result)
            if name not in mapped:
                compatible = False
                break
            values.append(float(mapped[name]["final"]))
        if compatible:
            arr = np.asarray(values, dtype=float)
            nuisance.append(
                {
                    "name": name,
                    "samples": int(len(arr)),
                    "values": arr.tolist(),
                    **_stats(arr),
                }
            )

    losses = np.asarray([float(result["final_loss"]) for result in results], dtype=float)
    return {
        "kind": "twc-filter-ensemble-summary",
        "runs": int(len(results)),
        "names": [str(result.get("name", "filter-fit")) for result in results],
        "physical_parameters": physical,
        "nuisance_parameters": nuisance,
        "final_loss": _stats(losses),
    }


def compare_fit_result_ensembles(
    baseline: Sequence[Mapping[str, Any]],
    perturbed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare untouched and deliberately perturbed repeated-measurement fits."""
    baseline_summary = summarize_fit_results(baseline)
    perturbed_summary = summarize_fit_results(perturbed)

    base_rows = {row["name"]: row for row in baseline_summary["physical_parameters"]}
    pert_rows = {row["name"]: row for row in perturbed_summary["physical_parameters"]}
    if list(base_rows) != list(pert_rows):
        raise ValueError("baseline and perturbed ensembles use different physical parameters")

    shifts = []
    for name in base_rows:
        base = base_rows[name]
        pert = pert_rows[name]
        delta = float(pert["mean"] - base["mean"])
        # Use baseline repeatability as the operational scale. This is not a
        # formal significance test; it is an effect-to-repeatability ratio.
        base_std = float(base["std"])
        ratio = None if base_std <= 0.0 else float(abs(delta) / base_std)
        shifts.append(
            {
                "name": name,
                "i": int(base["i"]),
                "j": int(base["j"]),
                "kind": base["kind"],
                "baseline_mean": float(base["mean"]),
                "baseline_std": base_std,
                "perturbed_mean": float(pert["mean"]),
                "perturbed_std": float(pert["std"]),
                "mean_shift": delta,
                "absolute_mean_shift": float(abs(delta)),
                "shift_over_baseline_std": ratio,
            }
        )

    for kind in {row["kind"] for row in shifts}:
        group = sorted(
            [row for row in shifts if row["kind"] == kind],
            key=lambda row: (-row["absolute_mean_shift"], row["name"]),
        )
        for rank, row in enumerate(group, start=1):
            row["absolute_shift_rank_within_kind"] = int(rank)

    base_n = {row["name"]: row for row in baseline_summary["nuisance_parameters"]}
    pert_n = {row["name"]: row for row in perturbed_summary["nuisance_parameters"]}
    nuisance_shifts = []
    for name in base_n.keys() & pert_n.keys():
        nuisance_shifts.append(
            {
                "name": name,
                "baseline_mean": float(base_n[name]["mean"]),
                "baseline_std": float(base_n[name]["std"]),
                "perturbed_mean": float(pert_n[name]["mean"]),
                "perturbed_std": float(pert_n[name]["std"]),
                "mean_shift": float(pert_n[name]["mean"] - base_n[name]["mean"]),
            }
        )

    shifts.sort(key=lambda row: (row["kind"], row["absolute_shift_rank_within_kind"], row["name"]))
    nuisance_shifts.sort(key=lambda row: row["name"])
    return {
        "kind": "twc-filter-ensemble-comparison",
        "baseline_runs": int(len(baseline)),
        "perturbed_runs": int(len(perturbed)),
        "baseline": baseline_summary,
        "perturbed": perturbed_summary,
        "physical_shifts": shifts,
        "nuisance_shifts": nuisance_shifts,
    }
