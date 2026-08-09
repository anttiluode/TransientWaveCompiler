# TW-1A common-realization differential readout — preregistration v0.1

Date frozen: 2026-08-09

## Motivation

The rank-one v0.8 emulator earned a simultaneous mixed-signal corner only after independent REVERSE_PLUS / REVERSE_MINUS operator drift was reduced to 10 ppm RMS. A ppm refinement on spent seeds found failure near 25 ppm in the combined context. Ordinary repeated-measurement averaging at the originally proposed 0.2% independent drift failed for N=1,2,4,8,16 and is analytically too expensive.

The load-bearing distinction is therefore **differential operator mismatch**, not the absolute amount of quasi-static operator drift.

This experiment tests the simplest architectural positive control: PLUS and MINUS remain separate reverse trials, but they use the **same frozen reciprocal drift realization**. This models an estimator whose two phase states are acquired quickly enough, or simultaneously enough, that device drift is common-mode across the subtraction.

It is not yet a claim that a particular chopping circuit achieves this timescale.

## Common-realization drift semantics

For every ordinary target or distractor training microcode execution:

1. FORWARD uses the programmed quantized Q exactly as before;
2. when the first reverse phase begins, draw one reciprocal drifted reverse operator at the configured drift RMS;
3. cache that complete drifted operator;
4. REVERSE_PLUS and REVERSE_MINUS both use that **identical cached operator**;
5. discard the cached realization at the next `CREDIT_CLEAR` / next complete physical gradient measurement.

Thus the spatial drift pattern may be large and may change between independent measurements/iterations, but its contribution is common across the local PLUS/MINUS energy subtraction.

No other emulator semantic changes.

## Fixed challenge point

Use the same difficult v0.7 50% damage context but restore the originally proposed differential-drift magnitude:

- Q/DAC/ADC = 8/8/8;
- leakage = 0.0005/tick;
- leakage CV = 0.50;
- mirror error = 0.15;
- reverse-operator drift RMS magnitude = **0.002 = 0.2%**;
- zero-mean credit noise = 0.25;
- credit offset = 0.00015;
- state noise = 5e-9 FS;
- static sense PGA.

The only difference from the killed independent-drift challenge is that the 0.2% reverse-operator realization is shared by PLUS and MINUS.

## Stage A — development positive control

Use only already-spent seeds:

`970,971,972,973,974,975,976,977,978,979`.

Compare:

- independent PLUS/MINUS drift, existing v0.5 interpreter;
- common-realization PLUS/MINUS drift, new paired interpreter.

No parameter sweep.

The common-realization mechanism survives development only if it satisfies the existing final ten-seed predicate:

1. every exact learner has DeltaC > 0;
2. at least 8/10 have DeltaC >=0.10;
3. median DeltaC >=0.15;
4. exact final contrast beats shuffled final in at least 8/10;
5. median placement gap >=0.10;
6. all values finite.

## Stage B — fresh confirmation

Only if Stage A common-realization passes.

Frozen untouched seeds:

`990,991,992,993,994,995,996,997,998,999`.

Run the exact same common-realization 0.2% challenge point once. No fallback and no threshold change.

## Decision

If Stage B passes, the emulator earns the statement:

> 0.2% quasi-static reverse-operator variation is tolerable when PLUS and MINUS share the same operator realization; the severe ppm requirement is specifically a requirement on **differential mismatch between phase states**, not absolute operator drift.

This would motivate a hardware phase-chopping/simultaneous-differential architecture.

If Stage A or B fails, common-mode freezing alone is insufficient and the next estimator must explicitly calibrate or encode the differential term.
