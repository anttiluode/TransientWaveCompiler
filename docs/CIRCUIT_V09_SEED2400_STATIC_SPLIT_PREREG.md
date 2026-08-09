# TW-1A v0.9 seed 2400 same-draw static split — preregistration

Date: 2026-08-09

Status: **diagnostic only on spent seed 2400.**

Fresh seed 2400 improved only +0.0252 at the formal v0.9 corner, while an ideal exact-credit control on the same task improved +0.8644. Removing all edge/self/drift thermal noise left seed 2400 weak (~+0.0478), so this experiment isolates static/support mixed-signal mechanisms.

## Anti-redraw rule

Every condition MUST first construct the exact formal v0.9 target/distractor/shuffled tiles with the same formal configuration and seeds. Static disorder is copied exactly as in the formal learner. Only **after construction** may the named block be surgically replaced. No condition is allowed to set a fabrication sigma to zero before tile construction, because doing so can change RNG consumption and redraw later blocks.

All conditions then set

```text
edge thermal b      = 0
kick-self thermal b = 0
drift thermal b     = 0
```

at runtime. The 5 ppm common + 5 ppm differential drift residual remains unless a condition explicitly removes it.

The sense PGA is frozen once from the unmodified formal config and reused in every condition.

## Conditions

```text
thermal_zero_baseline
no_drift_residual
no_inherited_edge_kick
no_state_leakage
exact_edge_lane_holds
exact_kick_self_gain
ideal_edge_codebook
ideal_converters
ideal_credit_path
all_support_clean
```

Surgical meanings:

- `no_drift_residual`: zero the already-drawn drift common/differential unit fields at use time.
- `no_inherited_edge_kick`: zero the already-drawn edge injection common/differential/A/B residual arrays.
- `no_state_leakage`: set measured retention to exactly one on every node.
- `exact_edge_lane_holds`: set C/D edge hold gains to exactly one while preserving the common edge codebook.
- `exact_kick_self_gain`: set the already-drawn self calibration/gain residual to unity; keep the 10-bit +/-0.125 quantizer.
- `ideal_edge_codebook`: replace only the fabricated unit/site codebook by the nominal monotonic 127-unit active-ratio codebook; keep every other static field from the formal draw.
- `ideal_converters`: after construction set drive DAC, returned-error DAC and sense ADC quantization to ideal (`None`); keep physical edge and kick-self coefficient quantizers.
- `ideal_credit_path`: set LCC curvature, credit accumulator leakage, credit offset and credit readout noise to zero after construction.
- `all_support_clean`: apply all eight surgeries above simultaneously, while retaining the exact kick-drift recurrence, physical trainable edge topology, 10-bit kick-self quantizer and the same 30-update protocol.

## Frozen readout

Report seed 2400:

```text
exact improvement
placement gap
final exact
final shuffled
```

No condition is declared a new passing corner from one seed. The purpose is only to identify which already-modeled physical block explains the gap between ideal-credit seed 2400 (+0.8644) and the mixed-signal body.

If no single surgery materially rescues 2400 but `all_support_clean` does, a preregistered pair split will follow among the strongest individual improvements. If even `all_support_clean` stays weak, inspect kick-drift coefficient quantization / update semantics rather than tightening circuit tolerances.
