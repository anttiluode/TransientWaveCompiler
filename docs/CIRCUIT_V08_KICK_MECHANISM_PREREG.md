# TW-1A v0.8 switch-kick mechanism split

Status: **diagnostic only; seeds 2100--2109 are spent**.

The frozen total-residual sweep established a learning boundary at 0.50 of the
failed formal kick residual and selected the already-tested 0.25 point as the
inward circuit target. The present emulator constructs the residual from two
physically distinct contributions:

```text
cancellation residual = raw_packet - measured_cancellation_packet
independent floor     = final_residual - cancellation residual
```

The formal parameters correspond to 2% RMS cancellation-measurement error plus
independent residual floors of 2 ppm common and 1 ppm differential state FS.
This experiment determines which contribution must actually be improved.

## Same-silicon rule

Construct the exact formal v0.8 physical tile first. Recover the already-drawn
per-edge components algebraically from the tile arrays:

```text
cancel_common = edge_injection_raw_common - edge_injection_common_measured
floor_common  = edge_injection_common - cancel_common
cancel_diff   = edge_injection_raw_diff - edge_injection_diff_measured
floor_diff    = edge_injection_diff - cancel_diff
```

Then rebuild only the final residual packet as

```text
residual = s_cancel * cancel + s_floor * floor.
```

No raw packet, measurement draw, floor draw, codebook or unrelated analog block
is redrawn. The formal thermal point `b=1e-5` remains enabled.

## Frozen conditions

```text
formal                 s_cancel=1.00  s_floor=1.00
cancel_x0p50           s_cancel=0.50  s_floor=1.00
cancel_x0p25           s_cancel=0.25  s_floor=1.00
cancel_x0p10           s_cancel=0.10  s_floor=1.00
floor_x0p50            s_cancel=1.00  s_floor=0.50
floor_x0p25            s_cancel=1.00  s_floor=0.25
floor_x0p10            s_cancel=1.00  s_floor=0.10
both_x0p50             s_cancel=0.50  s_floor=0.50
both_x0p25             s_cancel=0.25  s_floor=0.25
```

No additional scale is introduced after observing the result.

## Readout

For each condition report the unchanged formal learning predicate and seed 2107,
plus mean/max RMS fractions for the cancellation component, floor component and
reconstructed total common/differential residual.

## Decision

If reducing cancellation error alone reaches the formal predicate, prioritize
foreground cancellation accuracy / repeated measurement. If reducing the floor
alone reaches it, prioritize switch/layout symmetry and dummy cancellation. If
only a joint condition passes, both become first-chip requirements. The final
fresh v0.8 operating point must remain inward of the total-residual 0.50
boundary and cannot be relaxed by this diagnostic.
