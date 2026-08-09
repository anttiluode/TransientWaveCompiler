"""C1c: ideal active virtual-sum additivity gate.

A 64 pF sample capacitor is precharged to 0.4 V, then connected to the virtual
summing input of an ideal high-gain inverting charge integrator with a 1 nF
feedback/state capacitor. The packet must change the stored output by the same
amount whether the output initially holds 0 V or +0.2 V.

This is intentionally not a transistor OTA claim. It proves the architectural
property C1b showed passive sharing cannot provide: packet increment independent
of the already-stored state.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile


CF = 1e-9
CS = 64e-12
VSAMPLE = 0.4
A0 = 1e8
PRECHARGED = 0.2


def deck(initial_out: float) -> str:
    sum_ic = -initial_out / A0
    cfb_ic = initial_out - sum_ic
    return f"""* TW-1A C1c ideal virtual summing / charge integrator
.model SW SW(Ron=1 Roff=1e12 Vt=0.5 Vh=0)
Vctl ctl 0 PULSE(0 1 10n 0.2n 0.2n 300n 500n)
Eop out 0 0 sum {A0}
Cfb out sum {CF} IC={cfb_ic}
Rsum sum 0 1e12
Cs samp 0 {CS} IC={VSAMPLE}
Rsamp samp 0 1e12
Sx samp sum ctl 0 SW
.ic v(out)={initial_out} v(sum)={sum_ic} v(samp)={VSAMPLE}
.tran 0.05n 200n UIC
.measure tran vbefore FIND v(out) AT=5n
.measure tran vafter  FIND v(out) AT=180n
.measure tran vsumhi MAX v(sum) FROM=20n TO=180n
.measure tran vsumlo MIN v(sum) FROM=20n TO=180n
.end
"""


def _measure(text: str, name: str) -> float:
    m = re.search(rf"{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
    if not m:
        raise RuntimeError(f"measure {name!r} missing\n{text}")
    return float(m.group(1))


def run_case(initial_out: float) -> tuple[float, float, float]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir = td / "c1c.cir"
        log = td / "c1c.log"
        cir.write_text(deck(initial_out), encoding="utf-8")
        proc = subprocess.run(
            ["ngspice", "-b", "-o", str(log), str(cir)],
            text=True,
            capture_output=True,
            timeout=30,
        )
        text = (log.read_text(errors="replace") if log.exists() else "") + proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed ({proc.returncode})\n{text}")
        before = _measure(text, "vbefore")
        after = _measure(text, "vafter")
        hi = _measure(text, "vsumhi")
        lo = _measure(text, "vsumlo")
        return before, after, max(abs(hi), abs(lo))


def main() -> None:
    b0, a0, s0 = run_case(0.0)
    bp, ap, sp = run_case(PRECHARGED)
    inc0 = a0 - b0
    incp = ap - bp
    scale = max(abs(inc0), abs(incp), 1e-30)
    mismatch = abs(incp - inc0) / scale
    expected_mag = (CS / CF) * VSAMPLE

    print(f"empty before/after       {b0:+.9f} / {a0:+.9f} V")
    print(f"precharged before/after  {bp:+.9f} / {ap:+.9f} V")
    print(f"empty increment          {inc0*1e3:+.6f} mV")
    print(f"precharged increment     {incp*1e3:+.6f} mV")
    print(f"packet mismatch          {100*mismatch:.9f}%")
    print(f"ideal packet magnitude   {expected_mag*1e3:.6f} mV")
    print(f"virtual-node max         {max(abs(s0), abs(sp))*1e6:.6f} uV")

    if mismatch > 0.01:
        raise SystemExit("C1c FAIL: packet increment depends on existing state by >1%")
    if abs(abs(inc0) - expected_mag) / expected_mag > 0.01:
        raise SystemExit("C1c FAIL: packet magnitude misses Ce/Cf charge-integrator law by >1%")
    if max(abs(s0), abs(sp)) > 10e-6:
        raise SystemExit("C1c FAIL: virtual summing node moved by >10 uV")

    print("C1c PASS: active virtual summing restores state-independent packet addition")


if __name__ == "__main__":
    main()
