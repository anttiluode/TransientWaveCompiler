# TW-1A C0e circuit-native edge kT/C sweep — frozen diagnostic plan

Status: **diagnostic only** on already-spent C0d bodies 1700–1709.

The previous abstract full-node state-noise sweep was intentionally rejected as
a direct capacitor-sizing model.  This sweep replaces it with noise at the
physical switched-cap edge primitive.

## Frozen physical background

Use the qualified C0d machine:

```text
v0.5 phase-symmetric A/B reuse
4+3 segmented edge magnitude array
3% unit-cap sigma independently per physical edge
measured per-edge codebooks
all existing calibration / charge / credit / converter errors retained
```

The legacy independent state noise is forced to

```text
state_noise_std = 0.
```

## Circuit-native noise law

For selected fabricated edge capacitance ratio

```text
alpha = Cedge / Cstate,
```

define

```text
b = sqrt(kT/Cstate) / VFS_state.
```

One endpoint's sampled-edge thermal packet is modeled as

```text
sigma_edge / VFS_state = b * sqrt(alpha) / (1 + 2*alpha).
```

Each physical edge use draws one scalar packet and injects it

```text
+eta at endpoint i
-eta at endpoint j.
```

Forward, reverse-A and reverse-B samples are independent.  Magnitude code zero
has `alpha=0` and therefore no edge sampling packet.

Self-path, -PREV and switch thermal noise are not included yet; this is the edge
sampling contribution only.

## Frozen sweep

```text
b = edge_ktc_base_fraction

0
1e-5
3e-5
1e-4
3e-4
1e-3
3e-3
1e-2
```

For every point run 1700–1709 with the same 30-step learner and shuffled-credit
control used by C0d.

## Diagnostic score

Report:

```text
count DeltaC >= +0.10
count final exact > shuffled
median DeltaC
median placement gap
minimum DeltaC
```

Call a point `all-body clean` when it happens to satisfy the already-frozen v0.5
predicate. This label is diagnostic shorthand only.

## kT/C translation

After the last all-body-clean point and first failure are observed, choose an
inward `b_target` and report

```text
Cstate = kT / (b_target * VFS_state)^2
```

at 300 K for candidate state full-scale voltages 0.2, 0.4 and 0.6 V.

Because the validated edge ratio remains

```text
Cunit/Cstate = 0.001,
```

also report the implied

```text
Cunit = 0.001 * Cstate
Cedge,max = 0.127 * Cstate.
```

These are thermal-noise lower-bound candidates only.  The final absolute scale
must also satisfy 3% unit-cap matching, parasitic and charge-injection limits.
