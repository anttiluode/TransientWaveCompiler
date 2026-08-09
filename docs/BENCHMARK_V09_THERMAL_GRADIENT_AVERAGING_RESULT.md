# TW-1A v0.9 complete-gradient thermal averaging — result

Date: 2026-08-09

Status: **FAIL / KILL for ordinary complete-gradient averaging as the primary `b=2e-5` rescue.**

Preregistration: `docs/BENCHMARK_V09_THERMAL_GRADIENT_AVERAGING_PREREG.md`

Workflow: `v09-thermal-gradient-averaging`, successful run `31328886379`.

## Frozen point

```text
task seed          2400
fabrication seed   2400
dynamic seeds      8000..8004
edge b              2e-5
kick-self b         2e-5
drift b             2e-5
edge switch residual 0
drift switch residual 0
optimizer updates    30
```

For each optimizer update the experiment acquires `N` independent complete target+distractor physical gradients at fixed theta, averages the resulting gradient vectors, then applies one RMS-normalized update. The shuffled control receives the same averaged vector under the frozen permutation.

## Results

| complete physical gradients / update | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | maximum DeltaC | median gap | minimum gap | robust |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 0/5 | 3/5 | +0.028717 | -0.046686 | +0.066484 | +0.039150 | -0.067130 | NO |
| 4 | 0/5 | 4/5 | -0.006610 | -0.050615 | +0.070293 | +0.029063 | -0.046659 | NO |
| 16 | 1/5 | 4/5 | +0.080290 | -0.038520 | +0.115184 | +0.105919 | -0.070209 | NO |
| 64 | 2/5 | 4/5 | +0.095307 | -0.023338 | +0.150402 | +0.159717 | -0.037763 | NO |

`N=1` reproduces the partitioned all-thermal-on factorial exactly, validating that this experiment changes only the number of complete physical gradient acquisitions averaged before one update.

## Frozen decision

The preregistration states:

> If `N=64` is not robust, reject ordinary complete-gradient averaging as the primary rescue path at `b=2e-5`; do not extend the grid post hoc.

`N=64` is not robust. It reaches the absolute `+0.10` improvement threshold on only 2/5 dynamic replicates, loses exact-vs-shuffled placement on one replicate, and has median improvement only `+0.0953`.

Therefore:

```text
ORDINARY COMPLETE-GRADIENT AVERAGING: REJECTED AS PRIMARY RESCUE
```

No `N>64` continuation is authorized by this experiment.

## Cost meaning

The largest tested point pays approximately a `64x` physical-gradient acquisition cost per optimizer update while retaining the same small-cap body. This multiplies forward/reverse wave traversals, switching activity, sensing, error injection and credit accumulation even before fixed controller overhead.

The result therefore fails twice:

1. **performance:** it still does not meet the frozen robustness criterion;
2. **economics:** even if its median were accepted, 64 complete physical adjoints per update would erase the premise of a cheap local in-situ learner for fast adaptation.

## Why the response is not simple `1/sqrt(N)` recovery

`N=4` is actually worse than `N=1`, and `N=16/64` recover only slowly. The fixed-theta microscope in `docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_RESULT.md` explains why: at this operating point the physical gradient estimator has both enormous variance and a non-negligible bias component. The forward wave is thermally perturbed, and the reverse C/D echo receives new independent thermal packets rather than replaying the stochastic forward trajectory.

Averaging complete gradients reduces some variance, but it cannot automatically repair stochastic trajectory-replay mismatch or nonlinear contrast/credit bias.

## Architectural consequence

Together the controlled v0.9 results now reject both easy analog rescues:

```text
larger C only                    -> economically killed
repeat the same physical adjoint -> still fails at 64x acquisition cost
```

The deterministic kick-drift circuit/algebra remains a valid result. What is no longer supported is the claim that the present tape-free **stochastic physical adjoint learner** can operate economically at the small-cap thermal point.

The next authorized question is estimator-level rather than tolerance-level:

> Can the trainable forward wave body be optimized from noisy forward objectives without requiring reverse replay of the stochastic trajectory?

A forward-only perturbation estimator is a legitimate candidate because it samples the objective distribution directly rather than pretending an independently noisy reverse trajectory is the adjoint of a particular noisy forward realization. Any such experiment must count its forward-evaluation cost explicitly and must first establish deterministic/no-thermal learnability on spent tasks before spending fresh qualification seeds.
