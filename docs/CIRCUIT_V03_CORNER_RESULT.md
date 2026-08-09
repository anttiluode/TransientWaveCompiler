# TW-1A v0.3 simultaneous circuit corner result

The frozen experiment in `CIRCUIT_V03_CORNER_PREREG.md` **FAILED** and is retained.

Fresh bodies: 1300-1309. Artifact: `circuit-v03-corner`, workflow run 31302912140.

## Frozen criteria

Required all of:

- 10/10 `DeltaC >= +0.10`;
- 10/10 placed final > shuffled final;
- median `DeltaC >= +0.30`;
- median placement gap >= `+0.25`.

Observed:

```text
DeltaC >= +0.10          5/10
placed final > shuffled  7/10
median DeltaC            +0.08663
median placement gap     +0.07198
minimum DeltaC           -0.01093
minimum gap              -0.01137
```

The v0.3 corner is therefore a clear failure, not a threshold ambiguity.

## Per-body

```text
1300  DeltaC +0.0165   gap +0.0225
1301  DeltaC +0.7965   gap +0.7217
1302  DeltaC +0.1354   gap +0.2619
1303  DeltaC -0.0109   gap -0.0089
1304  DeltaC +0.2622   gap +0.3394
1305  DeltaC +0.2959   gap +0.1215
1306  DeltaC +0.4818   gap +0.4247
1307  DeltaC +0.0005   gap -0.0114
1308  DeltaC -0.0034   gap -0.0082
1309  DeltaC +0.0379   gap +0.0148
```

## Comparison with v0.2

The first v0.2 combined corner had:

```text
3/10 DeltaC >= +0.10
5/10 final wins
median DeltaC +0.0073
median gap    +0.0033
```

So charge balancing + self calibration materially improve the combined machine, but do not yet produce a robust corner.

The isolated v0.3 primitive results remain valid. This failure says the inward primitive values still interact badly when all are present together.

## Allowed follow-up

Bodies 1300-1309 are now spent and may be used for leave-one-group-out diagnosis. No diagnostic result on these bodies can qualify a revised corner.

Any v0.4/revised v0.3 simultaneous corner requires untouched bodies and a separately frozen configuration.