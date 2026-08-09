# TW-1A v0.5 SPICE-handoff sweep — frozen diagnostic plan

Status: **diagnostic only**. Bodies 1500–1509 are already spent by the qualified
v0.5 formal corner. This sweep cannot create or extend a formal qualification.
Its purpose is to convert the successful phase-symmetric architecture into
useful SPICE design targets.

All conditions other than the swept variable remain exactly those of
`CIRCUIT_V05_CORNER_PREREG.md`.

## Axis A — residual A/B coefficient-hold mismatch

```text
edge_lane_match_std
0.001
0.003
0.010
0.030
0.100
```

Interpretation: fractional RMS mismatch between the two matched coefficient
holds after the common edge transfer has settled and been calibrated.

## Axis B — raw common pre-settle loss

```text
edge_common_settling_loss
0.10
0.20
0.30
0.40
0.50
```

Interpretation: raw common gain loss before A/B sampling. This loss is included
in the measured edge transfer map, so degradation should arise mainly from code
headroom/quantization rather than PLUS/MINUS incoherence.

## Diagnostic score

For each value report the same four statistics as the formal gate:

```text
count DeltaC >= +0.10
count final exact > shuffled
median DeltaC
median placement gap
```

For SPICE handoff, call a point `all-body clean` when it happens to satisfy the
formal v0.5 predicate on these spent bodies. This label is diagnostic shorthand
only, not a new qualification.

The useful output is the largest tested all-body-clean point and the first tested
failure point on each axis. An inward engineering target should be chosen below
the observed diagnostic boundary.
