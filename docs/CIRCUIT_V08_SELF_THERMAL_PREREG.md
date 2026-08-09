# TW-1A v0.8 fresh qualification with self-sampling kT/C

This document is frozen before any result is observed on fresh temporal-order
bodies 2300--2309.

The previous fresh v0.8 kick-calibrated gate passed on 2200--2209. A subsequent
spent-body diagnostic added the missing local programmable self-sample thermal
path and passed at the same thermal base `b=1e-5`.

## Architecture and operating point

The qualification includes simultaneously:

- common/difference reverse coordinates (`C=F`, `D=A`);
- no terminal analog clone;
- one signed error injection into D;
- structural `-PREV` bank-role/orientation inversion;
- active virtual charge summing;
- reciprocal edge capacitor banks with nominal positive range 0.265;
- 3% RMS independent edge unit-cap mismatch;
- 1% RMS site-common edge `Cunit/Cstate` ratio mismatch;
- active edge-sampling thermal base `b_edge=1e-5`;
- local self-sampling thermal base `b_self=1e-5`, using
  `sigma_self/VFS=b_self*sqrt(|d|)`;
- 0.5% RMS foreground edge switch-kick cancellation measurement error;
- unchanged 2 ppm common / 1 ppm differential residual kick floors;
- retained C/D hold mismatch, self gain/calibration residual, state leakage,
  converter precision, square/LCC curvature, local-credit readout noise/offset
  and credit accumulator leakage.

The self thermal law corresponds to the C1e2/C1e3 working self architecture:
two equal samples through one reusable half-range `|self|<=1.5` bank. Equal
slicing changes timing/load but not the total ideal kT/C variance.

## Fresh bodies

```text
2300, 2301, ..., 2309
```

No parameter, threshold, training duration or condition may be changed after
these results are observed.

## Fabrication gate

Every target tile must satisfy:

```text
112/112 measured edge codebooks strictly monotonic
112/112 site ratio scales positive
112/112 measured code-127 ranges >= 0.250
```

Measured site-specific codebooks are used directly with no sorting, repair or
extrapolation.

## Learning gate

```text
training iterations  30
step size             0.20
```

Qualification requires all of:

```text
10/10 exact improvements >= +0.10
10/10 final exact contrasts > shuffled-credit controls
median exact improvement >= +0.30
median placement gap >= +0.25
```

## Interpretation

A pass supersedes the previous v0.8 emulator checkpoint by additionally
qualifying the circuit-native local self-sampling kT/C path at `b_self=1e-5`.
It still does not qualify the transistor OTA, the physical self-code capacitor
array, sample-reference driver, local square detector, or foundry layout.

A failure is preserved and seeds 2300--2309 become diagnostic-only.
