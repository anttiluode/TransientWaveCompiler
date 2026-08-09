# TW-1A v0.7 active-summing fresh qualification preregistration

This document is frozen before observing any v0.7 result on the reserved fresh
temporal-order bodies 2000--2009.

## Architecture under test

TW-1A v0.7 uses:

- one measured 127-unit, 4-bit-binary + 3-bit-thermometer capacitor bank per
  physical reciprocal edge;
- 3% RMS independent unit-cap fabrication mismatch;
- active virtual charge summing, so `a_e=Cselected/Cstate` directly;
- nominal edge code-127 range 0.255, with no software extrapolation beyond a
  fabricated site's measured range;
- exact-zero edge code;
- phase-symmetric A/B edge reuse and 0.1% RMS A/B hold mismatch;
- structural `-PREV` through two-bank role/orientation inversion, with no analog
  history gain or trim;
- active-integrator edge thermal packets
  `sigma_edge/VFS=b*sqrt(Cselected/Cstate)` at `b=1e-5`;
- the qualified C0e background self calibration, terminal-clone calibration,
  switch-kick cancellation residuals, converter precision, error-DAC
  asymmetry, LCC curvature, credit noise/offset/leakage and state leakage;
- no legacy independent edge-MDAC gain CV and no legacy passive common-settling
  gain. Active-integrator finite A0/GBW remain a separate C1 circuit budget and
  are not silently represented by those obsolete fields.

## Fresh task bodies

```text
2000, 2001, ..., 2009
```

These bodies are reserved for this qualification and must not be used for
parameter tuning before the result is read.

## Frozen physical values specific to v0.7

```text
unit-cap sigma                    0.03 RMS
nominal edge positive full scale 0.255
Cunit/Cstate                     0.255 / 127
legacy edge gain CV              0
legacy common settling loss      0
legacy -PREV ratio mismatch      0
legacy -PREV calibration         disabled
edge kT/C base fraction b        1e-5
```

All other background values are inherited from the qualified C0e operating
point except where structurally obsolete above.

## Fabrication gate

Every one of the ten target-tile fabrications must satisfy both:

1. all 112 physical edge codebooks are strictly monotonic;
2. all 112 measured code-127 magnitudes are at least 0.25.

A failing codebook/range is a fabrication failure and learning is not run for
that body. The controller may select the nearest measured physical level but
may not sort, repair or extrapolate it.

## Learning gate

Qualification requires all of:

```text
10/10 improvements >= +0.10
10/10 final exact contrasts > shuffled-credit controls
median improvement >= +0.30
median placement gap >= +0.25
```

The experiment uses 30 training iterations and step size 0.20, unchanged from
recent formal corners.

## Interpretation

A pass qualifies the v0.7 **emulator-level active-summing physical contract** at
`b=1e-5` with per-edge capacitor fabrication mismatch and the retained C0e
background present simultaneously. It does not qualify a transistor OTA. C1
must separately demonstrate finite-gain, finite-bandwidth, slew, output swing,
noise and loading at the worst-case scheduled feedback factor.
