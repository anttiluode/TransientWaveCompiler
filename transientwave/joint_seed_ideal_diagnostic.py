"""Development-only ideal control on already-seen v0.3 joint seeds."""
from __future__ import annotations

import json
from pathlib import Path

from .hardware_envelope_order_v03 import JOINT_SEEDS, base_config, run_point


def main() -> None:
    point = run_point(JOINT_SEEDS, base_config(), label="DEV ideal joint-seed control")
    out = {
        "experiment": "joint_seed_ideal_diagnostic",
        "status": "development_only_seen_seeds",
        "seeds": list(JOINT_SEEDS),
        "result": point,
    }
    path = Path("runs/joint_seed_ideal_diagnostic.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("rows", [(r["seed"], r["exact_improvement"], r["placement_gap"]) for r in point["rows"]], flush=True)
    print(f"wrote {path}", flush=True)

if __name__ == "__main__":
    main()
