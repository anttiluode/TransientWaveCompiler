"""Gate C0c: explicit 7-bit binary reciprocal edge capacitor array.

Unlike C0b, this deck always instantiates seven physical capacitor branches with
weights 1,2,4,8,16,32,64*Cunit. A digital magnitude code enables sample and
transfer switches only on selected branches. Magnitude zero therefore means all
seven programmable branches are physically disconnected by their switches.

The positive-code sweep is exhaustive (0..127). Representative negative codes
reuse the same magnitude selection with the transfer polarity crossbar reversed.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import subprocess
import tempfile


BITS = [1, 2, 4, 8, 16, 32, 64]
POS_CODES = list(range(128))
NEG_CODES = [-1, -2, -3, -7, -16, -31, -64, -85, -127]
CUNIT = 1e-12
CSUM = 1e-9
VDIFF = 0.4

MEAS = re.compile(
    r"^\s*(vi_sum|vj_sum)\s*=\s*([-+0-9.eE]+)", re.IGNORECASE | re.MULTILINE
)


def deck_for(code: int) -> str:
    mag = abs(int(code))
    lines = [
        "* TW-1A v0.5 Gate C0c explicit seven-branch binary edge array",
        ".option numdgt=12",
        "VSTATEI vi 0 0.2",
        "VSTATEJ vj 0 -0.2",
        "VRESET rst 0 PWL(0n 1 0.50n 1 0.51n 0 15n 0)",
        "VSAMPLE samp 0 PWL(0n 0 0.69n 0 0.70n 1 2.70n 1 2.71n 0 15n 0)",
        "VXFER xfer 0 PWL(0n 0 2.99n 0 3.00n 1 13.00n 1 13.01n 0 15n 0)",
        "VOFF offctl 0 0",
        # Millisecond off/leak RC versus a 15 ns experiment keeps disabled
        # branches electrically anchored without materially moving their charge.
        ".model ESW SW(Ron=10 Roff=1e9 Vt=0.5 Vh=0)",
        ".model RSW SW(Ron=1 Roff=1e9 Vt=0.5 Vh=0)",
        "CSUMI sumi 0 1n",
        "CSUMJ sumj 0 1n",
        "RSUMI sumi 0 1e9",
        "RSUMJ sumj 0 1e9",
        "SRESETI sumi 0 rst 0 RSW",
        "SRESETJ sumj 0 rst 0 RSW",
    ]

    for k, weight in enumerate(BITS):
        ct = f"ct{k}"
        cb = f"cb{k}"
        selected = bool(mag & weight)
        sample_ctl = "samp" if selected else "offctl"
        xfer_ctl = "xfer" if selected else "offctl"
        lines.extend(
            [
                f"CB{k} {ct} {cb} {weight * CUNIT:.12g}",
                f"RT{k} {ct} 0 1e9",
                f"RB{k} {cb} 0 1e9",
                f"SSA{k} {ct} vi {sample_ctl} 0 ESW",
                f"SSB{k} {cb} vj {sample_ctl} 0 ESW",
            ]
        )
        if code >= 0:
            lines.extend(
                [
                    f"SXI{k} {ct} sumi {xfer_ctl} 0 ESW",
                    f"SXJ{k} {cb} sumj {xfer_ctl} 0 ESW",
                ]
            )
        else:
            lines.extend(
                [
                    f"SXI{k} {ct} sumj {xfer_ctl} 0 ESW",
                    f"SXJ{k} {cb} sumi {xfer_ctl} 0 ESW",
                ]
            )

    lines.extend(
        [
            # Use the DC operating point rather than UIC so every disabled
            # branch has a well-defined initial voltage before switching starts.
            ".tran 5p 15n",
            ".measure tran VI_SUM FIND v(sumi) AT=12.90n",
            ".measure tran VJ_SUM FIND v(sumj) AT=12.90n",
            ".end",
            "",
        ]
    )
    return "\n".join(lines)


def run_code(code: int, root: Path) -> dict[str, float]:
    deck = root / f"array_{code:+d}.cir"
    log = root / f"array_{code:+d}.log"
    deck.write_text(deck_for(code), encoding="utf-8")
    try:
        proc = subprocess.run(
            ["ngspice", "-b", "-o", str(log), str(deck)],
            text=True,
            capture_output=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        tail = log.read_text(errors="replace")[-4000:] if log.exists() else ""
        raise SystemExit(f"ngspice timed out for code {code}\n{tail}") from exc
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
    return {"vi": vi, "vj": vj, "diff": vi - vj, "common": vi + vj}


def expected_diff(code: int) -> float:
    if code == 0:
        return 0.0
    ce = abs(code) * CUNIT
    x = ce * VDIFF / (CSUM + 2.0 * ce)
    return math.copysign(2.0 * x, code)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tw1a-c0c-") as td:
        root = Path(td)
        pos = {code: run_code(code, root) for code in POS_CODES}
        neg = {code: run_code(code, root) for code in NEG_CODES}

    max_formula_error = 0.0
    max_common = 0.0
    previous = -1.0
    for code in POS_CODES:
        r = pos[code]
        exp = expected_diff(code)
        max_common = max(max_common, abs(r["common"]))
        if code == 0:
            if abs(r["diff"]) > 2e-8:
                raise SystemExit(f"zero code leaks transfer: {r['diff']}")
            continue
        if r["diff"] <= previous:
            raise SystemExit(f"positive transfer is not monotonic at code {code}")
        previous = r["diff"]
        rel = abs(r["diff"] - exp) / abs(exp)
        max_formula_error = max(max_formula_error, rel)
        if rel > 0.015:
            raise SystemExit(f"code {code}: explicit-array/formula error {rel:.3%}")
        if abs(r["common"]) > max(2e-8, 5e-5 * abs(r["diff"])):
            raise SystemExit(f"code {code}: endpoint stamp not reciprocal")

    max_sign_asym = 0.0
    for code, rn in neg.items():
        rp = pos[-code]
        if rn["diff"] >= 0.0:
            raise SystemExit(f"negative code {code}: wrong sign")
        asym = abs(rp["diff"] + rn["diff"]) / max(
            0.5 * (abs(rp["diff"]) + abs(rn["diff"])), 1e-30
        )
        max_sign_asym = max(max_sign_asym, asym)
        if asym > 5e-4:
            raise SystemExit(f"code +/-{-code}: sign asymmetry {asym:.6%}")

    print("C0c explicit 7-bit binary capacitor array PASS")
    print(f"positive codes checked: {len(POS_CODES)} (exhaustive 0..127)")
    print(f"negative codes checked: {len(NEG_CODES)}")
    print(f"max explicit-array vs analytic relative error: {max_formula_error:.6%}")
    print(f"max endpoint common residual: {max_common:.3e} V")
    print(f"max tested sign asymmetry: {max_sign_asym:.6%}")
    for code in (0, 1, 2, 3, 16, 31, 64, 85, 127):
        r = pos[code]
        print(
            f"code {code:3d}: Vi={r['vi']:+.9e} Vj={r['vj']:+.9e} "
            f"diff={r['diff']:+.9e} expected={expected_diff(code):+.9e}"
        )


if __name__ == "__main__":
    main()
