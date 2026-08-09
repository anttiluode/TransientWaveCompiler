# TW-1A forward-only SPSA at small-cap thermal point — preregistration

Date: 2026-08-09

Status: **spent-body thermal diagnostic; frozen before outcomes. No fresh qualification.**

## Frozen hypothesis

The physical-adjoint failure at `b=2e-5` may be specific to stochastic trajectory replay rather than to the trainable forward wave body itself.

The clean SPSA calibration selected, before thermal outcomes:

```text
c = 1.0
step_size = 0.40
iterations = 30
```

with 3/3 clean direction sequences above `+0.10`, 3/3 beating shuffled placement, median `DeltaC=+0.446339` and minimum `+0.374621`.

This experiment restores the exact small-cap sampled thermal body while continuing to use **forward objectives only**. No reverse lane, error waveform, LCC credit detector or credit accumulator is executed.

## Frozen task / fabrication

```text
task seed          2400
fabrication seed   2400
PGA                 compiler-recommended
```

Construct exact formal v0.9 silicon first, then set inherited edge-switch and drift-switch residuals to zero after construction. This isolates the already-proven thermal failure without redrawing static silicon.

Restore:

```text
edge b       = 2e-5
kick-self b  = 2e-5
drift b      = 2e-5
```

All static codebook, ADC/DAC quantization, leakage, site-ratio, self calibration, LCC/static fabrication fields remain as constructed. Reverse credit-path noise is irrelevant because reverse is not executed.

## Frozen stochastic axes

Cross:

```text
dynamic seeds   = 8000, 8001, 8002, 8003, 8004
SPSA directions = 9100, 9101, 9102
```

for 15 total runs.

For each run, target and distractor partitioned dynamic streams are independently reseeded from the named dynamic seed using the existing role-offset convention. The `+` and `-` perturbation evaluations consume the streams naturally in sequence. **No common-random-number or shared-noise pairing is used.**

## Frozen optimizer

For each of 30 updates:

1. draw one Rademacher direction `Delta`;
2. program `theta + 1.0*Delta` and measure noisy target+distractor forward contrast `C_plus`;
3. program `theta - 1.0*Delta` and measure a new independently noisy target+distractor forward contrast `C_minus`;
4. form `g_hat=(C_plus-C_minus)/2 * Delta`;
5. restore current theta and apply the same RMS-normalized `step_size=0.40` update semantics used by the clean calibration;
6. apply the same estimate with the frozen parameter permutation to the shuffled-placement control.

Thus training cost remains:

```text
4 noisy forward traversals / update
120 noisy forward traversals / 30-update run
0 reverse traversals
```

Deterministic evaluation traversals used to record learning curves are diagnostic overhead and excluded from the training traversal count.

## Frozen readouts

Across all 15 runs report:

```text
count DeltaC >= +0.10
count exact > shuffled
median/min/max DeltaC
median/min placement gap
```

Also report per-dynamic-seed 3-direction counts and per-direction-seed 5-dynamic counts so one lucky stochastic axis cannot hide a systematic failure.

Call the point **thermal-forward-viable** only if all hold:

```text
>= 12/15 DeltaC >= +0.10
>= 12/15 exact > shuffled
median DeltaC >= +0.20
median placement gap >= +0.15
every dynamic seed has >= 2/3 DeltaC >= +0.10
```

Call it a **strong pass** only if all 15 runs clear both `+0.10` and shuffled placement and median `DeltaC >= +0.30`.

## Frozen decision

- **Strong pass:** immediately test the same SPSA point with formal forward switch residuals restored, then do a factored task × fabrication × dynamic fresh protocol. Begin a hardware deletion/cost model for reverse credit circuitry.
- **Thermal-forward-viable but not strong:** preserve SPSA as the leading architecture, diagnose only the failed stochastic axis, and test a small forward-objective replication/structured-direction improvement before fresh seeds.
- **Not thermal-forward-viable:** do not tune SPSA post hoc on this noise realization. Next test a structured orthogonal/Hadamard finite-difference estimator on the same spent body, exploiting the small 39-parameter task, or abandon small-cap on-device training.

The historical v0.9 physical-adjoint gate remains red regardless of this result. A forward-only success would define a different training architecture, not retroactively rescue the adjoint.
