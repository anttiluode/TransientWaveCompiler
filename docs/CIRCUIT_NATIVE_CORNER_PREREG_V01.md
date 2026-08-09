# TW-1A circuit-native simultaneous corner preregistration v0.1

Status: **frozen before combined-corner results are inspected**.

The one-axis circuit-native sweep has completed. This experiment tests whether its inward design values survive **simultaneously**, while also restoring the background mixed-signal imperfections that had already been demonstrated in the older emulator.

Independent one-axis limits are not assumed to form a safe Cartesian box. This experiment may fail.

## Bodies

Untouched temporal-order arbors: **1200-1209**.

These bodies were not used in the v0.1 circuit-native reference confirmation (1100-1104) or the one-axis sweeps (1110-1114).

## Training

- 30 host updates;
- step size 0.20;
- RMS-normalized update;
- same measured combined credit sent to a fixed norm-matched shuffled-edge control;
- one static PGA selected from the nominal initial model and frozen through training.

## Simultaneous circuit configuration

Precision:

```text
edge MDAC             8 signed exact-zero bits
self MDAC            12 signed bits
forward drive DAC     8 signed bits
returned-error DAC   10 signed bits
sense ADC             8 bits + static PGA
```

Circuit-native inward values from the frozen v0.1 sweep:

```text
common edge-MDAC gain CV                  0.10
common self-MDAC gain CV                  0.003
terminal clone gain RMS                   0.01
lane-B edge settling deficit              0.10
A -> B edge memory                        0.03
lane-select edge charge injection RMS     3e-5 state FS / active edge / tick
-PREV ratio RMS error                     0.003
error-DAC +/- magnitude asymmetry         0.10
normalized LCC quartic curvature          1.0
credit accumulator decay rate / tick      0.01
```

Restored older mixed-signal background:

```text
state leakage rate / tick                 0.0005
state leakage spatial CV                  0.50
state noise RMS / state full scale        5e-9
final credit readout noise fraction       0.25
final credit static offset fraction       0.00015
```

The legacy `mirror_error` and independent `differential_pass_drift` remain exactly zero because they are not physical primitives of the lockstep circuit.

## PASS criteria

All must hold:

1. **10/10** placed-credit learners improve normalized temporal-order contrast by at least `+0.10`;
2. **10/10** placed-credit final contrasts exceed their shuffled-credit controls;
3. median placed-credit improvement >= `+0.30`;
4. median placed-minus-shuffled improvement gap >= `+0.25`.

No criterion will be relaxed after the run.

## Interpretation

### If PASS

The inward one-axis values become the first demonstrated **combined circuit-level design corner** for TW-1A v0.2. They remain emulator evidence, not transistor/process guarantees.

### If FAIL

The failed v0.1 corner is retained. Follow-up diagnosis may remove one group of errors at a time to find interactions, but a new combined corner must be separately preregistered on new bodies rather than tuned on 1200-1209.

## Hardware claim boundary

Even a PASS does not establish area, energy, bandwidth, thermal behavior, capacitor sizing, op-amp settling, clock feedthrough or layout matching. It only says the proposed circuit topology has a nontrivial simultaneous behavioral error budget worth taking into SPICE / board prototyping.