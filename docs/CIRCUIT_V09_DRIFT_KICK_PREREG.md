# TW-1A v0.9 drift-shear switch residual — preregistration

Date: 2026-08-09

Status: **diagnostic on spent bodies 2300..2309; no fresh seeds authorized.**

The full kick-drift thermal learner passed every preregistered unity-drift kT/C point through `b_drift=2e-5`. C1f, however, implements the shear through real sampling/transfer switches. This gate adds the missing post-cancellation switch-injection residual at the node-local drift interface.

## Frozen thermal/learning point

```text
edge b                    = 2e-5
kick-residual self b      = 2e-5
unity drift b             = 2e-5
kick residual range       = +/-0.125, 10 signed bits
all v0.8 fabrication, converter, leakage, LCC and credit settings unchanged
30 updates, step size 0.20
same sense PGA rule and same-credit shuffled control
```

## Residual model

Each physical node owns one drift-shear switch path reused by forward C and returned C/D contexts. After foreground cancellation/autozero, model two static residual packets:

```text
q_C = q_common + q_diff/2
q_D = q_common - q_diff/2
```

`q_common` is the node-local packet shared by every use of the physical drift shear. `q_diff` is the C/D context-selection residual. Forward uses `q_C`. The terminal inverse drift also uses `q_C` because it exercises the same C-side state path.

The residual is added after the Z shear, in the same place as drift sampling noise. Unit Gaussian spatial fields are generated from a dedicated seed stream and then scaled by the requested RMS, so every sweep point uses the same underlying static silicon.

This experiment sweeps **post-cancellation residual directly**. It does not yet assume a raw switch-kick amplitude or a cancellation measurement percentage. Those are mapped only after a residual target is known.

## Frozen sweeps

Common-only:

```text
q_common RMS / state FS = 0, 0.5, 1, 2, 3, 5, 10 ppm
q_diff = 0
```

Differential-only:

```text
q_diff RMS / state FS = 0, 0.5, 1, 2, 3, 5, 10 ppm
q_common = 0
```

A later pair point is allowed only after these independent boundaries are visible.

## Frozen predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

Fabrication must also retain all edge-codebook/headroom and kick-self-range checks from the full kick-drift gate.

## Interpretation

- If both 2 ppm common and 1 ppm differential are clean, the existing v0.8 edge-kick floor class is already a plausible first drift target.
- If common is loose but differential is tight, drift cancellation should prioritize C/D phase symmetry over absolute offset.
- If even sub-ppm common residual is required, the unity drift likely needs correlated cancellation, chopping, or a different state-transfer topology before fresh qualification.

No result from this spent-body sweep directly promotes v0.9.
