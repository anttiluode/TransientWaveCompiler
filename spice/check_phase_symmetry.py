"""Parse ngspice C0a measurements and enforce the phase-symmetry experiment."""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path


MEASURE = re.compile(
    r"^\s*(a_seq|b_seq|a_sym|b_sym)\s*=\s*([-+0-9.eE]+)", re.IGNORECASE | re.MULTILINE
)


def main(path: str) -> None:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    values = {k.lower(): float(v) for k, v in MEASURE.findall(text)}
    missing = {"a_seq", "b_seq", "a_sym", "b_sym"} - values.keys()
    if missing:
        raise SystemExit(f"missing ngspice measurements: {sorted(missing)}")

    vdiff = 0.4
    gain_a_seq = values["a_seq"] / vdiff
    gain_b_seq = values["b_seq"] / -vdiff
    gain_a_sym = values["a_sym"] / vdiff
    gain_b_sym = values["b_sym"] / -vdiff

    seq_mismatch = abs(gain_a_seq - gain_b_seq) / max(
        0.5 * (abs(gain_a_seq) + abs(gain_b_seq)), 1e-30
    )
    sym_mismatch = abs(gain_a_sym - gain_b_sym) / max(
        0.5 * (abs(gain_a_sym) + abs(gain_b_sym)), 1e-30
    )

    print(f"A sequential gain: {gain_a_seq:.9f}")
    print(f"B sequential gain: {gain_b_seq:.9f}")
    print(f"sequential mismatch: {seq_mismatch:.6%}")
    print(f"A symmetric gain: {gain_a_sym:.9f}")
    print(f"B symmetric gain: {gain_b_sym:.9f}")
    print(f"symmetric mismatch: {sym_mismatch:.6%}")

    # Aperture is intentionally around 1.2 tau, so common transfer should be
    # roughly 70% settled rather than nearly ideal.
    if not (0.60 <= gain_a_sym <= 0.80 and 0.60 <= gain_b_sym <= 0.80):
        raise SystemExit("phase-symmetric common transfer is outside intended 60-80% window")

    # This ideal-reset timing deck should be vastly better than the emulator's
    # inward 1% residual target.  Later transistor decks are allowed the actual
    # <=1% C0 contract.
    if sym_mismatch > 1e-3:
        raise SystemExit(f"symmetric ideal-reset mismatch too large: {sym_mismatch:.6g}")

    # The control case must actually demonstrate why the inter-lane reset
    # exists.  Require a visibly large first/second-use error.
    if seq_mismatch < 0.10:
        raise SystemExit(f"sequential control mismatch unexpectedly small: {seq_mismatch:.6g}")

    if not math.isfinite(seq_mismatch + sym_mismatch):
        raise SystemExit("non-finite SPICE result")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_phase_symmetry.py <ngspice-log>")
    main(sys.argv[1])
