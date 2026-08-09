# TW-1A C0e state-noise budget sweep — frozen diagnostic plan

Status: **diagnostic only**. Bodies 1700–1709 are already spent by the qualified
C0d per-edge mismatch gate. This sweep cannot create a new formal qualification.

## Question

How much independent per-tick state noise can the already-qualified v0.5 + C0d
machine tolerate before temporal-order learning loses its all-body margin?

This is needed before choosing absolute state capacitance. The earlier emulator
value `state_noise_std=5e-9` was deliberately tiny and was never a transistor
noise requirement.

## Frozen hardware background

Use exactly the qualified C0d configuration:

```text
4+3 segmented edge magnitude array
3% unit-cap sigma independently per edge
measured per-edge physical codebooks
all v0.5 calibration / phase-symmetry / charge / credit errors unchanged
```

Only `state_noise_std` changes.

## Frozen sweep

`state_noise_std` is the Gaussian RMS injected per node per state update as a
fraction of state full scale:

```text
0
1e-7
3e-7
1e-6
3e-6
1e-5
3e-5
1e-4
3e-4
1e-3
3e-3
1e-2
```

For each value run the same ten spent bodies 1700–1709, 30 iterations, step size
0.20 and the same shuffled-credit control.

## Diagnostic score

For every point report:

```text
count DeltaC >= +0.10
count final exact > shuffled
median DeltaC
median placement gap
minimum DeltaC
```

Call a point `all-body clean` when it happens to satisfy the already-frozen v0.5
formal predicate:

```text
10/10 DeltaC >= +0.10
10/10 exact final > shuffled
median DeltaC >= +0.30
median placement gap >= +0.25
```

This label is diagnostic shorthand only.

## Physical translation rule

After observing the boundary, choose an inward normalized noise target and
translate it with

```text
sigma_V ~= sqrt(k*T/Cstate)
noise_fraction = sigma_V / VFS_state
Cstate >= k*T / (noise_fraction * VFS_state)^2
```

as a **single-equivalent kT/C estimate**, not yet a complete node noise model.
Report candidate capacitances for several plausible state voltage full scales
rather than choosing a process-specific supply without evidence.
