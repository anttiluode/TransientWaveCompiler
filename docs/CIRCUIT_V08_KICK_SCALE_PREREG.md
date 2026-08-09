# TW-1A v0.8 switch-kick residual scale sweep

Status: **diagnostic only; seeds 2100--2109 are spent**.

The same-silicon diagnosis of the failed fresh v0.8 gate isolated one single
support block: zeroing residual edge switch-kick packets alone restored 10/10
with large margin and moved seed 2107 from `DeltaC=+0.035623` to about
`+0.292370`. Thermal, C/D hold mismatch, edge fabrication, converter precision,
retention and the other single-block removals did not rescue 2107.

This experiment is frozen before observing any partial-residual result.

## Same-silicon rule

For every seed, construct the exact formal v0.8 physical tile first, including
its raw switch packets, autozero measurement error, residual floor, thermal
point and all other disorder. Then multiply only the already-drawn residual
arrays by a scalar `s`. No RNG stream, raw packet, measured packet, codebook or
other block is redrawn.

The arrays scaled together are:

```text
edge_injection_common
edge_injection_diff
edge_injection_a
edge_injection_b
```

This is a **total residual budget** study. It does not yet distinguish whether
the required reduction should come from better foreground cancellation,
layout/common-centroid symmetry, dummy-switch cancellation or a lower residual
floor.

## Frozen scale points

```text
s = 1.00   # exact failed formal residual
    0.75
    0.50
    0.25
    0.10
    0.00   # diagnostic ideal already known to rescue, rerun for one table
```

No intermediate scale is added after results are observed.

The formal edge thermal point `b=1e-5` remains enabled.

## Readout

For each scale report:

- 10-body improvement/win/median/minimum summary;
- seed 2107 improvement and placement gap;
- RMS of the unscaled and scaled common/differential residual edge packets as
  fractions of state full scale, averaged across the ten physical tiles;
- maximum per-tile RMS residual fraction.

## Decision rule

The largest nonzero tested `s` satisfying the unchanged formal learning
predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

becomes the **diagnostic residual boundary**. A circuit-facing target must be
chosen inward from that boundary before any new fresh qualification seeds are
reserved.

If no nonzero scale passes, the residual mechanism requires architectural
cancellation rather than a tolerance target.
