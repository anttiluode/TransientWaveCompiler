# TW-1A full-basis forward Hadamard estimator at the small-cap thermal point — result

Date: 2026-08-09

Status: **FAIL under the frozen thermal-Hadamard viability rule. Full-basis forward measurement improves robustness over one-direction SPSA, but not enough to justify the 256-forward/update tax.**

Preregistration: `docs/BENCHMARK_V10_FORWARD_HADAMARD_THERMAL_PREREG.md`

Workflow: `v10-forward-hadamard-thermal`, successful run `31329887445`.

## Structural clean control

The exact same 64-direction least-squares estimator was first run with sampled thermal bases set to zero on task/fabrication 2400.

Result:

```text
DeltaC                 +0.839012
placement gap          +0.937920
exact > shuffled       yes
minimum rank           39
maximum condition      2.0
training forwards      7680
reverse traversals     0
```

The implementation control therefore passes strongly. The estimator is capable of reconstructing and applying a useful 39-coordinate gradient through the quantized fabricated body. Bound clipping begins later in training, but the actual-perturbation least-squares matrix remains full rank and well conditioned.

## Thermal results

The physical point restores independent sampled edge/self/drift thermal bases at `b=2e-5`, with edge/drift switch residuals zero after construction.

| dynamic seed | DeltaC | placement gap | exact > shuffled | min rank | max condition |
|---:|---:|---:|:---:|---:|---:|
| 8000 | +0.224427 | +0.329490 | yes | 39 | 1.000 |
| 8001 | +0.068228 | +0.076544 | yes | 39 | 1.000 |
| 8002 | +0.052876 | +0.091951 | yes | 39 | 1.000 |
| 8003 | +0.099247 | +0.208114 | yes | 39 | 1.293 |
| 8004 | +0.112817 | +0.269590 | yes | 39 | 1.000 |

Aggregate:

```text
DeltaC >= +0.10       2/5
exact > shuffled      5/5
median DeltaC        +0.099247
minimum DeltaC       +0.052876
maximum DeltaC       +0.224427
median placement gap +0.208114
minimum placement gap +0.076544
minimum rank          39
```

Every run improves and every run beats shuffled placement. That is substantially cleaner than one-direction thermal SPSA, whose 15-run median DeltaC was only `+0.045210` and which lost shuffled placement on 4/15 runs.

However the preregistered viability rule required:

```text
5/5 DeltaC >= +0.10
5/5 exact > shuffled
median DeltaC >= +0.30
median placement gap >= +0.20
minimum rank = 39
```

Only the shuffled-placement, median-gap, and rank clauses pass. The absolute learning-margin clauses fail badly.

## Acquisition cost

The full structured estimator requires:

```text
64 Hadamard directions
4 forward traversals / direction
256 forward traversals / optimizer update
7680 forward traversals / 30-update run
0 reverse traversals
```

This is not a small detail. The estimator buys a cleaner direction by replacing reverse-adjoint complexity with brute-force forward measurement. At the tested thermal point it still does not achieve the frozen learning margin.

## Frozen decision

The preregistration explicitly forbids increasing the direction count or averaging each direction after a failure. Therefore:

```text
BRUTE-FORCE FORWARD FINITE-DIFFERENCE TRAINING AT b=2e-5:
NOT ACCEPTED AS THE PRIMARY ON-DEVICE TRAINING ARCHITECTURE
```

No 128-direction, repeated-Hadamard, or post-outcome perturbation tuning is authorized on this spent body.

## What survives

Several things remain real and useful:

1. The deterministic/low-noise forward wave body is highly trainable. Full-basis clean finite differences reach `DeltaC=+0.839`.
2. Even at the small-cap thermal point, all five Hadamard runs improve and beat shuffled placement. The objective landscape is not destroyed; measurement SNR is the limiter.
3. The stochastic physical adjoint has an additional trajectory-replay problem and is therefore worse conceptually than forward-only measurement under independent process noise.
4. Forward-only optimization can be moved **off chip** or performed during slower calibration/tuning without requiring reverse C/D lanes or a T-long stochastic replay tape.

## Architectural conclusion

The evidence now separates the project into two objects:

### A. The wave body / compiler

Still strong. It compiles a sparse symmetric second-order operator into reciprocal edge cells and produces measurable transient objectives. It can be tuned when a sufficiently accurate external or slow measurement loop is available.

### B. The small-cap on-device gradient learner

Not supported at the present `b=2e-5` physical point. Three independent rescue classes have now failed under controlled partitioned noise:

```text
larger common capacitance       -> economically killed before robustness
repeat complete physical adjoint -> fails through 64x repetition
forward SPSA                    -> fails thermal viability
full 64-direction Hadamard      -> better, but still fails at 256 forwards/update
```

The next project move should therefore stop treating on-device gradient training as the destination. Preserve the adjoint and forward-only estimators as research results, but redirect hardware/compiler validation toward **externally tuned coupled-resonator / wave-filter problems**, where the same symmetric sparse second-order formalism is already the native design language and slow accurate tuning is acceptable.
