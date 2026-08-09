# TW-1A circuit-native simultaneous corner result v0.1

The preregistered simultaneous corner in `CIRCUIT_NATIVE_CORNER_PREREG_V01.md` **FAILED** and is retained as a formal failure.

GitHub Actions artifact: `circuit-native-corner-v01`, workflow run 31302292122.

## Frozen criteria

Required:

- 10/10 placed learners `DeltaC >= +0.10`;
- 10/10 placed final contrast > shuffled final contrast;
- median `DeltaC >= +0.30`;
- median placement gap `>= +0.25`.

Observed:

```text
DeltaC >= +0.10        3/10
placed final > shuffled 5/10
median DeltaC          +0.007256
median placement gap   +0.003292
min DeltaC             -0.028521
min placement gap      -0.041459
```

Therefore this is not a near miss. The naïve Cartesian combination of one-axis inward values collapses useful learning on many bodies.

## Per-body result

```text
seed 1200  DeltaC +0.0061   gap +0.0084
seed 1201  DeltaC -0.0285   gap -0.0415
seed 1202  DeltaC +0.1685   gap +0.1595
seed 1203  DeltaC -0.0003   gap -0.0038
seed 1204  DeltaC -0.0159   gap -0.0315
seed 1205  DeltaC +0.1560   gap +0.2216
seed 1206  DeltaC -0.0254   gap -0.0159
seed 1207  DeltaC +0.0084   gap +0.0084
seed 1208  DeltaC +0.0236   gap -0.0018
seed 1209  DeltaC +0.2078   gap +0.2507
```

## What this does and does not kill

It does **not** undo the exact-gradient audit, the 5/5 quantized lockstep reference result, or the one-axis result showing that the old 10-ppm long-pass problem is structurally removed.

It **does** kill the claim that all inward one-axis values can simply be used together.

The present error budget is interaction-limited.

## Allowed follow-up

The frozen preregistration permits diagnosis on these now-spent bodies by removing one error or one error group at a time. Such diagnostics may identify interactions, but they do not establish a new safe corner.

Any revised simultaneous corner must be separately preregistered and run on new bodies.

The next diagnostic question is therefore:

> Which physical subgroup is responsible for the collapse: common operator mismatch, second-order/history error, A/B subphase imperfections, terminal copy, local credit storage/detection, or the older background leakage/noise/readout errors?
