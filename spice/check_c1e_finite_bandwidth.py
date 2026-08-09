"""C1e: finite one-pole GBW sweep for a 20 ns active-integrator aperture."""
from __future__ import annotations

from pathlib import Path
import math
import re
import subprocess
import tempfile


CF = 1e-9
TARGET_PACKET = 25.6e-3
PRECHARGED = 0.2
A0 = 1e5
ROUT = 1e6
APERTURE = 20e-9
ALPHAS = [0.265, 3.0]
GBW_VALUES = [30e6, 100e6, 300e6, 1e9]


def deck(initial_out: float, alpha: float, gbw: float) -> str:
    cs = alpha * CF
    vsample = TARGET_PACKET / alpha
    gm = A0 / ROUT
    cdom = A0 / (2 * math.pi * ROUT * gbw)
    sum_ic = -initial_out / A0
    cfb_ic = initial_out - sum_ic
    return f"""* TW-1A C1e one-pole finite-bandwidth active integrator
.model SW SW(Ron=1 Roff=1e12 Vt=0.5 Vh=0)
Vctl ctl 0 PULSE(0 1 10n 0.1n 0.1n 20n 100n)
Gop x 0 sum 0 {gm}
Rop x 0 {ROUT}
Cop x 0 {cdom} IC={initial_out}
Ebuf out 0 x 0 1
Cfb out sum {CF} IC={cfb_ic}
Rsum sum 0 1e12
Cs samp 0 {cs} IC={vsample}
Rsamp samp 0 1e12
Sx samp sum ctl 0 SW
.ic v(x)={initial_out} v(out)={initial_out} v(sum)={sum_ic} v(samp)={vsample}
.tran 0.01n 50n UIC
.measure tran vbefore FIND v(out) AT=5n
.measure tran vafter FIND v(out) AT=30n
.measure tran vsumhi MAX v(sum) FROM=10.1n TO=30n
.measure tran vsumlo MIN v(sum) FROM=10.1n TO=30n
.end
"""


def _measure(text: str, name: str) -> float:
    m = re.search(rf"{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
    if not m:
        raise RuntimeError(f"measure {name!r} missing\n{text}")
    return float(m.group(1))


def run_case(initial_out: float, alpha: float, gbw: float):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir, log = td / "c1e.cir", td / "c1e.log"
        cir.write_text(deck(initial_out, alpha, gbw), encoding="utf-8")
        proc = subprocess.run(["ngspice", "-b", "-o", str(log), str(cir)], text=True, capture_output=True, timeout=30)
        text = (log.read_text(errors="replace") if log.exists() else "") + proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed ({proc.returncode})\n{text}")
        before, after = _measure(text, "vbefore"), _measure(text, "vafter")
        hi, lo = _measure(text, "vsumhi"), _measure(text, "vsumlo")
        return after - before, max(abs(hi), abs(lo))


def main() -> None:
    passing = {}
    for alpha in ALPHAS:
        beta = 1.0 / (1.0 + alpha)
        print(f"Cin/Cf={alpha:g} beta={beta:.6f}")
        first_pass = None
        for gbw in GBW_VALUES:
            inc0, sum0 = run_case(0.0, alpha, gbw)
            incp, sump = run_case(PRECHARGED, alpha, gbw)
            mag_error = abs(abs(inc0) - TARGET_PACKET) / TARGET_PACKET
            mismatch = abs(incp - inc0) / max(abs(inc0), abs(incp), 1e-30)
            v_sum = max(sum0, sump)
            ok = mag_error <= 1e-3 and mismatch <= 1e-3
            if ok and first_pass is None:
                first_pass = gbw
            print(
                f"  GBW={gbw/1e6:8.1f}MHz packet={inc0*1e3:+.6f}mV "
                f"magerr={100*mag_error:.6f}% mismatch={100*mismatch:.6f}% "
                f"vsummax={v_sum*1e6:.3f}uV pass={ok}"
            )
        passing[alpha] = first_pass
    print("first passing GBW Hz", passing)
    if any(v is None for v in passing.values()):
        raise SystemExit("C1e FAIL: no frozen GBW point met the 0.1% marker")
    print("C1e PASS: finite-bandwidth boundary measured at edge and worst self loading")


if __name__ == "__main__":
    main()
