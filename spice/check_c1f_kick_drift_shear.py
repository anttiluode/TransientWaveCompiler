"""C1f: deterministic two-bank kick-drift shear gate.

This process-independent ngspice test does *not* qualify thermal noise. It asks
whether two finite-gain active virtual-sum state banks can execute

    P <- P + K*Z
    Z <- Z + P

with explicit sample/transfer phases, finite switch resistance and the same
state-independent charge-integration principle established by C1c.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile


CSTATE = 1e-9
A0 = 1e5
RON = 1.0
CASES = [
    (0.20, 0.05, -0.00625),
    (-0.15, 0.08, +0.00625),
    (0.12, -0.04, +0.125),
    (-0.10, -0.06, -0.125),
    (0.30, -0.10, +0.05),
]


def deck(z0: float, p0: float, k: float) -> str:
    if k == 0.0:
        raise ValueError("C1f frozen cases require nonzero K")
    ck = abs(k) * CSTATE
    # A positive sampled voltage transferred to the inverting virtual-sum bank
    # produces a negative output packet. Sample -sign(K)*Z so the kick is +K*Z.
    zpol = -1.0 if k > 0 else +1.0

    psum_ic = -p0 / A0
    zsum_ic = -z0 / A0
    pcf_ic = p0 - psum_ic
    zcf_ic = z0 - zsum_ic

    return f"""* TW-1A C1f two-bank kick-drift shear
.model SW SW(Ron={RON} Roff=1e12 Vt=0.5 Vh=0)

* P state bank: out = -A0 * psum
Ep p 0 0 psum {A0}
Cfp p psum {CSTATE} IC={pcf_ic}
Rpsum psum 0 1e12

* Z state bank: out = -A0 * zsum
Ez z 0 0 zsum {A0}
Cfz z zsum {CSTATE} IC={zcf_ic}
Rzsum zsum 0 1e12

* Read-only polarity buffers. Differential hardware can realize these as wire
* orientation; VCVSs prevent this topology gate from inventing source loading.
Ezkick kzsrc 0 z 0 {zpol}
Epneg pneg 0 p 0 -1

* KICK sample: first sample -sign(K)*Z onto |K|*Cstate, then transfer it
* into the P virtual sum.
Ck ks 0 {ck} IC=0
Rkhold ks 0 1e15
Sk_sample ks kzsrc ksample 0 SW
Sk_xfer   ks psum kxfer 0 SW
Vksample ksample 0 PULSE(1 0 8n 0.2n 0.2n 200n 500n)
Vkxfer   kxfer   0 PULSE(0 1 10n 0.2n 0.2n 22n 500n)

* DRIFT sample: after the P kick settles, sample -P onto one Cstate packet
* capacitor, then transfer it into Z, yielding +P increment at Z.
Cd ds 0 {CSTATE} IC=0
Rdhold ds 0 1e15
Sd_sample ds pneg dsample 0 SW
Sd_xfer   ds zsum dxfer 0 SW
Vdsample dsample 0 PULSE(0 1 36n 0.2n 0.2n 10n 500n)
Vdxfer   dxfer   0 PULSE(0 1 50n 0.2n 0.2n 22n 500n)

.ic v(p)={p0} v(psum)={psum_ic} v(z)={z0} v(zsum)={zsum_ic} v(ks)=0 v(ds)=0
.tran 0.05n 110n UIC
.measure tran pbefore FIND v(p) AT=5n
.measure tran zbefore FIND v(z) AT=5n
.measure tran pkicked FIND v(p) AT=40n
.measure tran pafter FIND v(p) AT=100n
.measure tran zafter FIND v(z) AT=100n
.measure tran psumhi MAX v(psum) FROM=0n TO=100n
.measure tran psumlo MIN v(psum) FROM=0n TO=100n
.measure tran zsumhi MAX v(zsum) FROM=0n TO=100n
.measure tran zsumlo MIN v(zsum) FROM=0n TO=100n
.end
"""


def _measure(text: str, name: str) -> float:
    m = re.search(rf"{re.escape(name)}\s*=\s*([-+0-9.eE]+)", text, flags=re.I)
    if not m:
        raise RuntimeError(f"measure {name!r} missing\n{text}")
    return float(m.group(1))


def run_case(z0: float, p0: float, k: float) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cir = td / "c1f.cir"
        log = td / "c1f.log"
        cir.write_text(deck(z0, p0, k), encoding="utf-8")
        proc = subprocess.run(
            ["ngspice", "-b", "-o", str(log), str(cir)],
            text=True,
            capture_output=True,
            timeout=30,
        )
        text = (log.read_text(errors="replace") if log.exists() else "") + proc.stdout + proc.stderr
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed ({proc.returncode})\n{text}")
        names = (
            "pbefore",
            "zbefore",
            "pkicked",
            "pafter",
            "zafter",
            "psumhi",
            "psumlo",
            "zsumhi",
            "zsumlo",
        )
        return {name: _measure(text, name) for name in names}


def scaled_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1e-3)


def main() -> None:
    max_p_err = 0.0
    max_z_err = 0.0
    max_p_disturb = 0.0
    max_vsum = 0.0

    for z0, p0, k in CASES:
        r = run_case(z0, p0, k)
        # Use the actually measured pre-shear states so finite-A0 initial
        # consistency is not mistaken for packet error.
        p1_expected = r["pbefore"] + k * r["zbefore"]
        z1_expected = r["zbefore"] + p1_expected

        p_err = scaled_error(r["pkicked"], p1_expected)
        z_err = scaled_error(r["zafter"], z1_expected)
        p_disturb = scaled_error(r["pafter"], r["pkicked"])
        vsum = max(
            abs(r["psumhi"]),
            abs(r["psumlo"]),
            abs(r["zsumhi"]),
            abs(r["zsumlo"]),
        )
        max_p_err = max(max_p_err, p_err)
        max_z_err = max(max_z_err, z_err)
        max_p_disturb = max(max_p_disturb, p_disturb)
        max_vsum = max(max_vsum, vsum)

        print(
            f"Z0={z0:+.5f} P0={p0:+.5f} K={k:+.5f} "
            f"P1={r['pkicked']:+.8f}/{p1_expected:+.8f} "
            f"Z1={r['zafter']:+.8f}/{z1_expected:+.8f} "
            f"Perr={100*p_err:.6f}% Zerr={100*z_err:.6f}% "
            f"Pdist={100*p_disturb:.6f}% vsum={vsum*1e6:.3f}uV"
        )

    print(f"max P1 scaled error       {100*max_p_err:.6f}%")
    print(f"max Z1 scaled error       {100*max_z_err:.6f}%")
    print(f"max P drift disturbance   {100*max_p_disturb:.6f}%")
    print(f"max virtual-sum excursion {max_vsum*1e6:.6f} uV")

    if max_p_err > 1e-3:
        raise SystemExit("C1f FAIL: P kick misses 0.1% marker")
    if max_z_err > 1e-3:
        raise SystemExit("C1f FAIL: Z drift misses 0.1% marker")
    if max_p_disturb > 1e-3:
        raise SystemExit("C1f FAIL: read-only drift sampling disturbs P by >0.1%")
    if max_vsum > 100e-6:
        raise SystemExit("C1f FAIL: virtual-sum node excursion exceeds 100 uV")

    print("C1f PASS: two active state banks execute deterministic kick-drift shears")


if __name__ == "__main__":
    main()
