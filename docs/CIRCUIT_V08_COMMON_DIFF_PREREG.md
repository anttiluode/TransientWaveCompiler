# TW-1A v0.8 common/difference fresh qualification preregistration

This document is frozen before any v0.8 result is observed on fresh temporal-order bodies 2100--2109.

## Architecture under test

The qualification combines the currently supported physical contract:

- active virtual charge summing; edge coefficient is measured `Cselected/Cstate`;
- common/difference reverse coordinates (`C=F`, `D=A`), so no terminal analog clone and no matched +/- error injection pair;
- structural `-PREV` through two-bank role/orientation inversion;
- one signed error waveform injected into D;
- local credit reconstructed only at the sensor from `delta_C +/- delta_D` and the same square/LCC difference identity;
- 127-unit 4-bit-binary + 3-bit-thermometer reciprocal edge banks;
- 3% RMS independent unit-cap mismatch;
- 1% RMS site-common `Cunit/Cstate` mismatch using an independent deterministic fabrication stream;
- nominal positive edge range 0.265 (`Cunit/Cstate=0.265/127`);
- active-integrator sampled-edge thermal base `b=1e-5`;
- retained C/D hold mismatch, switch-kick cancellation residuals, state leakage, self calibration, converter precision, LCC curvature, local-credit readout noise/offset and credit accumulator leakage from the v0.7/C0e background.

The inherited terminal-clone mismatch and +/- error-sign-asymmetry values may still be drawn internally for RNG compatibility but are physically obsolete and are never consumed by the v0.8 interpreter.

## Fresh task bodies

```text
2100, 2101, ..., 2109
```

These bodies are reserved for this qualification. No parameter or threshold may be changed after observing their result.

## Frozen fabrication gate

Every target tile must satisfy all of:

```text
112/112 edge codebooks strictly monotonic
112/112 site ratio scales positive
112/112 measured code-127 edge ranges >= 0.250
```

Measured site-specific codebooks are used as fabricated. They may not be sorted, repaired or extrapolated.

## Frozen learning protocol

```text
training iterations  30
step size             0.20
thermal base b        1e-5
```

Qualification requires:

```text
10/10 exact improvements >= +0.10
10/10 exact final contrasts > shuffled-credit controls
median exact improvement >= +0.30
median placement gap >= +0.25
```

## Interpretation

A pass qualifies the **emulator-level v0.8 common/difference active-summing contract** at the stated fabrication and thermal point. It does not qualify a transistor OTA, square detector, switch network, or foundry layout. Those remain circuit bring-up gates.

A failure is preserved and the 2100--2109 bodies become diagnostic-only. No automatic fallback or threshold relaxation is allowed.
