"""Small, dependency-free Touchstone 2-port reader for measured filter traces.

The parser intentionally supports the subset TWC needs for real VNA work:

- 2-port S-parameter files;
- Touchstone 1.x ``.s2p`` and the ordinary Touchstone 2.0 network-data form;
- RI, MA, and DB value formats;
- both 2.0 data-order conventions;
- full matrices (plus reciprocal lower/upper 2-port matrices).

It preserves physical frequency in hertz. Conversion to TWC's normalized
``Omega`` is explicit and deliberately separate from parsing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


_FREQUENCY_SCALE = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
}


@dataclass(frozen=True)
class Touchstone2Port:
    frequency_hz: np.ndarray
    s11: np.ndarray
    s21: np.ndarray
    s12: np.ndarray
    s22: np.ndarray
    reference_ohm: float
    frequency_unit: str
    data_format: str
    data_order: str
    version: str

    @property
    def samples(self) -> int:
        return int(len(self.frequency_hz))


def _strip_comment(line: str) -> str:
    return line.split("!", 1)[0].strip()


def _parse_option_line(line: str) -> tuple[str, str, str, float]:
    tokens = line[1:].strip().lower().split()
    frequency_unit = "ghz"
    parameter = "s"
    data_format = "ma"
    reference_ohm = 50.0

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _FREQUENCY_SCALE:
            frequency_unit = token
        elif token in {"s", "y", "z", "g", "h"}:
            parameter = token
        elif token in {"ri", "ma", "db"}:
            data_format = token
        elif token == "r":
            if i + 1 >= len(tokens):
                raise ValueError("Touchstone option line has R without a reference value")
            reference_ohm = float(tokens[i + 1])
            i += 1
        else:
            raise ValueError(f"unsupported Touchstone option token: {token!r}")
        i += 1

    if parameter != "s":
        raise ValueError("twc-filter currently accepts Touchstone S-parameters only")
    if not np.isfinite(reference_ohm) or reference_ohm <= 0:
        raise ValueError("Touchstone reference resistance must be positive")
    return frequency_unit, parameter, data_format, reference_ohm


def _pair(a: float, b: float, data_format: str) -> complex:
    if data_format == "ri":
        return complex(a, b)
    angle = np.deg2rad(float(b))
    if data_format == "ma":
        magnitude = float(a)
    elif data_format == "db":
        magnitude = 10.0 ** (float(a) / 20.0)
    else:
        raise ValueError(f"unsupported Touchstone data format: {data_format}")
    return complex(magnitude * np.cos(angle), magnitude * np.sin(angle))


def _decode_record(
    values: list[float],
    *,
    frequency_scale: float,
    data_format: str,
    data_order: str,
    matrix_format: str,
) -> tuple[float, complex, complex, complex, complex]:
    if matrix_format == "full":
        if len(values) != 9:
            raise ValueError(f"full two-port Touchstone record requires 9 values, got {len(values)}")
        frequency = float(values[0]) * frequency_scale
        pairs = [
            _pair(values[1], values[2], data_format),
            _pair(values[3], values[4], data_format),
            _pair(values[5], values[6], data_format),
            _pair(values[7], values[8], data_format),
        ]
        if data_order == "21_12":
            s11, s21, s12, s22 = pairs
        elif data_order == "12_21":
            s11, s12, s21, s22 = pairs
        else:
            raise ValueError(f"unsupported Touchstone two-port order: {data_order}")
        return frequency, s11, s21, s12, s22

    if matrix_format in {"lower", "upper"}:
        if len(values) != 7:
            raise ValueError(
                f"{matrix_format} two-port Touchstone record requires 7 values, got {len(values)}"
            )
        frequency = float(values[0]) * frequency_scale
        s11 = _pair(values[1], values[2], data_format)
        s21 = _pair(values[3], values[4], data_format)
        s22 = _pair(values[5], values[6], data_format)
        return frequency, s11, s21, s21, s22

    raise ValueError(f"unsupported Touchstone matrix format: {matrix_format}")


def parse_touchstone_2port_text(text: str) -> Touchstone2Port:
    lines = text.splitlines()
    version = "1.0"
    number_of_ports: int | None = None
    data_order: str | None = None
    matrix_format = "full"
    option: tuple[str, str, str, float] | None = None
    reference_values: list[float] | None = None
    in_network_data = False
    saw_network_keyword = False
    numeric_lines_v1: list[list[float]] = []
    numeric_tokens_v2: list[float] = []

    for raw_line in lines:
        line = _strip_comment(raw_line)
        if not line:
            continue
        lower = line.lower()

        if lower.startswith("[version]"):
            parts = line.split()
            if len(parts) != 2:
                raise ValueError("Touchstone [Version] requires one value")
            version = parts[1]
            continue

        if line.startswith("#"):
            if option is None:
                option = _parse_option_line(line)
            continue

        if lower.startswith("[number of ports]"):
            number_of_ports = int(line.split("]", 1)[1].strip())
            continue

        if lower.startswith("[two-port data order]"):
            data_order = line.split("]", 1)[1].strip().lower()
            continue

        if lower.startswith("[matrix format]"):
            matrix_format = line.split("]", 1)[1].strip().lower()
            continue

        if lower.startswith("[reference]"):
            tail = line.split("]", 1)[1].strip()
            reference_values = [float(token) for token in tail.split()] if tail else []
            continue

        if lower == "[network data]":
            saw_network_keyword = True
            in_network_data = True
            continue

        if lower in {"[noise data]", "[end]"}:
            in_network_data = False
            if lower == "[end]":
                break
            continue

        if line.startswith("["):
            # Other v2 metadata keywords do not contain network samples.
            continue

        try:
            values = [float(token) for token in line.split()]
        except ValueError as exc:
            raise ValueError(f"non-numeric Touchstone network line: {line!r}") from exc

        if version.startswith("2") or saw_network_keyword:
            if in_network_data:
                numeric_tokens_v2.extend(values)
        else:
            # Version 1.x: full two-port network data is one 9-value record per
            # line. A following 5-value noise-data row is outside our scope.
            if len(values) == 9:
                numeric_lines_v1.append(values)
            elif len(values) == 5 and numeric_lines_v1:
                break
            else:
                raise ValueError(
                    f"unsupported Touchstone 1.x two-port data line with {len(values)} values"
                )

    if option is None:
        option = ("ghz", "s", "ma", 50.0)
    frequency_unit, _parameter, data_format, reference_ohm = option

    if number_of_ports is not None and number_of_ports != 2:
        raise ValueError(f"expected a 2-port Touchstone file, got {number_of_ports} ports")

    if version.startswith("2"):
        if number_of_ports is None:
            raise ValueError("Touchstone 2.0 file is missing [Number of Ports]")
        if data_order is None:
            raise ValueError("Touchstone 2.0 two-port file is missing [Two-Port Data Order]")
    if data_order is None:
        data_order = "21_12"
    if data_order not in {"21_12", "12_21"}:
        raise ValueError("Touchstone two-port data order must be 21_12 or 12_21")

    if reference_values:
        if len(reference_values) not in {1, 2}:
            raise ValueError("two-port [Reference] must contain one or two resistance values")
        if len(reference_values) == 2 and not np.isclose(reference_values[0], reference_values[1]):
            raise ValueError("unequal per-port Touchstone reference impedances are not yet supported")
        reference_ohm = float(reference_values[0])

    frequency_scale = _FREQUENCY_SCALE[frequency_unit]
    record_width = 9 if matrix_format == "full" else 7

    records: list[list[float]]
    if version.startswith("2") or saw_network_keyword:
        if not numeric_tokens_v2:
            raise ValueError("Touchstone file contains no network data")
        if len(numeric_tokens_v2) % record_width != 0:
            raise ValueError(
                f"Touchstone network data has {len(numeric_tokens_v2)} numeric values; "
                f"expected a multiple of {record_width}"
            )
        records = [
            numeric_tokens_v2[i : i + record_width]
            for i in range(0, len(numeric_tokens_v2), record_width)
        ]
    else:
        records = numeric_lines_v1

    if not records:
        raise ValueError("Touchstone file contains no two-port network records")

    decoded = [
        _decode_record(
            record,
            frequency_scale=frequency_scale,
            data_format=data_format,
            data_order=data_order,
            matrix_format=matrix_format,
        )
        for record in records
    ]
    frequency_hz = np.asarray([row[0] for row in decoded], dtype=float)
    if not np.all(np.isfinite(frequency_hz)) or np.any(np.diff(frequency_hz) <= 0):
        raise ValueError("Touchstone frequencies must be finite and strictly increasing")

    arrays = [
        np.asarray([row[q] for row in decoded], dtype=complex)
        for q in range(1, 5)
    ]
    return Touchstone2Port(
        frequency_hz=frequency_hz,
        s11=arrays[0],
        s21=arrays[1],
        s12=arrays[2],
        s22=arrays[3],
        reference_ohm=float(reference_ohm),
        frequency_unit=frequency_unit.upper(),
        data_format=data_format.upper(),
        data_order=data_order,
        version=version,
    )


def read_touchstone_2port(path: str | Path) -> Touchstone2Port:
    return parse_touchstone_2port_text(Path(path).read_text(encoding="ascii"))


def normalized_omega_linear(
    frequency_hz: np.ndarray,
    *,
    center_hz: float,
    scale_hz: float,
) -> np.ndarray:
    """Explicit linear map ``Omega = (f - center_hz) / scale_hz``.

    This is intentionally not presented as a universal bandpass transform.
    The caller chooses the normalization used by its coupling-matrix model.
    A negative ``scale_hz`` may be used to reverse the Omega sign convention.
    """
    center_hz = float(center_hz)
    scale_hz = float(scale_hz)
    if not np.isfinite(center_hz):
        raise ValueError("center_hz must be finite")
    if not np.isfinite(scale_hz) or scale_hz == 0.0:
        raise ValueError("scale_hz must be finite and nonzero")
    f = np.asarray(frequency_hz, dtype=float)
    return (f - center_hz) / scale_hz


def touchstone_measurement_fragment(
    data: Touchstone2Port,
    *,
    center_hz: float,
    scale_hz: float,
    source: str | None = None,
) -> dict[str, Any]:
    omega = normalized_omega_linear(
        data.frequency_hz, center_hz=center_hz, scale_hz=scale_hz
    )
    return {
        "measurement_source": {
            "format": "touchstone",
            "path": source,
            "version": data.version,
            "reference_ohm": float(data.reference_ohm),
            "input_frequency_unit": data.frequency_unit,
            "input_data_format": data.data_format,
            "two_port_data_order": data.data_order,
            "omega_mapping": {
                "mode": "linear",
                "center_hz": float(center_hz),
                "scale_hz": float(scale_hz),
                "formula": "(frequency_hz - center_hz) / scale_hz",
            },
        },
        "frequency_hz": data.frequency_hz.tolist(),
        "omega": omega.tolist(),
        "s11": {"real": np.real(data.s11).tolist(), "imag": np.imag(data.s11).tolist()},
        "s21": {"real": np.real(data.s21).tolist(), "imag": np.imag(data.s21).tolist()},
    }


def inject_touchstone_measurement(
    topology_spec: dict[str, Any],
    data: Touchstone2Port,
    *,
    center_hz: float,
    scale_hz: float,
    source: str | None = None,
) -> dict[str, Any]:
    """Return a copy of a topology spec with measured S11/S21 inserted."""
    result = dict(topology_spec)
    result.update(
        touchstone_measurement_fragment(
            data, center_hz=center_hz, scale_hz=scale_hz, source=source
        )
    )
    return result
