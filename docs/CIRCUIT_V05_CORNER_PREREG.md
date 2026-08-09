# TW-1A v0.5 phase-symmetric simultaneous corner — preregistration

This gate is frozen before any v0.5 temporal-order learning result is inspected.

## Question

Does replacing A-first/B-second edge evaluation with matched pre-settled A/B
coefficient holds remove the dominant v0.4 simultaneous-corner failure while
retaining the same calibration-first mixed-signal background?

## Untouched bodies

```text
1500, 1501, 1502, 1503, 1504,
1505, 1506, 1507, 1508, 1509
```

These seeds were not used by any v0.2, v0.3 or v0.4 formal gate or diagnostic.

## Frozen learner

```text
iterations = 30
step_size = 0.20
normalize_rms = true
shuffle_seed = 1729
```

## Converter / state contract

```text
edge code        8 bit
self code        12 bit
drive DAC         8 bit
error DAC        10 bit
sense ADC         8 bit
state full scale 20
sense ADC FS      2
state clipping    enabled
```

## Background retained unchanged from v0.4

```text
leakage_rate                 5e-4 / tick
leakage_cv                   0.50
state_noise_std              5e-9 FS
credit_noise_fraction        0.25
credit_offset_fraction       1.5e-4
error DAC sign asymmetry     0.10
LCC curvature                1.0
credit accumulator leakage   0.01 / reverse tick
```

## Calibration-first fixed mismatch

```text
raw edge gain CV             0.10
edge calibration residual    0.001
raw self gain CV             0.10
self calibration residual    0.001
raw -PREV mismatch std       0.03
-PREV calibration residual   0.001
-PREV trim                   12 bit, +/-12.5%
raw clone mismatch std       0.05
clone calibration residual   0.001
clone trim                   12 bit, +/-12.5%
clone noise                  0
```

## Edge switch charge / autozero

```text
raw common packet std        3e-4 FS
raw differential packet std  1e-4 FS
autozero                     enabled
cancellation fractional err  0.02
common residual floor        2e-6 FS
differential residual floor  1e-6 FS
```

## v0.5 phase-symmetric edge contract

The v0.4 B-only edge settling and A->B state-dependent residue paths are
structurally forbidden:

```text
legacy edge_settling_error   0
legacy ab_edge_memory        0
```

Instead both reverse lane coefficient holds are charged before either lane
evaluates:

```text
raw common settling loss     0.10
A/B hold residual mismatch   0.001 RMS fractional
```

The 10% common settling loss multiplies the fabricated reciprocal edge transfer
and is included in the foreground measured edge map.  The 0.1% A/B hold mismatch
is the remaining reverse-specific edge symmetry error.

## Qualification predicate

The corner qualifies only if all conditions hold:

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

No body may be removed or replaced.  A failed gate remains a formal failure and
1500–1509 become diagnostic-only.

## Interpretation

A pass establishes an emulator-level phase-symmetric calibration envelope.  It
does not establish transistor feasibility; SPICE must still demonstrate that
matched pre-settled holds can achieve the frozen residual mismatch and charge
cancellation targets.
