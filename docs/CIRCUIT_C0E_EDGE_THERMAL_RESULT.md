# TW-1A C0e circuit-native edge kT/C sweep — result

Status: **diagnostic** on already-spent C0d bodies 1700–1709.

This sweep replaced the old independent full-node noise stress term with thermal
noise at the physical sampled edge capacitor.  Each active physical edge use
draws one scalar packet and injects it equal/opposite into its two endpoint state
nodes.  Magnitude code zero injects no edge-sampling packet.

The normalized base parameter is

```text
b = sqrt(kT/Cstate) / VFS_state.
```

For a selected fabricated edge capacitance ratio

```text
alpha = Cedge/Cstate,
```

one endpoint's sampled edge-packet RMS is

```text
sigma_edge/VFS = b * sqrt(alpha)/(1 + 2*alpha).
```

## Frozen sweep result

| b | all-body clean | DeltaC>=0.10 | final wins | median DeltaC | median gap | min DeltaC |
|---:|:---:|---:|---:|---:|---:|---:|
| 0 | yes | 10 | 10 | +0.5704 | +0.5230 | +0.2612 |
| 1e-5 | yes | 10 | 10 | +0.5137 | +0.5185 | +0.2959 |
| 3e-5 | **yes** | 10 | 10 | +0.4739 | +0.4149 | +0.2312 |
| 1e-4 | no | 8 | 9 | +0.3003 | +0.1883 | +0.0168 |
| 3e-4 | no | 4 | 5 | +0.0425 | +0.0263 | -0.0455 |
| 1e-3 | no | 1 | 5 | +0.0157 | -0.0024 | -0.0951 |
| 3e-3 | no | 0 | 4 | +0.0134 | -0.0158 | -0.0788 |
| 1e-2 | no | 0 | 4 | +0.0099 | -0.0110 | -0.0921 |

The diagnostic boundary is therefore between

```text
b = 3e-5   last tested all-body-clean point
b = 1e-4   first tested failure
```

## Inward C0e thermal target

Use

```text
b_target <= 1e-5
```

for the first absolute-scale design pass.  This is one third of the largest
tested all-body-clean value and itself retained strong margin:

```text
10/10 DeltaC >= +0.10
10/10 final exact > shuffled
median DeltaC       +0.513738
median placement gap +0.518489
minimum DeltaC      +0.295878
```

At the largest physical edge code of the validated C0d ratio

```text
alpha_max = 127 * 0.001 = 0.127,
```

the per-edge endpoint packet is only

```text
sigma_edge,max/VFS
  = 1e-5 * sqrt(0.127)/(1+2*0.127)
  ~= 2.84e-6.
```

Thus the inward base target is consistent with the earlier observation that
few-ppm state disturbances are meaningful, while locating that noise at the
physical edge primitive rather than spraying it independently across every node.

## First thermal lower-bound capacitance scale

At 300 K,

```text
Cstate = kT / (b_target * VFS_state)^2
```

with `b_target=1e-5` gives:

| candidate state voltage full scale | Cstate | Cunit = 0.001 Cstate | Cedge,max = 0.127 Cstate |
|---:|---:|---:|---:|
| 0.2 V | 1.035 nF | 1.035 pF | 131.5 pF |
| 0.4 V | 258.9 pF | 258.9 fF | 32.88 pF |
| 0.6 V | 115.1 pF | 115.1 fF | 14.61 pF |

These are **thermal lower-bound candidates**, not chosen silicon sizes.

The last-clean diagnostic point `b=3e-5` would reduce all capacitances by a
factor of nine, e.g. at 0.4 V:

```text
Cstate    28.76 pF
Cunit     28.76 fF
Cedge,max 3.653 pF.
```

The inward `1e-5` choice intentionally keeps substantial learning margin while
leaving unit capacitors in a range where matching, parasitic and layout concerns
can plausibly dominate before thermal noise does.

## What this does and does not include

Included in the C0e diagnostic:

```text
3% independently mismatched segmented edge capacitor banks
measured per-edge codebooks
v0.5 phase-symmetric A/B reuse
edge/self/-PREV/clone calibration residuals
switch-charge autozero residuals
converter quantization
credit path noise/offset/curvature/leakage
edge-sampling thermal packets
```

Not yet included:

```text
self-MDAC sampling thermal noise
-PREV/history sampling thermal noise
state-bank reset/copy switch kT/C
correlated substrate/reference noise
MOS switch channel thermal noise beyond the sampled-edge kT/C abstraction
layout-correlated capacitor mismatch and extracted parasitics
noisy calibration measurement itself
```

## Next formal gate

The C0e boundary was measured only on spent bodies.  The next formal gate must use
untouched bodies and replace the legacy independent node-noise term with the
circuit-native edge thermal model at the frozen inward target `b=1e-5`.

Only after that fresh gate passes should `b<=1e-5` be promoted from a diagnostic
sizing target to an emulator-qualified edge-thermal contract.
