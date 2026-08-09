# TW-1A forward-only SPSA clean calibration — preregistration

Date: 2026-08-09

Status: **spent-body algorithm calibration only; no fresh qualification. Frozen before outcomes.**

## Why this exists

The v0.9 partitioned diagnostics showed that the deterministic kick-drift body is strong but the tape-free stochastic physical adjoint has extreme gradient variance and a mixed bias component. Ordinary capacitor enlargement and up to 64 complete physical-adjoint averages per optimizer update were both rejected as primary rescue paths.

This experiment asks whether the **forward body itself** can be trained without reverse trajectory replay.

The candidate is simultaneous perturbation stochastic approximation (SPSA). One parameter direction perturbs all trainable edge parameters at once. The machine measures only the scalar target-vs-distractor contrast at `theta+c*Delta` and `theta-c*Delta` and forms

```text
g_hat = (C_plus - C_minus) / (2 c) * Delta
```

for Rademacher `Delta_i in {-1,+1}`.

For the temporal-order benchmark there are 39 trainable tree edges, but a two-point SPSA update still needs only:

```text
2 parameter points * (target + distractor) = 4 forward wave traversals
```

and **zero reverse traversals**.

This first experiment is deliberately clean. It establishes whether quantization/nonlinearity permit SPSA learning at all before thermal noise is restored.

## Frozen task / silicon

```text
task seed          2400
fabrication seed   2400
PGA                 compiler-recommended
edge switch residual zero after construction
drift switch residual zero after construction
edge b              0
kick-self b         0
drift b             0
```

Keep all static codebook, converter, leakage, site-ratio, self calibration, LCC and fabricated mismatch effects from formal v0.9. Credit-path noise is irrelevant because no reverse/credit circuit is executed.

## Frozen SPSA matrix

All 39 trainable parameters have source-space bounds 2..18 on this benchmark. Use one absolute perturbation magnitude for every coordinate:

```text
c in {0.25, 0.5, 1.0, 2.0}
```

and the same RMS-normalized host update semantics used by the adjoint learner:

```text
step_size in {0.10, 0.20, 0.40}
```

Run 30 optimizer updates for each `(c, step_size)` condition under three frozen Rademacher direction sequences:

```text
direction seeds = 9100, 9101, 9102
```

At each perturbation, project `theta +/- c*Delta` to the declared parameter bounds. At the current task start (`theta=10` for every trainable stiffness), every preregistered perturbation is symmetric and interior.

Use exact forward-only physical objectives (`_run_forward(stochastic=False)` followed by the existing quadratic `_objective()`). Do **not** call `execute()` and do not run any reverse lane.

## Control

Maintain a shuffled-placement learner on the same fabricated silicon. It receives the same SPSA gradient estimate with the frozen parameter permutation used by prior benchmarks. It performs no extra objective measurements.

This preserves the old question: does the measured update vector help because its parameter placement is meaningful?

## Frozen readouts

For each `(c, step_size)` summarize the three direction seeds:

```text
count DeltaC >= +0.10
count final exact > shuffled
median/min/max DeltaC
median/min placement gap
median forward traversal count
```

A condition is called **clean-viable** only if all hold:

```text
3/3 DeltaC >= +0.10
3/3 exact > shuffled
median DeltaC >= +0.30
median placement gap >= +0.20
```

## Frozen selection rule

If one or more conditions are clean-viable, choose for the subsequent thermal SPSA experiment by this deterministic ordering:

1. highest median DeltaC;
2. then highest minimum DeltaC;
3. then smaller `c`;
4. then smaller `step_size`.

No post-outcome hyperparameter additions are allowed before the thermal test.

If no condition is clean-viable, SPSA is not yet justified as the thermal escape. Do not tune on fresh tasks; either test a structured orthogonal finite-difference estimator on the same spent body or abandon forward-only training for this task.

## Architectural accounting

This experiment tests an estimator, not a chip revision. If it succeeds, the potential hardware implication is large: reverse C/D state, error injection and local credit accumulation may no longer be required for training. That deletion is **not** claimed here; it becomes legitimate only if forward-only learning survives the real `b=2e-5` stochastic point.
