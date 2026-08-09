# TW-1A v0.5 C0c capacitor-codebook learning gate — preregistration

This gate is frozen before any temporal-order learning result using the C0c
nonuniform capacitor codebook is inspected.

## Question

Does the already-qualified phase-symmetric v0.5 machine retain its edge-credit
learning behavior when the ideal uniformly spaced signed 8-bit edge coefficient
ladder is replaced by the physical C0c charge-sharing level set?

## Physical codebook

C0c uses a seven-bit magnitude capacitor array with

```text
Cunit/Csum = 0.001
magnitude codes 0..127
```

For magnitude `m`, the differential charge-sharing transfer is proportional to

```text
f(m) = m*r / (1 + 2*m*r),  r = Cunit/Csum.
```

The level set is normalized so code 127 still equals the backend edge full scale
`|a_e| = 0.25`. Positive/negative sign is applied by the reciprocal transfer
crossbar. Code zero remains exactly zero in the emulator codebook.

The compiler/controller is allowed to choose the nearest measured physical level;
it is **not** allowed to linearize the analog circuit by inventing extra codes.

## Untouched bodies

```text
1600, 1601, 1602, 1603, 1604,
1605, 1606, 1607, 1608, 1609
```

These have not been used in v0.2-v0.5 formal gates or diagnostics.

## Frozen learner

```text
iterations = 30
step_size = 0.20
normalize_rms = true
shuffle_seed = 1729
```

## Frozen physical background

Use exactly the qualified v0.5 simultaneous-corner configuration:

```text
edge bits                       8 (C0c codebook)
self bits                      12
drive DAC bits                  8
error DAC bits                 10
sense ADC bits                  8
state full scale               20
ADC full scale                  2
state clipping                  enabled

leakage_rate                    5e-4/tick
leakage_cv                      0.50
state_noise_std                 5e-9 FS
credit_noise_fraction           0.25
credit_offset_fraction          1.5e-4

raw edge gain CV                0.10
edge calibration residual       0.001
raw common settling loss        0.10
A/B hold residual mismatch      0.001 RMS
raw self gain CV                0.10
self calibration residual       0.001
raw -PREV mismatch              0.03 RMS
-PREV calibration residual      0.001
raw terminal clone mismatch     0.05 RMS
clone calibration residual      0.001

raw common switch kick          3e-4 FS
raw differential switch kick    1e-4 FS
charge cancellation error       0.02
common/diff residual floors     2e-6 / 1e-6 FS

error-DAC sign asymmetry         0.10
LCC curvature                   1.0
credit accumulator leakage      0.01/tick
```

Legacy B-only settling loss and A->B edge memory remain structurally zero.

## Qualification predicate

Exactly the same predicate as the qualified v0.5 gate:

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

No failed body may be removed or replaced. If this gate fails, bodies 1600–1609
become diagnostic-only and the failure remains part of the record.

## Claim boundary

A pass means the measured C0c **level spacing** can replace the ideal uniform
edge ladder at emulator level. It does not yet include capacitor mismatch,
switch parasitics, or per-edge codebook variation. Those belong to the next C0d
mismatch/calibration gate.
