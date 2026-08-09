"""C1b: prove that passive edge charge sharing is not a NEXT accumulator.

The edge sampler is one differential 64 pF capacitor precharged to 0.4 V. The
destination state is represented by two 1 nF halves. When the sample capacitor
is simply connected across those precharged state halves, the final differential
voltage is passive charge sharing:

    Vfinal = (Cstate/2 * Vinitial + Cedge * Vsample) / (Cstate/2 + Cedge).

Therefore the increment depends on the state already stored. C1b intentionally
*passes* when this non-additivity is observed, because its purpose is to reject
passive sharing as the TW-1A NEXT summing mechanism.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile


CSTATE = 1e-9
CEDGE = 64e-12
VSAMPLE = 0.4
PRECHARGED = 0.2
TMEAS = "180n"


def expected_final(initial_diff: float) -> float:
    cdiff = 0.5 * CSTATE
    return (cdiff * initial_diff + CEDGE * VSAMPLE) / (cdiff + CEDGE)


def deck(initial_diff: float) -> str:
    vp = 0.5 * initial_diff
    vn = -0.5 * initial_diff
    return f"""* TW-1A C1b passive precharged-destination additivity rejection
.model SW SW(Ron=1 Roff=1e12 Vt=0.5 Vh=0)
Vctl ctl 0 PULSE(0 1 10n 1n 1n 300n 500n)
Cdp dp 0 {CSTATE} IC={vp}
Cdn dn 0 {CSTATE} IC={vn}
Cs sp sn {CEDGE} IC={VSAMPLE}
Rsp sp 0 1e12
Rsn sn 0 1e12
Splus sp dp ctl 0 SW
Sminus sn dn ctl 0 SW
* Explicit differential probe node; ngspice .measure is happier with one scalar.
Ediff diff 0 dp dn 1
.ic v(dp)={vp} v(dn)={vn} v(sp)=0.2 v(sn)=-0.2
.tran 0.1n 200n UIC
.measure tran dpfinal FIND v(diff) AT={TMEAS}
.end
"""


def run_case(initial_diff: float) -> float:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir = td / "c1b.cir"
        log = td / "c1b.log"
        cir.write_text(deck(initial_diff), encoding="utf-8")
        proc = subprocess.run(
            ["ngspice", "-b", "-o", str(log), str(cir)],
            text=True,
            capture_output=True,
            timeout=30,
        )
        text = (log.read_text(errors="replace") if log.exists() else "") + proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed ({proc.returncode})\n{text}")
        m = re.search(r"dpfinal\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
        if not m:
            raise RuntimeError(f"dpfinal measure missing\n{text}")
        return float(m.group(1))


def main() -> None:
    v0 = run_case(0.0)
    vpre = run_case(PRECHARGED)
    expected0 = expected_final(0.0)
    expected_pre = expected_final(PRECHARGED)
    inc0 = v0
    inc_pre = vpre - PRECHARGED
    ratio = inc_pre / inc0
    additivity_error = abs(1.0 - ratio)

    print(f"empty final              {v0:+.9f} V")
    print(f"precharged final         {vpre:+.9f} V")
    print(f"empty increment          {inc0*1e3:+.6f} mV")
    print(f"precharged increment     {inc_pre*1e3:+.6f} mV")
    print(f"increment ratio          {ratio:.9f}")
    print(f"additivity error         {100*additivity_error:.6f}%")
    print(f"analytic empty final     {expected0:+.9f} V")
    print(f"analytic precharge final {expected_pre:+.9f} V")

    if abs(v0 - expected0) > 2e-5 or abs(vpre - expected_pre) > 2e-5:
        raise SystemExit("C1b FAIL: SPICE did not reproduce passive charge sharing")

    if additivity_error < 0.45:
        raise SystemExit("C1b FAIL: passive sharing unexpectedly looked additive")

    print("C1b PASS: passive charge sharing is rejected as a NEXT accumulator")


if __name__ == "__main__":
    main()
