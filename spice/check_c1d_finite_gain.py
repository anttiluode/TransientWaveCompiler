"""C1d: finite open-loop DC gain sweep for the active charge integrator."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile


CF = 1e-9
TARGET_PACKET = 25.6e-3
PRECHARGED = 0.2
ALPHAS = [0.265, 3.0]
A0_VALUES = [1e3, 3e3, 1e4, 3e4, 1e5]


def deck(initial_out: float, alpha: float, a0: float) -> str:
    cs = alpha * CF
    vsample = TARGET_PACKET / alpha
    sum_ic = -initial_out / a0
    cfb_ic = initial_out - sum_ic
    return f"""* TW-1A C1d finite DC gain active integrator
.model SW SW(Ron=1 Roff=1e12 Vt=0.5 Vh=0)
Vctl ctl 0 PULSE(0 1 10n 0.2n 0.2n 300n 500n)
Eop out 0 0 sum {a0}
Cfb out sum {CF} IC={cfb_ic}
Rsum sum 0 1e12
Cs samp 0 {cs} IC={vsample}
Rsamp samp 0 1e12
Sx samp sum ctl 0 SW
.ic v(out)={initial_out} v(sum)={sum_ic} v(samp)={vsample}
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


def run_case(initial_out: float, alpha: float, a0: float):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir, log = td / "c1d.cir", td / "c1d.log"
        cir.write_text(deck(initial_out, alpha, a0), encoding="utf-8")
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
        print(f"Cin/Cf={alpha:g} beta={1/(1+alpha):.6f}")
        first_pass = None
        for a0 in A0_VALUES:
            inc0, sum0 = run_case(0.0, alpha, a0)
            incp, sump = run_case(PRECHARGED, alpha, a0)
            mag_error = abs(abs(inc0) - TARGET_PACKET) / TARGET_PACKET
            mismatch = abs(incp - inc0) / max(abs(inc0), abs(incp), 1e-30)
            v_sum = max(sum0, sump)
            ok = mag_error <= 1e-3 and mismatch <= 1e-3
            if ok and first_pass is None:
                first_pass = a0
            print(
                f"  A0={a0:8.0f} packet={inc0*1e3:+.6f}mV "
                f"magerr={100*mag_error:.6f}% mismatch={100*mismatch:.6f}% "
                f"vsummax={v_sum*1e6:.3f}uV pass={ok}"
            )
        passing[alpha] = first_pass
    print("first passing A0", passing)
    if any(v is None for v in passing.values()):
        raise SystemExit("C1d FAIL: no frozen A0 point met the 0.1% marker")
    print("C1d PASS: finite-gain boundary measured for edge and worst self loading")


if __name__ == "__main__":
    main()
