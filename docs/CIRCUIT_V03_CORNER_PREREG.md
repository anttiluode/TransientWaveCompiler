# TW-1A v0.3 simultaneous circuit corner preregistration

Status: **frozen before v0.3 combined-corner results are inspected**.

TW-1A v0.2's first combined corner formally failed. Diagnostics on those spent bodies identified independent lane-select charge injection as the dominant failure and uncalibrated self-MDAC gain as the next strong interaction. TW-1A v0.3 changes both primitives and has passed fresh isolated sweeps.

This is the first simultaneous test of the revised circuit architecture.

## Fresh bodies

Untouched temporal-order arbors: **1300-1309**.

They were not used in v0.2 development/diagnosis or v0.3 primitive sweeps.

## Training

- 30 host updates;
- step size 0.20;
- RMS-normalized update;
- fixed norm-matched shuffled-credit control;
- static sense PGA selected from nominal initial model and frozen through training.

## Precision

```text
reciprocal edge MDAC       8 signed exact-zero bits
calibrated self MDAC      12 signed bits, +/-3 command range
forward drive DAC          8 signed bits
returned-error DAC        10 signed bits
sense ADC                  8 bits + static PGA
```

## v0.3 circuit values

```text
common edge-MDAC gain CV                   0.10
raw self-MDAC gain CV                      0.10
self gain-calibration residual RMS         0.001   = 0.1%
terminal A->B clone gain RMS               0.01    = 1%
lane-B edge settling deficit               0.10
A->B edge memory                           0.03
common edge charge injection RMS           3e-5 state FS / active edge / tick
residual A/B differential injection RMS    1e-5 state FS / active edge / tick
-PREV ratio RMS error                      0.003   = 0.3%
error-DAC +/- magnitude asymmetry          0.10
normalized LCC quartic curvature           1.0
credit accumulator decay rate / tick       0.01
```

The legacy v0.2 independent `edge_charge_injection_std` is exactly zero. Legacy abstract `mirror_error` and independent PLUS/MINUS `differential_pass_drift` are also exactly zero because they are not physical primitives of the lockstep architecture.

## Restored older mixed-signal background

```text
state leakage / tick                       0.0005
state leakage spatial CV                   0.50
state noise RMS / state full scale         5e-9
final credit readout noise fraction        0.25
final credit static offset fraction        0.00015
```

## PASS criteria

All must hold:

1. **10/10** placed-credit learners improve normalized temporal-order contrast by at least `+0.10`;
2. **10/10** placed-credit final contrasts exceed shuffled-credit final contrasts;
3. median placed improvement >= `+0.30`;
4. median placed-minus-shuffled improvement gap >= `+0.25`.

No criterion will be relaxed after results.

## Interpretation

### PASS

A pass earns the first demonstrated combined behavioral corner for the **charge-balanced, calibrated TW-1A v0.3 circuit architecture**. It remains emulator evidence, not a transistor/process guarantee.

### FAIL

The failure is retained. Diagnosis may use 1300-1309 only after the preregistered result is frozen, and any further revised corner requires new bodies.

## Explicit kill boundary

Even a pass does not establish ASIC feasibility unless later SPICE/board work can plausibly meet the two new residual specifications:

- <=0.1% self calibration error over the required retention/update interval;
- <=1e-5 state-FS RMS differential lane-switch injection per active edge/tick.

Those are now circuit measurement targets rather than simulator narrative knobs.