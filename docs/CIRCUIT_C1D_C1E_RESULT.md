# TW-1A C1d/C1e active-integrator result

This document records the process-independent first-order active-integrator
results frozen in `CIRCUIT_C1D_C1E_PREREG.md` and the self-slicing follow-up in
`CIRCUIT_C1E2_SELF_SLICING_PREREG.md`.

## C1d — finite DC gain

Acceptance marker: <=0.1% packet magnitude error and <=0.1% dependence of packet
increment on whether the output started at 0 or +0.2 V.

```text
load                beta       first passing A0
edge Cin/Cf=0.265    0.7905         3,000
self Cin/Cf=3.0      0.2500        30,000
```

At the worst unsliced self load, A0=30,000 produced about 0.0133% packet
magnitude error and 0.0781% state-dependent mismatch. Thus the earlier
A0=100,000 working number is conservative for this static first-order gate.

A separate compiler proof in `transientwave/integrator_gain_coordinates.py`
shows that fixed positive node-integrator gain can additionally be absorbed into
a symmetric coordinate transform; C1d therefore should not be interpreted as a
requirement for absolute uncalibrated gain accuracy. Drift and signal-dependent
gain remain outside that transform.

## C1e — finite 20 ns bandwidth

With A0=100,000 and one 20 ns transfer aperture:

```text
edge Cin/Cf=0.265
  30 MHz      fail
  100 MHz     PASS
  300 MHz     PASS
  1 GHz       PASS

monolithic self Cin/Cf=3
  30 MHz      44.1% packet error
  100 MHz     11.1%
  300 MHz      1.67%
  1 GHz        0.352%   FAIL
```

Therefore C1e is a **real architecture failure** for one monolithic |self|=3
sample capacitor. The failure includes the finite transfer-switch RC as well as
the one-pole amplifier response. It is not fixed by simply carrying the old
300 MHz number forward.

## C1e2 — equal self-packet slicing

C1e2 keeps the total ideal |self|=3 contribution unchanged while splitting it
into N sequential packets, so the instantaneous load is `Cin/Cf=3/N`.
Each transfer retains the 20 ns aperture.

```text
slices N   load alpha   beta      first passing frozen GBW   self transfer time
1          3.000        0.2500    none through 1 GHz          20 ns
2          1.500        0.4000    300 MHz                      45 ns
4          0.750        0.5714    300 MHz                      95 ns
8          0.375        0.7273    100 MHz                     195 ns
```

Representative N=2, 300 MHz result:

```text
total packet          -25.58975 mV
magnitude error          0.04004%
state-dependent mismatch 0.02325%
```

The working timing architecture is therefore **two self slices at 300 MHz**,
subject to the next gate: prove that one half-size self bank can be reset,
resampled and reused for the second slice without losing the 0.1% marker.

C1e2 used separately initialized sample capacitors to keep the amplifier
trajectory continuous while isolating transfer dynamics. It does not yet prove
the physical resample/reset cycle or its energy.
