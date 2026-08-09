# TW-1A v0.5 C0d per-edge segmented-mismatch learning gate — preregistration

This gate is frozen before any temporal-order learning result using fabricated
per-edge capacitor mismatch is inspected.

## Question

Does the qualified phase-symmetric v0.5 machine retain its learning primitive
when every physical reciprocal edge receives its own fabricated 4+3 segmented
magnitude capacitor codebook at 3% unit-cap mismatch, and the controller uses
only that site's measured physical levels?

## Untouched bodies

```text
1700, 1701, 1702, 1703, 1704,
1705, 1706, 1707, 1708, 1709
```

These bodies were not used by previous formal gates or diagnostics.

## Physical C0d codebook

Each physical edge independently draws 127 unit capacitors:

```text
C_i/Cunit = 1 + Normal(0, 0.03)
Cunit/Csum = 0.001
```

Magnitude selection is the C0d working topology:

```text
lower binary groups: 1, 2, 4, 8 units
upper thermometer:   seven ordered 16-unit segments
units total:         127
```

For every magnitude code 0..127, selected fabricated capacitance is converted to
its physical charge-sharing level.  The controller may measure the resulting
site-specific codebook and choose the nearest physical code.  It may not sort,
repair, interpolate, or invent levels.

Code zero remains the all-branches-off physical state.

## Hard fabrication-yield predicate

Before training, the exact fabricated target tile for each body is audited.
The formal gate immediately fails unless

```text
10/10 tiles have 112/112 strictly monotonic magnitude codebooks.
```

A non-monotonic edge is a hardware yield failure even if nearest-code software
could still choose among its levels.

## Frozen learner

```text
iterations = 30
step_size = 0.20
normalize_rms = true
shuffle_seed = 1729
```

## Frozen mixed-signal background

All non-capacitor conditions remain exactly those of the qualified v0.5 corner:

```text
edge path                     signed 8-bit / measured local codebook
self code                     12 bit
drive DAC                      8 bit
error DAC                     10 bit
sense ADC                      8 bit
state full scale              20
sense ADC full scale           2
state clipping                 enabled

leakage_rate                   5e-4/tick
leakage_cv                     0.50
state_noise_std                5e-9 FS
credit_noise_fraction          0.25
credit_offset_fraction         1.5e-4

raw reciprocal edge gain CV    0.10
edge calibration residual      0.001
raw common settling loss       0.10
A/B hold residual mismatch     0.001 RMS
raw self gain CV               0.10
self calibration residual      0.001
raw -PREV mismatch             0.03 RMS
-PREV calibration residual     0.001
raw terminal clone mismatch    0.05 RMS
clone calibration residual     0.001

raw common switch kick         3e-4 FS
raw differential switch kick   1e-4 FS
autozero cancellation error    0.02
common/diff residual floors    2e-6 / 1e-6 FS

error-DAC sign asymmetry        0.10
LCC curvature                  1.0
credit accumulator leakage     0.01/tick
```

Legacy B-only settling loss and A->B edge memory remain structurally zero.

## Learning qualification predicate

If and only if the fabrication-yield predicate passes, the learning gate
qualifies when all previous v0.5 conditions also hold:

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

No failed body or fabricated tile may be replaced.  A failure remains in the
record and 1700–1709 become diagnostic-only.

## Claim boundary

A pass establishes emulator-level compatibility with **independent 3%-sigma
segmented capacitor codebooks per physical edge**.  It still does not include
layout-correlated gradients, extracted parasitics, MOS switch mismatch, or noisy
codebook measurement.  Those remain later C0d/C0e physical gates.
