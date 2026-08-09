# TW-1A hardware envelope — 10-ppm differential-drift combined corner preregistration v0.8

Date frozen: 2026-08-09

## Basis

v0.7 showed that the 50% simultaneous corner failed on fresh seeds. A leave-one-damage-out diagnostic on those now-spent seeds identified differential REVERSE_PLUS / REVERSE_MINUS pass drift as the only single damage term whose removal restored the final predicate.

A further development-only ppm refinement, again using only those spent seeds, held every other 50% damage component fixed and found the following pass prefix:

`0, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5, 2e-5`

with first failure at `2.5e-5` RMS fractional differential drift.

The preregistered one-step-inward candidate from that spent-seed boundary is therefore **`1e-5` RMS differential drift**.

None of those development results count as confirmation. v0.8 freezes one exact corner before inspecting a new seed block.

## Frozen architecture/task

No change from v0.7:

- rank-one reciprocal edge-cell hardware;
- zero-preserving signed mid-tread quantizers;
- Q/DAC/ADC = 8/8/8;
- static compiler-predicted sense PGA;
- internal state full scale +/-20 with clipping;
- temporal-order AB-vs-BA contrast benchmark;
- 40 updates, step size 0.20;
- RMS-normalized physical contrast credit;
- fixed norm-matched shuffled-credit control.

## Frozen simultaneous corner

All v0.7 50% terms are retained except differential drift, which is tightened to the ppm-refinement candidate:

- mean leakage rate: **0.0005/tick**;
- leakage spatial CV: **0.50**;
- mirror error: **0.15 = 15%**;
- differential PLUS/MINUS drift: **`1e-5` RMS = 0.001% = 10 ppm**;
- zero-mean local credit noise: **0.25 = 25% of credit RMS**;
- credit DC offset: **0.00015 = 0.015%**;
- state noise: **`5e-9 FS`** = `1e-7` state-unit RMS per node/tick at +/-20 full scale.

## Holdout seeds

`980,981,982,983,984,985,986,987,988,989`

No fallback corner is permitted.

## Final predicate

The corner qualifies only if all conditions hold:

1. every exact learner has `DeltaC_exact > 0`;
2. at least 8/10 have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast beats shuffled final contrast in at least 8/10;
5. median placed-vs-shuffled improvement gap >= 0.10;
6. all values remain finite.

## Decision

PASS earns the first demonstrated simultaneous mixed-signal operating point for the v0.5 rank-one TW-1A emulator on this benchmark.

FAIL leaves only the independent one-axis boundaries demonstrated; the next engineering work must change the differential estimator rather than continue scalar fabrication backoff.
