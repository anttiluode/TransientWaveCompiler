"""Gate C0b: process-independent signed reciprocal charge-packet experiment.

This is the next step after the C0a timing harness.  It uses ideal voltage-
controlled switches but real capacitor charge redistribution.  The edge code is
represented by an equivalent selected capacitance ``|code| * Cunit``; code zero
instantiates no edge transfer capacitor at all.  Later C0c replaces the equivalent
capacitance with an explicit segmented/binary unit array and then MOS switches.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import subprocess
import tempfile


CODES = [0, 1, 2, 16, 64, 127, -1, -16, -127]
CUNIT = 1e-12
CSUM = 1e-9
VDIFF = 0.4

MEAS = re.compile(
    r"^\s*(vi_sum|vj_sum)\s*=\s*([-+0-9.eE]+)", re.IGNORECASE | re.MULTILINE
)


def deck_for(code: int) -> str:
    mag = abs(int(code))
    lines = [
        "* TW-1A v0.5 Gate C0b generated equivalent edge-cap cell",
        ".option numdgt=12",
        "VSTATEI vi 0 0.2",
        "VSTATEJ vj 0 -0.2",
        "VRESET rst 0 PWL(0n 1 0.45n 1 0.451n 0 4n 0)",
        "VSAMPLE samp 0 PWL(0n 0 0.499n 0 0.50n 1 1.00n 1 1.001n 0 4n 0)",
        "VXFER xfer 0 PWL(0n 0 1.199n 0 1.20n 1 3.20n 1 3.201n 0 4n 0)",
        ".model ESW SW(Ron=0.1 Roff=1e15 Vt=0.5 Vh=0)",
        ".model RSW SW(Ron=0.01 Roff=1e15 Vt=0.5 Vh=0)",
        "CSUMI sumi 0 1n",
        "CSUMJ sumj 0 1n",
        "RSUMI sumi 0 1e15",
        "RSUMJ sumj 0 1e15",
        "SRESETI sumi 0 rst 0 RSW",
        "SRESETJ sumj 0 rst 0 RSW",
    ]
    if mag:
        cedge = mag * CUNIT
        lines.extend(
            [
                f"CEDGE ct cb {cedge:.12g}",
                "RCT ct 0 1e15",
                "RCB cb 0 1e15",
                "SSAMPLEI ct vi samp 0 ESW",
                "SSAMPLEJ cb vj samp 0 ESW",
            ]
        )
        if code > 0:
            lines.extend(
                [
                    "SXFERI ct sumi xfer 0 ESW",
                    "SXFERJ cb sumj xfer 0 ESW",
                ]
            )
        else:
            lines.extend(
                [
                    "SXFERI ct sumj xfer 0 ESW",
                    "SXFERJ cb sumi xfer 0 ESW",
                ]
            )
    lines.extend(
        [
            ".tran 1p 4n",
            ".measure tran VI_SUM FIND v(sumi) AT=3.10n",
            ".measure tran VJ_SUM FIND v(sumj) AT=3.10n",
            ".end",
            "",
        ]
    )
    return "\n".join(lines)


def run_code(code: int, root: Path) -> dict[str, float]:
    deck = root / f"edge_{code:+d}.cir"
    log = root / f"edge_{code:+d}.log"
    deck.write_text(deck_for(code), encoding="utf-8")
    proc = subprocess.run(
        ["ngspice", "-b", "-o", str(log), str(deck)],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"ngspice failed for code {code}:\n{proc.stdout}\n{proc.stderr}\n"
            + (log.read_text(errors="replace") if log.exists() else "")
        )
    text = log.read_text(encoding="utf-8", errors="replace")
    vals = {k.lower(): float(v) for k, v in MEAS.findall(text)}
    if vals.keys() < {"vi_sum", "vj_sum"}:
        raise SystemExit(f"missing measurements for code {code}: {vals}\n{text}")
    vi = vals["vi_sum"]
    vj = vals["vj_sum"]
    return {
        "vi": vi,
        "vj": vj,
        "diff": vi - vj,
        "common": vi + vj,
    }


def expected_diff(code: int) -> float:
    if code == 0:
        return 0.0
    ce = abs(code) * CUNIT
    # Two equal endpoint sum capacitors and one edge capacitor between them.
    # With symmetric final voltages +/-x:
    #   Cedge*VDIFF = Csum*x + Cedge*(2x)
    x = ce * VDIFF / (CSUM + 2.0 * ce)
    return math.copysign(2.0 * x, code)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tw1a-c0b-") as td:
        root = Path(td)
        rows = {code: run_code(code, root) for code in CODES}

    print("code        Vi_sum        Vj_sum          diff        common      expected")
    for code in CODES:
        r = rows[code]
        exp = expected_diff(code)
        print(
            f"{code:4d}  {r['vi']:+.9e}  {r['vj']:+.9e}  {r['diff']:+.9e}  "
            f"{r['common']:+.3e}  {exp:+.9e}"
        )

        # Reciprocity: one sampled packet must create equal/opposite endpoint
        # movement.  Use an absolute floor for the exact-zero case.
        if abs(r["common"]) > max(1e-10, 1e-6 * abs(r["diff"])):
            raise SystemExit(f"code {code}: endpoint stamp is not reciprocal")

        if code == 0:
            if abs(r["diff"]) > 1e-10:
                raise SystemExit(f"zero code is not physically off: {r['diff']}")
            continue

        if code * r["diff"] <= 0.0:
            raise SystemExit(f"code {code}: wrong transfer sign")
        rel = abs(r["diff"] - exp) / max(abs(exp), 1e-30)
        if rel > 5e-3:
            raise SystemExit(f"code {code}: charge redistribution error {rel:.3%}")

    # Positive magnitude must be monotonic.
    pos = [1, 2, 16, 64, 127]
    for a, b in zip(pos, pos[1:]):
        if not abs(rows[b]["diff"]) > abs(rows[a]["diff"]):
            raise SystemExit(f"non-monotonic magnitude: code {a} -> {b}")

    # Signed path must be symmetric for the tested mirrored codes.
    for mag in (1, 16, 127):
        p = rows[mag]["diff"]
        n = rows[-mag]["diff"]
        signed_asym = abs(p + n) / max(0.5 * (abs(p) + abs(n)), 1e-30)
        print(f"sign symmetry |code|={mag}: {signed_asym:.6%}")
        if signed_asym > 1e-4:
            raise SystemExit(f"sign asymmetry too large for ideal C0b at |code|={mag}")


if __name__ == "__main__":
    main()
