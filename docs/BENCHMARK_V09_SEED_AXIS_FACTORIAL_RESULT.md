# TW-1A v0.9 separated task / fabrication / dynamic-noise factorial — result

Date: 2026-08-09

Status: **diagnostic FAIL; uniform `b=2e-5` lacks broad stochastic SNR margin and also shows a smaller fabrication interaction. No fresh qualification authorized.**

Preregistration: `docs/BENCHMARK_V09_SEED_AXIS_FACTORIAL_PREREG.md`

Workflow: `v09-seed-axis-factorial`, successful run `31328037441`.

## Frozen matrix

```text
task seed         2400 only
ideal DeltaC      +0.864382
fabrication       2400, 3000, 3001, 3002, 3003
dynamic seeds     8000..8004
edge b             2e-5
kick-self b        2e-5
drift b            2e-5
formal v0.9 switch/converter/leakage/credit point otherwise unchanged
```

This is 25 runs of the same highly ideal-learnable task. Static silicon and dynamic stochastic trajectories are independent axes.

## Fabrication summaries

| fabrication | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | maximum DeltaC | median HW/ideal |
|---:|---:|---:|---:|---:|---:|---:|
| 2400 | 0/5 | 4/5 | +0.026145 | +0.002823 | +0.033482 | 0.0302 |
| 3000 | 0/5 | 4/5 | +0.048474 | +0.011113 | +0.068734 | 0.0561 |
| 3001 | 0/5 | 0/5 | -0.011444 | -0.025807 | +0.026234 | -0.0132 |
| 3002 | 0/5 | 4/5 | +0.022536 | +0.000110 | +0.029691 | 0.0261 |
| 3003 | 1/5 | 4/5 | +0.070959 | +0.005358 | +0.112508 | 0.0821 |

Across all 25 cells:

```text
DeltaC >= +0.10       1/25
exact > shuffled      16/25
```

The result is not compatible with “one unlucky fresh body.” Four of five independent fabrication draws never produce a single +0.10 run, and the fifth produces only one.

## Dynamic-axis structure

Dynamic seed `8002` loses exact-over-shuffled placement on **all five** fabrication seeds. That cross-fabrication repeat is direct evidence that the dynamic trajectory itself can dominate the learner outcome at this operating point.

Fabrication `3001` is also consistently pathological: it loses exact-over-shuffled on all five dynamic seeds and has negative median improvement. Therefore the diagnosis is not “dynamic noise only.” There is a secondary static-silicon interaction/yield axis that becomes visible once the stochastic margin is poor.

## Preregistered interpretation

The frozen interpretation is:

```text
current v0.9 operating point lacks stochastic SNR margin
```

with an additional fabrication interaction.

The historical fresh 2400..2409 gate remains red. This diagnostic explains why a single task=fabrication=dynamic seed cohort was not a reliable qualification protocol, but it does not rescue the hardware point: task 2400 is strongly ideal-learnable and the factored hardware succeeds only 1/25 times under the old absolute +0.10 criterion.

## Consequences

1. Future qualification must factor **task**, **fabrication**, and **dynamic replicate** rather than binding all three to one integer seed.
2. Task qualification must also respect the already-demonstrated ideal task ceiling: seed 2405 cannot be required to exceed +0.10 when ideal physical credit itself reaches only about +0.0529.
3. Neither protocol correction changes the hardware diagnosis at `b=2e-5`; task 2400 is not a benchmark-tail case and the factored machine is still broadly weak.
4. The next physical work should therefore improve or trade thermal margin before spending new formal seeds.

## Relationship to the thermal-source factorial

`docs/BENCHMARK_V09_THERMAL_FACTORIAL_RESULT.md` holds task 2400 and fabrication 2400 fixed, removes switch residuals entirely, and factors the three thermal sources. Its strong all-off control and weak edge/drift single-source points show that the broad seed-axis failure is primarily a dynamic sampled-noise problem, not merely a defective fabrication draw.
