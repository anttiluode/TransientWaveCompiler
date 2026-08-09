# TW-1A v0.9 full kick-drift thermal diagnostic — preregistration

Date: 2026-08-09

Status: **diagnostic on spent bodies 2300..2309; no fresh seeds authorized.**

C1f established deterministic two-bank shears, and the trained range audit found
`max |P| = 0.003234` of the existing state full scale. This experiment now
executes the complete physical learner in exact kick-drift coordinates rather
than approximating the inertial term as a noisy gain-2 block.

## State representation

The same two vectors per context are reinterpreted as

```text
Z = z[n]
P = z[n] - z[n-1]
K = Q - 2 I
```

with one tick

```text
P <- P + K*Z + source
Z <- Z + P.
```

The reciprocal edge coefficients are unchanged. Only the node-local self term
is shifted by `-2` and represented by a provisional 10-bit signed residual bank
with physical range `+/-0.125`.

## Reverse boundary

The existing v0.8 common/difference echo maps exactly to

```text
C_Z <- Z - P
C_P <- -P
D_Z <- error_T
D_P <- error_T.
```

The `C_Z <- Z-P` inverse-drift operation pays one sample of the same unity-drift
noise model used by ordinary `Z <- Z+P` ticks. `P <- -P` is a differential
polarity reinterpretation and adds no independent magnitude error in this gate.

## Frozen physical background

Use spent task/fabrication seeds `2300..2309` and retain the v0.8 qualified
background:

```text
edge nominal positive range              0.265
unit-cap mismatch                         3% RMS
site-common Cunit/Cstate mismatch         1% RMS
kick-cancellation measurement error       0.5% RMS
kick residual floors                      2 ppm common / 1 ppm differential
converter/leakage/LCC/credit settings     unchanged
30 parameter updates, step size 0.20
same task-specific sense PGA
same same-credit shuffled control
```

The already-earned edge thermal margin is used:

```text
edge b                 = 2e-5
kick-residual self b   = 2e-5
```

Residual-self kT/C enters the P kick with

```text
sigma_Kself/VFS = b_self * sqrt(|K_self|).
```

## Unity-drift thermal sweep

A full-size sampled unity drift would have normalized kT/C base equal to its
own `b_drift`. Sweep

```text
b_drift = 0,
          2.5e-6,
          5e-6,
          7.5e-6,
          1e-5,
          1.5e-5,
          2e-5.
```

A dedicated deterministic RNG stream is used so changing only `b_drift` scales
the same underlying Gaussian samples and cannot redraw static silicon or other
noise streams.

The first gate includes thermal noise on the unity drift transfer and the one
terminal inverse drift. It does **not** yet add a new drift-specific switch-kick
model; C1f proved only deterministic topology. If the thermal gate is useful,
drift switch injection becomes the next circuit residual.

## Frozen predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

Additionally every physical tile must retain all 112 valid monotonic edge
codebooks, >=0.250 edge headroom, and no residual-self saturation.

## Interpretation

- `b_drift=0` must pass. Otherwise the kick-drift emulator/quantization split is rejected.
- If `b_drift=2e-5` passes, a same-scale drift sample is compatible with the fourfold smaller kT/C-capacitance corner.
- If a smaller nonzero point passes, the drift sampling capacitor can be oversized independently instead of forcing edge/state resources back to `b=1e-5`.
- If no nonzero point passes, C1f remains an algebra/deterministic circuit curiosity and the present sampled unity drift is not an economic solution.

No result from this spent-body diagnostic directly authorizes fresh qualification.
