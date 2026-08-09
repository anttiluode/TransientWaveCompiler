# TW-1A v0.9 seed 2400 switch-interaction residual sweep — preregistration

Date: 2026-08-09

Status: **diagnostic only on spent seed 2400.**

The same-draw pair split identified one unique rescuing pair:

```text
all-thermal-zero baseline                 DeltaC +0.047842
remove inherited edge switch residual     DeltaC +0.093745
remove drift switch residual              DeltaC +0.081666
remove both                               DeltaC +0.706913
```

All other tested pairs among edge codebook, kick-self calibration and the two switch residual blocks remained below +0.10. This experiment converts the zero/one diagnosis into a quantitative simultaneous residual target.

## Anti-redraw rule

Construct the exact formal seed-2400 v0.9 silicon first, copy static disorder exactly as in the formal learner, freeze PGA=32, then disable edge/kick-self/drift thermal sources at runtime. Do not change any fabrication sigma before construction.

The already-drawn inherited edge residual arrays are scaled in place:

```text
edge_injection_common *= s
edge_injection_diff   *= s
edge_injection_A      *= s
edge_injection_B      *= s
```

The already-drawn drift unit fields remain unchanged while their formal amplitudes are scaled:

```text
q_drift_common RMS = s * 5 ppm state FS
q_drift_diff RMS   = s * 5 ppm state FS.
```

Thus each point is the same silicon and the same spatial residual pattern; only simultaneous post-cancellation residual amplitude changes.

## Frozen scale ladder

```text
s = 1.00, 0.75, 0.50, 0.25, 0.10, 0.00
```

No edge codebook, self gain, leakage, converters, lane holds or credit-path settings are changed.

## Readout

For each scale report:

```text
exact improvement
placement gap
final exact > shuffled
edge A/B residual RMS as fraction of state FS
drift C/D residual RMS as fraction of state FS
```

## Decision frozen before results

- The largest `s` giving seed-2400 improvement >= +0.10 and exact > shuffled is the **diagnostic simultaneous residual boundary point** on this body.
- Do not qualify on that cliff. If a clean boundary appears, choose the next tested point inward (smaller `s`) as the candidate reference and then replay the complete spent 2400..2409 cohort with thermal restored before any new fresh qualification.
- If even `s=0.10` stays weak while `s=0` is strong, switch residuals must be treated structurally rather than as a simple calibration tolerance.
