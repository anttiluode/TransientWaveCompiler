# TW-1A full-update coherent drift — preregistration v0.1

Date frozen: 2026-08-09

## Motivation

Independent 0.2% reverse-pass drift fails badly. Sharing one drift realization only between REVERSE_PLUS and REVERSE_MINUS greatly improves learning but still fails the registered robustness tail.

For the temporal-order objective,

`C(Q) = [E_AB(Q)-E_BA(Q)]/[E_AB(Q)+E_BA(Q)]`,

an exact gradient requires `E_AB`, `dE_AB/dQ`, `E_BA`, and `dE_BA/dQ` to refer to the **same physical Q**. A physical gradient measurement also requires the forward/retraced and returned fields to evolve under one reciprocal operator realization during that gradient evaluation.

This experiment therefore tests the mathematically coherent quasi-static limit: one drifted Q realization is frozen across the entire AB+BA contrast-gradient update and may change only between optimizer updates.

## Coherent-cycle semantics

At the start of each optimizer iteration:

1. form the current zero-preserving quantized rank-one edge-cell Q;
2. draw one reciprocal spatial drift realization with RMS magnitude `0.002 = 0.2%`, using the same per-cell/per-edge multiplicative model as the v0.5 drift model;
3. freeze the resulting Q for the complete gradient evaluation;
4. run AB FORWARD, REVERSE_PLUS and REVERSE_MINUS under that Q;
5. run BA FORWARD, REVERSE_PLUS and REVERSE_MINUS under the **same Q**;
6. form the normalized contrast gradient and apply one host update;
7. discard the drift realization.

A new independent 0.2% drifted Q is drawn for the next optimizer iteration.

Deterministic benchmark evaluation between updates remains on the programmed nominal quantized Q, exactly as in prior envelope experiments.

This is a positive control for a hardware timing requirement: the programmable wave operator must be quasi-static over one complete physical gradient evaluation, not ppm-identical across arbitrarily separated passes.

## Fixed challenge point

Use the same v0.7 50% context:

- Q/DAC/ADC = 8/8/8;
- leakage = 0.0005/tick;
- leakage CV = 0.50;
- mirror error = 0.15;
- coherent operator-drift magnitude = **0.002 RMS = 0.2%**;
- zero-mean local credit noise = 0.25;
- credit offset = 0.00015;
- state noise = 5e-9 FS;
- static sense PGA.

No repeated averaging is used: one AB physical gradient plus one BA physical gradient per optimizer update, the original eight traversal cost.

## Stage A — mechanism test on spent seeds

Use only already-spent seeds:

`970,971,972,973,974,975,976,977,978,979`.

The mechanism survives only if the existing final ten-seed predicate passes:

1. every exact learner has DeltaC >0;
2. at least 8/10 have DeltaC >=0.10;
3. median DeltaC >=0.15;
4. exact final contrast beats shuffled final in at least 8/10;
5. median placement gap >=0.10;
6. all values finite.

## Stage B — fresh confirmation

Only if Stage A passes, release the still-untouched seeds:

`990,991,992,993,994,995,996,997,998,999`.

Run the exact same 0.2% full-update-coherent challenge once. No fallback and no parameter change.

## Decision

PASS on fresh seeds earns the statement:

> TW-1A tolerates 0.2% quasi-static spatial operator variation in this benchmark when the operator is coherent across the entire AB+BA physical gradient evaluation; the severe ppm limit is a **within-gradient differential stability** requirement, not an absolute fabrication-accuracy requirement.

FAIL means even full gradient-cycle coherence is insufficient and explicit drift calibration/estimator redesign is required.
