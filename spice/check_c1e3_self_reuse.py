"""C1e3: reuse one Cin/Cf=1.5 self sample capacitor for two slices."""
from __future__ import annotations

from pathlib import Path
import math
import re
import subprocess
import tempfile


CF = 1e-9
ALPHA = 1.5
CS = ALPHA * CF
TARGET_TOTAL = 25.6e-3
VSAMPLE = TARGET_TOTAL / 3.0
PRECHARGED = 0.2
A0 = 1e5
GBW = 300e6
ROUT = 1e6
RON = 1.0
TRANSFER = 20e-9
RESET_VALUES = [5e-9, 10e-9, 20e-9]
T1_START = 10e-9
DEAD = 1e-9


def _pwl(points):
    return " ".join(f"{t:.12g} {v:g}" for t, v in points)


def deck(initial_out: float, reset_time: float) -> tuple[str, dict[str, float]]:
    gm = A0 / ROUT
    cdom = A0 / (2 * math.pi * ROUT * GBW)
    sum_ic = -initial_out / A0
    cfb_ic = initial_out - sum_ic

    t1_end = T1_START + TRANSFER
    reset_start = t1_end + DEAD
    reset_end = reset_start + reset_time
    t2_start = reset_end + DEAD
    t2_end = t2_start + TRANSFER
    t_after = t2_end - 0.2e-9
    t_sample2 = t2_start - 0.2e-9
    t_stop = t2_end + 5e-9

    transfer_ctl = _pwl(
        [
            (0, 0),
            (T1_START - 0.1e-9, 0),
            (T1_START, 1),
            (t1_end, 1),
            (t1_end + 0.1e-9, 0),
            (t2_start - 0.1e-9, 0),
            (t2_start, 1),
            (t2_end, 1),
            (t2_end + 0.1e-9, 0),
            (t_stop, 0),
        ]
    )
    reset_ctl = _pwl(
        [
            (0, 0),
            (reset_start - 0.1e-9, 0),
            (reset_start, 1),
            (reset_end, 1),
            (reset_end + 0.1e-9, 0),
            (t_stop, 0),
        ]
    )

    text = f"""* TW-1A C1e3 reusable two-slice self sample bank
.model SW SW(Ron={RON} Roff=1e12 Vt=0.5 Vh=0)
Vx ctlx 0 PWL({transfer_ctl})
Vr ctlr 0 PWL({reset_ctl})
Vref ref 0 {VSAMPLE}
Gop x 0 sum 0 {gm}
Rop x 0 {ROUT}
Cop x 0 {cdom} IC={initial_out}
Ebuf out 0 x 0 1
Cfb out sum {CF} IC={cfb_ic}
Rsum sum 0 1e12
Cs samp 0 {CS} IC={VSAMPLE}
Rsamp samp 0 1e12
Stransfer samp sum ctlx 0 SW
Sreset samp ref ctlr 0 SW
.ic v(x)={initial_out} v(out)={initial_out} v(sum)={sum_ic} v(samp)={VSAMPLE}
.tran 0.01n {t_stop} UIC
.measure tran vbefore FIND v(out) AT=5n
.measure tran vsample2 FIND v(samp) AT={t_sample2}
.measure tran vafter FIND v(out) AT={t_after}
.measure tran vsumhi MAX v(sum) FROM={T1_START + 0.1e-9} TO={t_after}
.measure tran vsumlo MIN v(sum) FROM={T1_START + 0.1e-9} TO={t_after}
.end
"""
    timing = {
        "t1_start": T1_START,
        "t1_end": t1_end,
        "reset_start": reset_start,
        "reset_end": reset_end,
        "t2_start": t2_start,
        "t2_end": t2_end,
        "elapsed": t2_end - T1_START,
    }
    return text, timing


def _measure(text: str, name: str) -> float:
    m = re.search(rf"{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
    if not m:
        raise RuntimeError(f"measure {name!r} missing\n{text}")
    return float(m.group(1))


def run_case(initial_out: float, reset_time: float):
    text_deck, timing = deck(initial_out, reset_time)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir, log = td / "c1e3.cir", td / "c1e3.log"
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
        before = _measure(text, "vbefore")
        after = _measure(text, "vafter")
        sample2 = _measure(text, "vsample2")
        hi = _measure(text, "vsumhi")
        lo = _measure(text, "vsumlo")
        return after - before, sample2, max(abs(hi), abs(lo)), timing


def main() -> None:
    first_pass = None
    for reset_time in RESET_VALUES:
        inc0, sample0, sum0, timing = run_case(0.0, reset_time)
        incp, samplep, sump, _ = run_case(PRECHARGED, reset_time)
        mag_error = abs(abs(inc0) - TARGET_TOTAL) / TARGET_TOTAL
        mismatch = abs(incp - inc0) / max(abs(inc0), abs(incp), 1e-30)
        sample_error = max(abs(sample0 - VSAMPLE), abs(samplep - VSAMPLE)) / VSAMPLE
        ok = mag_error <= 1e-3 and mismatch <= 1e-3
        if ok and first_pass is None:
            first_pass = reset_time
        print(
            f"reset={reset_time*1e9:5.1f}ns packet={inc0*1e3:+.6f}mV "
            f"magerr={100*mag_error:.6f}% mismatch={100*mismatch:.6f}% "
            f"sample2={sample0*1e3:.6f}mV sampleerr={100*sample_error:.6f}% "
            f"vsummax={max(sum0,sump)*1e6:.3f}uV "
            f"elapsed={timing['elapsed']*1e9:.1f}ns pass={ok}"
        )

    print("first passing reset seconds", first_pass)
    if first_pass is None:
        raise SystemExit("C1e3 FAIL: no frozen reset aperture met the 0.1% marker")
    print("C1e3 PASS: one half-range self bank can be reset and reused for two slices")


if __name__ == "__main__":
    main()
