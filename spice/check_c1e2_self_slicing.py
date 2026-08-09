"""C1e2: sequentially sliced |self|=3 packet timing sweep."""
from __future__ import annotations

from pathlib import Path
import math
import re
import subprocess
import tempfile


CF = 1e-9
TARGET_TOTAL = 25.6e-3
PRECHARGED = 0.2
A0 = 1e5
ROUT = 1e6
RON = 1.0
APERTURE = 20e-9
GAP = 5e-9
START = 10e-9
SLICES = [1, 2, 4, 8]
GBW_VALUES = [30e6, 100e6, 300e6, 1e9]


def deck(initial_out: float, slices: int, gbw: float) -> tuple[str, float]:
    alpha = 3.0 / slices
    cs = alpha * CF
    vsample = TARGET_TOTAL / 3.0
    gm = A0 / ROUT
    cdom = A0 / (2 * math.pi * ROUT * gbw)
    sum_ic = -initial_out / A0
    cfb_ic = initial_out - sum_ic
    lines = [
        "* TW-1A C1e2 sequential sliced self packet",
        f".model SW SW(Ron={RON} Roff=1e12 Vt=0.5 Vh=0)",
        f"Gop x 0 sum 0 {gm}",
        f"Rop x 0 {ROUT}",
        f"Cop x 0 {cdom} IC={initial_out}",
        "Ebuf out 0 x 0 1",
        f"Cfb out sum {CF} IC={cfb_ic}",
        "Rsum sum 0 1e12",
    ]
    for k in range(slices):
        delay = START + k * (APERTURE + GAP)
        lines.extend(
            [
                f"Vctl{k} ctl{k} 0 PULSE(0 1 {delay} 0.1n 0.1n {APERTURE} 1u)",
                f"Cs{k} samp{k} 0 {cs} IC={vsample}",
                f"Rsamp{k} samp{k} 0 1e12",
                f"Sx{k} samp{k} sum ctl{k} 0 SW",
            ]
        )
    end_transfer = START + (slices - 1) * (APERTURE + GAP) + APERTURE
    t_before = 5e-9
    t_after = end_transfer - 0.2e-9
    t_stop = end_transfer + 5e-9
    ic = [f"v(x)={initial_out}", f"v(out)={initial_out}", f"v(sum)={sum_ic}"]
    ic += [f"v(samp{k})={vsample}" for k in range(slices)]
    lines.extend(
        [
            ".ic " + " ".join(ic),
            f".tran 0.01n {t_stop} UIC",
            f".measure tran vbefore FIND v(out) AT={t_before}",
            f".measure tran vafter FIND v(out) AT={t_after}",
            f".measure tran vsumhi MAX v(sum) FROM={START + 0.1e-9} TO={t_after}",
            f".measure tran vsumlo MIN v(sum) FROM={START + 0.1e-9} TO={t_after}",
            ".end",
        ]
    )
    return "\n".join(lines) + "\n", end_transfer


def _measure(text: str, name: str) -> float:
    m = re.search(rf"{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
    if not m:
        raise RuntimeError(f"measure {name!r} missing\n{text}")
    return float(m.group(1))


def run_case(initial_out: float, slices: int, gbw: float):
    text_deck, end_transfer = deck(initial_out, slices, gbw)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir, log = td / "c1e2.cir", td / "c1e2.log"
        cir.write_text(text_deck, encoding="utf-8")
        proc = subprocess.run(
            ["ngspice", "-b", "-o", str(log), str(cir)],
            text=True,
            capture_output=True,
            timeout=30,
        )
        text = (log.read_text(errors="replace") if log.exists() else "") + proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed ({proc.returncode})\n{text}")
        before, after = _measure(text, "vbefore"), _measure(text, "vafter")
        hi, lo = _measure(text, "vsumhi"), _measure(text, "vsumlo")
        return after - before, max(abs(hi), abs(lo)), end_transfer - START


def main() -> None:
    first_passing = {}
    for slices in SLICES:
        alpha = 3.0 / slices
        beta = 1.0 / (1.0 + alpha)
        print(f"slices={slices} Cin/Cf={alpha:g} beta={beta:.6f}")
        first = None
        for gbw in GBW_VALUES:
            inc0, sum0, transfer_time = run_case(0.0, slices, gbw)
            incp, sump, _ = run_case(PRECHARGED, slices, gbw)
            mag_error = abs(abs(inc0) - TARGET_TOTAL) / TARGET_TOTAL
            mismatch = abs(incp - inc0) / max(abs(inc0), abs(incp), 1e-30)
            ok = mag_error <= 1e-3 and mismatch <= 1e-3
            if ok and first is None:
                first = gbw
            print(
                f"  GBW={gbw/1e6:8.1f}MHz packet={inc0*1e3:+.6f}mV "
                f"magerr={100*mag_error:.6f}% mismatch={100*mismatch:.6f}% "
                f"vsummax={max(sum0,sump)*1e6:.3f}uV "
                f"self_xfer={transfer_time*1e9:.1f}ns pass={ok}"
            )
        first_passing[slices] = first
    print("first passing GBW Hz", first_passing)
    non_monolithic = {n: g for n, g in first_passing.items() if n > 1 and g is not None}
    if not non_monolithic:
        raise SystemExit("C1e2 FAIL: no sliced frozen point met the 0.1% marker")
    print("C1e2 PASS: self slicing yields at least one finite-GBW timing point")


if __name__ == "__main__":
    main()
