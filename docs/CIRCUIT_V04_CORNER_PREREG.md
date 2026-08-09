# TW-1A v0.4 calibration-first simultaneous corner — preregistration

This experiment is frozen before any v0.4 learning result is inspected.

## Question

Does the calibration-first architecture recover the temporal-order learning
primitive under a simultaneous mixed-signal corner when raw fabricated mismatch
is intentionally much larger than the allowed post-calibration residual?

## Untouched bodies

```text
1400, 1401, 1402, 1403, 1404,
1405, 1406, 1407, 1408, 1409
```

These bodies were not used by the v0.2/v0.3 sweeps, failed corners, diagnostics,
or reference audits.

## Frozen learner

```text
iterations = 30
step_size = 0.20
normalize_rms = true
shuffle_seed = 1729
```

The shuffled arm receives the same measured credit values with one frozen edge
permutation, as in the previous temporal-order qualification.

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

## Background physical errors retained from v0.3

```text
leakage_rate                 5e-4 / tick
leakage_cv                   0.50
state_noise_std              5e-9 FS
credit_noise_fraction        0.25
credit_offset_fraction       1.5e-4
edge_settling_error          0.10
A->B edge memory             0.03
error DAC sign asymmetry     0.10
LCC curvature                1.0
credit accumulator leakage   0.01 / reverse tick
```

These are not calibrated away in v0.4.

## Raw mismatch and frozen calibration residuals

### Reciprocal edge MDAC

```text
raw edge gain CV             0.10
foreground calibration       enabled
measurement residual std     0.001
```

The 8-bit edge code is inverse-programmed through the measured gain map.

### Node self MDAC

```text
raw self gain CV             0.10
foreground calibration       enabled
measurement residual std     0.001
```

The 12-bit self code is inverse-programmed through the measured gain map.

### -PREV ratio

```text
raw ratio mismatch std       0.03
foreground trim              enabled
measurement residual std     0.001
trim resolution              12 bit
trim range                   +/-12.5%
```

### Terminal A->B clone

```text
raw clone gain mismatch std  0.05
foreground trim              enabled
measurement residual std     0.001
trim resolution              12 bit
trim range                   +/-12.5%
clone noise                  0
```

### Edge switch charge

Raw switch disturbance is intentionally larger than the v0.3 residual packet:

```text
raw common packet std        3e-4 FS
raw differential packet std  1e-4 FS
autozero                     enabled
cancellation fractional err  0.02
common residual floor        2e-6 FS
differential residual floor  1e-6 FS
```

The recurrence sees only `raw - measured_cancellation + residual_floor`.

## Qualification predicate

The corner qualifies only if all four conditions hold across all ten bodies:

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

No failed body may be removed or replaced.  If this corner fails, it remains a
formal failure and the 1400–1409 bodies become diagnostic-only.

## Interpretation rule

A pass would establish an emulator-level calibration envelope, not transistor
feasibility.  A fail would mean that calibration-first modeling alone does not
close the simultaneous interaction problem at these frozen residuals.
