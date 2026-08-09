# TW-1A v0.9 partitioned thermal-source factorial — preregistration

Date: 2026-08-09

Status: **diagnostic only; fixed task 2400 and fixed fabrication 2400.**

The full-thermal residual-boundary diagnostic showed that even zero edge/drift switch residual does not by itself close seed 2400 when all three `b=2e-5` thermal sources are active. Historical single-source removals are not sufficient to settle the interaction because the older harness let edge thermal and credit readout consume a shared RNG stream.

This experiment uses `transientwave/circuit_emulator_v09_partitioned_rng.py`, in which edge thermal, self thermal, drift thermal and credit readout have independent dynamic RNG streams.

## Fixed task and silicon

```text
task seed         = 2400
fabrication seed  = 2400
```

Task 2400 is strongly learnable under ideal physical credit (`DeltaC_ideal ~= +0.864382`). The exact formal v0.9 silicon is always constructed first.

After construction:

- zero all already-drawn inherited edge-switch residual arrays;
- set drift common/differential residual amplitudes to zero;
- keep all codebook, site-ratio, self-gain, leakage, converters, lane holds, LCC and credit-path nonidealities unchanged;
- freeze the task-static PGA selected from the unmodified formal configuration.

Thus this experiment isolates sampled thermal interactions, not switch residual interactions.

## Thermal factors

Each active source uses its formal v0.9 value

```text
b = 2e-5
```

and each inactive source uses zero. Test all eight combinations:

```text
none
edge
self
drift
edge+self
edge+drift
self+drift
edge+self+drift
```

## Dynamic replicates

For every thermal combination, reseed the partitioned dynamic streams with

```text
8000, 8001, 8002, 8003, 8004
```

while leaving static fabrication unchanged.

This yields 40 task-identical, fabrication-identical training runs whose only factors are thermal-source presence and dynamic-noise replicate.

## Frozen learning protocol/readout

```text
30 updates
step size 0.20
RMS-normalized update
same-credit fixed shuffled control
```

For each thermal combination report across five dynamic replicates:

```text
count DeltaC >= +0.10
count final exact > shuffled
median/min/max DeltaC
median placement gap
median hardware/ideal DeltaC ratio
```

## Interpretation frozen before results

- If one single-source condition is consistently weak, that sampled operation remains the dominant thermal target.
- If singles are strong but a particular pair is weak, optimize the pair's relative physical scale rather than shrinking every capacitor uniformly.
- If all pairs are strong and only the three-source combination is weak, the `b=2e-5` point is a distributed stochastic-margin problem rather than a single circuit bottleneck.
- If even `none` is broadly weak across dynamic replicates, the remaining static fabrication/support stack—not thermal noise—is limiting this silicon draw.

No fresh qualification follows directly from this diagnostic.
