# TW-1A hardware envelope — 50% combined-corner confirmation preregistration v0.7

Date frozen: 2026-08-09

## Motivation

v0.6 preregistered a 75% backoff from the v0.5 independent-recommendation vector. That 75% corner failed the final all-positive robustness condition on fresh seeds 952–961, despite strong median learning.

A development-only replay on those now-spent seeds tested fixed scales `0, 0.25, 0.50, 0.75`. The largest scale satisfying the unchanged final predicate was **0.50**; 0.75 reproduced the v0.6 failure.

That replay is not confirmatory evidence. v0.7 freezes the 50% corner before inspecting any new seed result and performs exactly one new confirmation.

## Frozen hardware/task contract

No emulator, benchmark, optimizer, quantizer, PGA, threshold, or learning-rule change from v0.6.

- rank-one reciprocal physical edge cells;
- zero-preserving signed mid-tread quantization;
- Q/DAC/ADC = **8/8/8**;
- static compiler-predicted sense PGA;
- internal state full scale +/-20 with clipping enabled;
- temporal-order AB-vs-BA contrast benchmark;
- 40 updates;
- host step size 0.20;
- RMS-normalized combined physical contrast credit;
- fixed norm-matched shuffled-credit permutation.

## Frozen simultaneous 50% corner

This is exactly one-half of the v0.6 full independent-recommendation vector:

- mean leakage rate: **0.0005 per tick**;
- leakage spatial CV: **0.50**;
- time-mirror gain error: **0.15 = 15%**;
- differential REVERSE_PLUS / REVERSE_MINUS drift: **0.00025 = 0.025% RMS**;
- zero-mean local credit readout noise: **0.25 = 25% of credit RMS**;
- systematic local credit offset fraction: **0.00015 = 0.015%**;
- analog state-noise fraction: **5e-9 of internal state full scale RMS per node per tick**.

With +/-20 internal state full scale, the state-noise term is **1e-7 state-unit RMS per node per tick**.

## Holdout seeds

The only confirmatory block is:

`970,971,972,973,974,975,976,977,978,979`.

These seeds must not be used for any parameter selection or threshold change before the run.

## Frozen final predicate

The 50% corner qualifies only if **all** of the following hold across all ten seeds:

1. every exact learner has `DeltaC_exact > 0`;
2. at least 8/10 have `DeltaC_exact >= 0.10`;
3. median `DeltaC_exact >= 0.15`;
4. exact final contrast beats shuffled final contrast in at least 8/10;
5. median `(DeltaC_exact - DeltaC_shuffle) >= 0.10`;
6. all contrasts, energies, gradients and parameters remain finite.

No fallback scale is permitted inside this experiment.

## Decision

If the frozen 50% corner passes, it becomes the first demonstrated simultaneous mixed-signal operating corner for the 8-bit TW-1A emulator on the temporal-order benchmark.

If it fails, no combined corner is claimed; v0.5/v0.6 independent bounds remain the only hardware tolerance results.
