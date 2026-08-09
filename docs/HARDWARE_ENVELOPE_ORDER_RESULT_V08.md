# TW-1A hardware envelope — 10-ppm simultaneous corner result v0.8

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V08.md`

Workflow: `hardware-envelope-order-v08`

Fresh confirmatory seeds: 980–989.

## Frozen simultaneous corner

- rank-one reciprocal edge-cell Q: **8 bits**;
- drive + returned-error DAC: **8 bits**;
- sense ADC: **8 bits**, with compiler-predicted static PGA;
- mean leakage: **0.0005/tick**;
- leakage spatial CV: **0.50**;
- time-mirror gain error: **0.15 = 15%**;
- differential REVERSE_PLUS / REVERSE_MINUS drift: **`1e-5` RMS = 0.001% = 10 ppm**;
- zero-mean local credit readout noise: **0.25 = 25% of credit RMS**;
- systematic local credit offset: **0.00015 = 0.015%**;
- analog state noise: **`5e-9` of state full scale RMS per node/tick**, equal to `1e-7` state units for the frozen +/-20 internal range.

## Result

**QUALIFIED: PASS (6/6 registered criteria).**

Across all ten untouched irregular arbors:

- every exact learner improved;
- **10/10** had `DeltaC >= 0.10`;
- median exact contrast improvement: **+0.955218**;
- exact final contrast beat shuffled final contrast in **10/10**;
- median placed-credit improvement advantage: **+0.898327**;
- all values remained finite.

Per-seed exact improvements and placement gaps:

| seed | DeltaC exact | placement gap |
|---:|---:|---:|
| 980 | +0.119584 | +0.170626 |
| 981 | +1.174679 | +0.791444 |
| 982 | +0.348583 | +0.316047 |
| 983 | +0.894169 | +1.391156 |
| 984 | +0.371705 | +0.372585 |
| 985 | +1.099098 | +1.005210 |
| 986 | +0.960603 | +1.504747 |
| 987 | +0.949832 | +1.156485 |
| 988 | +1.593608 | +1.749498 |
| 989 | +0.983945 | +0.788184 |

## What is now demonstrated

This is the first preregistered **simultaneous mixed-signal operating point** earned by the rank-one TW-1A emulator on the temporal-order benchmark.

It is not a claim that every independent v0.5 tolerance maximum can be combined. v0.6 and v0.7 explicitly showed that they cannot. In combined operation, differential PLUS/MINUS pass mismatch is the dominant interaction found so far.

The current engineering picture is therefore:

- one reciprocal physical edge must be represented as one quantized rank-one edge cell;
- clean 8-bit Q/DAC/ADC operation is strong;
- the originally requested 8/8/8 + 5% mirror + 0.2% drift + 5% credit-noise point passed one six-seed nominal block, but **0.2% differential drift is not robust under simultaneous damage**;
- a simultaneous corner is demonstrated once differential drift is reduced to **10 ppm RMS** while retaining substantial leakage, mirror error, credit noise, systematic offset, and state noise.

## Independent v0.5/v0.6 requirements retained for reference

Benchmark-specific precision floors:

- rank-one edge-cell Q: **>=5 bits** within the tested grid;
- DAC: **>=4 tested bits**;
- ADC + static PGA: **>=5 bits**.

Architecture-wide returned-error dynamic range for the compiler's full `G=8` boundary-gain promise remains separate and is approximately a **10-bit signed zero-preserving path** under the conservative four-code weakest-error margin.

Independent damage boundaries at 8/8/8:

- mean leakage: boundary `0.002/tick`, inward recommendation `0.001/tick`;
- mirror error: boundary `0.50`, inward recommendation `0.30`;
- differential +/- drift: independent boundary `0.001`, but combined-context boundary is far tighter;
- state noise: refined boundary `3e-8 FS`, inward recommendation `1e-8 FS`;
- credit noise: at least 100% RMS passed independently;
- credit offset: refined boundary `0.001`, inward recommendation `0.0003`;
- leakage CV: at least 150% passed at mean leakage 0.001/tick.

## Next engineering question

Ten-ppm differential matching is an unattractive fabrication requirement. The next branch should therefore change the **estimator**, not keep tightening fabrication tolerances.

The simplest positive control is repeated independent PLUS/MINUS measurements whose local credits are averaged before the host update. If averaging restores learning at the originally proposed 0.2% differential drift, TW-1A can trade reverse-pass count for drift tolerance. A later single-run chopped/lock-in estimator may recover the same cancellation more efficiently.
