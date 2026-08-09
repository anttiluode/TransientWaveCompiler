# TW-1A forward-only SPSA clean calibration — result

Date: 2026-08-09

Status: **PASS on spent clean fabricated machine. Frozen thermal candidate selected: `c=1.0`, `step_size=0.40`.**

Preregistration: `docs/BENCHMARK_V10_FORWARD_SPSA_CLEAN_PREREG.md`

Workflow: `v10-forward-spsa-clean`, successful run `31329551570`.

## What was tested

Task/fabrication 2400, formal v0.9 static silicon, edge/drift switch residuals removed after construction, all three sampled thermal bases set to zero. No reverse lane and no credit circuit were executed.

Each SPSA optimizer update used only:

```text
C(theta + c Delta)
C(theta - c Delta)
```

where one contrast measurement is target + distractor forward objectives. Thus one optimizer update costs four forward wave traversals regardless of the 39 trainable edges.

Every condition ran 30 updates under three frozen Rademacher direction sequences, for:

```text
120 training forward traversals / run
0 reverse traversals / run
```

## Matrix summary

| c | step | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean-viable |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0.25 | 0.10 | 0/3 | 3/3 | +0.071044 | +0.066387 | +0.110139 | NO |
| 0.25 | 0.20 | 3/3 | 3/3 | +0.130140 | +0.117826 | +0.133352 | NO |
| 0.25 | 0.40 | 2/3 | 2/3 | +0.448474 | +0.092351 | +0.457183 | NO |
| 0.50 | 0.10 | 0/3 | 3/3 | +0.074670 | +0.072406 | +0.104385 | NO |
| 0.50 | 0.20 | 2/3 | 3/3 | +0.131785 | +0.095546 | +0.144548 | NO |
| 0.50 | 0.40 | 3/3 | 3/3 | +0.433205 | +0.241905 | +0.369100 | YES |
| 1.00 | 0.10 | 0/3 | 3/3 | +0.072957 | +0.070696 | +0.068129 | NO |
| 1.00 | 0.20 | 3/3 | 3/3 | +0.165192 | +0.130707 | +0.159476 | NO |
| 1.00 | 0.40 | 3/3 | 3/3 | **+0.446339** | **+0.374621** | **+0.394441** | **YES** |
| 2.00 | 0.10 | 0/3 | 3/3 | +0.072267 | +0.065961 | +0.099990 | NO |
| 2.00 | 0.20 | 3/3 | 3/3 | +0.170916 | +0.137988 | +0.141073 | NO |
| 2.00 | 0.40 | 3/3 | 3/3 | +0.377000 | +0.294773 | +0.290469 | YES |

The `c=0.25, step=0.40` cell illustrates why the preregistered multi-direction criterion mattered: its median is high, but one direction sequence stalls at `+0.09235` and loses shuffled placement, so it is not robust enough to select.

## Frozen selection

The preregistered selection order among clean-viable cells was:

1. highest median DeltaC;
2. then highest minimum DeltaC;
3. then smaller `c`;
4. then smaller step.

The selected point is therefore unambiguous:

```text
c = 1.0
step_size = 0.40
iterations = 30
```

It has:

```text
3/3 DeltaC >= +0.10
3/3 exact > shuffled
median DeltaC = +0.446339
minimum DeltaC = +0.374621
median placement gap = +0.394441
```

## Meaning

This changes the architectural diagnosis materially.

The trainable **forward** wave body is not dependent on the physical adjoint for learnability. A two-point scalar perturbation estimator can find useful parameter placement through the quantized fabricated body using only forward measurements.

The comparison is especially relevant because the original temporal-order benchmark has only 39 trainable tree edges. The forward-only update cost is independent of that count:

```text
4 forward traversals / optimizer update
```

versus the current physical-adjoint protocol's target/distractor forward+reverse machinery.

This is still only a clean spent-body result. It does **not** yet authorize deleting reverse hardware. The decisive test is whether the same frozen SPSA point survives the actual partitioned small-cap thermal body at `b=2e-5`.

If it does, the project should stop treating the stochastic physical adjoint as mandatory architecture and start costing a forward-only trainable filter body plus digital perturbation controller. If it fails, the next candidate is a structured multi-direction/orthogonal objective estimator, not another attempt to reverse independent thermal trajectories.
