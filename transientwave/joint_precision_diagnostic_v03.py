"""Development-only diagnosis of the v0.3 joint precision miss.

Uses only already-seen v0.3 joint-confirmation seeds 856..861. Results may guide
v0.4 preregistration but are not themselves confirmatory evidence.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from .hardware_envelope_order_v03 import JOINT_SEEDS, base_config, run_point


CANDIDATES = [
    (9, 5, 6),
    (10, 5, 6),
    (12, 5, 6),
    (9, 6, 6),
    (9, 8, 6),
    (9, 10, 6),
    (9, 5, 7),
    (9, 5, 8),
    (9, 5, 10),
    (9, 6, 7),
    (10, 5, 7),
    (10, 6, 7),
    (10, 8, 8),
    (12, 8, 8),
    (12, 10, 10),
]


def main() -> None:
    points = []
    for w, d, a in CANDIDATES:
        cfg = replace(base_config(), weight_bits=w, dac_bits=d, adc_bits=a)
        p = run_point(JOINT_SEEDS, cfg, label=f"DEV joint w={w} d={d} a={a}")
        p["candidate"] = {"weight_bits": w, "dac_bits": d, "adc_bits": a}
        points.append(p)
        misses = [
            (r["seed"], r["exact_improvement"], r["placement_gap"])
            for r in p["rows"]
            if r["exact_improvement"] < 0.10
        ]
        print("  misses", misses, flush=True)

    passing = [p for p in points if p["summary"]["qualified"]]
    passing.sort(
        key=lambda p: (
            sum(p["candidate"].values()),
            max(p["candidate"].values()),
            p["candidate"]["adc_bits"],
            p["candidate"]["dac_bits"],
            p["candidate"]["weight_bits"],
        )
    )
    out = {
        "experiment": "joint_precision_diagnostic_v03",
        "status": "development_only_seen_seeds",
        "seeds": list(JOINT_SEEDS),
        "points": points,
        "lowest_cost_passing_candidate": None if not passing else passing[0]["candidate"],
    }
    path = Path("runs/joint_precision_diagnostic_v03.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("lowest passing", out["lowest_cost_passing_candidate"], flush=True)
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
