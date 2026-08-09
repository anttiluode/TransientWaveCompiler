# TW-1A v0.8 kick-calibrated fresh qualification preregistration

This document is frozen before any result is observed on fresh temporal-order
bodies 2200--2209.

The previous fresh v0.8 gate on 2100--2109 failed narrowly because seed 2107
was sensitive to residual edge switch kick. Same-silicon diagnostics isolated
the mechanism: reducing the foreground kick-cancellation measurement error is
sufficient; tightening the independent residual floor is not.

## Architecture under test

The architecture is unchanged from v0.8 common/difference active summing:

- common/difference reverse coordinates (`C=F`, `D=A`);
- no terminal analog clone;
- one signed error injection into D, no matched +/- error pair;
- structural `-PREV` bank-role/orientation inversion;
- active virtual charge summing;
- 127-unit 4-bit-binary + 3-bit-thermometer reciprocal edge banks;
- 3% RMS independent unit-cap mismatch;
- 1% RMS site-common `Cunit/Cstate` ratio mismatch;
- nominal edge positive full scale 0.265;
- active edge thermal base `b=1e-5`;
- retained C/D hold mismatch, state leakage, self calibration, converter
  precision, LCC curvature, credit noise/offset and credit accumulator leakage.

## Only changed circuit requirement

```text
raw common kick RMS                 3e-4 state FS
raw differential kick RMS           1e-4 state FS
foreground cancellation error RMS   0.005   (0.5%)
residual common floor RMS            2e-6 state FS
residual differential floor RMS      1e-6 state FS
```

Compared with the failed fresh gate, only the cancellation measurement error is
changed, from 2% RMS to 0.5% RMS. The residual floors remain unchanged.

This operating point is the already-tested `cancel x0.25` same-silicon point,
not an interpolated value.

## Fresh task bodies

```text
2200, 2201, ..., 2209
```

No tuning, additional condition or threshold change is permitted after these
results are observed.

## Fabrication gate

Every target tile must satisfy:

```text
112/112 measured edge codebooks strictly monotonic
112/112 site ratio scales positive
112/112 measured code-127 ranges >= 0.250
```

Measured site-specific codebooks are used directly with no repair, sorting or
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

A pass qualifies the emulator-level v0.8 common/difference active-summing
contract with the 0.5% foreground kick-cancellation requirement and unchanged
2 ppm / 1 ppm residual floors. It still does not qualify a transistor OTA,
switch layout, square detector or foundry process.

A failure is preserved and 2200--2209 become diagnostic-only.
