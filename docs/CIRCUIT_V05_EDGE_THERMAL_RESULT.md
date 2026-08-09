# TW-1A v0.5 C0e edge-thermal formal gate — QUALIFIED

The preregistered gate on untouched bodies 1800–1809 **passes** both the frozen
fabrication-yield predicate and the frozen temporal-order learning predicate
with circuit-native sampled-edge kT/C noise at the inward C0e target.

## Frozen edge-thermal contract

The legacy independent full-node stress term was removed:

```text
state_noise_std = 0
```

and replaced by physical sampled-edge packets.  For selected edge ratio

```text
alpha = Cedge/Cstate
b     = sqrt(kT/Cstate)/VFS_state
```

one endpoint receives RMS

```text
sigma_edge/VFS = b * sqrt(alpha)/(1 + 2*alpha)
```

with one random scalar injected equal/opposite into the two physical edge
endpoints.  Forward, reverse-A and reverse-B samples are independent.  Code zero
has no sampled-edge thermal packet.

The formal value was

```text
b = 1e-5.
```

## Fabrication result

Each target tile again contained 112 independently fabricated 4+3 segmented
edge codebooks at 3% unit-cap mismatch:

```text
monotonic fabricated tiles    10/10
monotonic edge codebooks      112/112 on every tile
minimum observed code step    +7.195656e-4 coefficient units
```

No failed edge/tile was repaired, sorted, or replaced.

## Learning result

```text
qualified                 true
improvement >= +0.10      10/10
final exact wins           10/10
median improvement        +0.645397
median placement gap      +0.632325
minimum improvement       +0.330965
minimum placement gap     +0.283292
```

Per-body exact improvements:

```text
1800  +0.592876
1801  +0.757226
1802  +0.511993
1803  +0.681543
1804  +0.689888
1805  +0.675237
1806  +0.330965
1807  +1.025437
1808  +0.361857
1809  +0.615557
```

All ten exact learners finish above their same-credit shuffled controls.

## Physical sizing consequence

The spent-body C0e diagnostic found the last tested all-body-clean point at
`b=3e-5` and first failure at `1e-4`.  This fresh formal pass promotes the inward
value

```text
sqrt(kT/Cstate)/VFS_state <= 1e-5
```

from a diagnostic choice to an **emulator-qualified edge-sampling thermal
contract**, subject to the claim boundary below.

At 300 K the corresponding single-equivalent thermal lower-bound state
capacitances are:

| candidate state voltage FS | Cstate | Cunit=0.001 Cstate | Cedge,max=0.127 Cstate |
|---:|---:|---:|---:|
| 0.2 V | 1.035 nF | 1.035 pF | 131.5 pF |
| 0.4 V | 258.9 pF | 258.9 fF | 32.88 pF |
| 0.6 V | 115.1 pF | 115.1 fF | 14.61 pF |

These are not yet final capacitor values.  They are the state-cap lower bounds
that make the **edge-sampling** kT/C contribution satisfy the now-qualified
normalized contract.

## What is qualified simultaneously

The passing fresh gate contains:

```text
v0.5 phase-symmetric A/B edge reuse
3% independently mismatched 4+3 segmented cap banks on every edge
measured site-specific nonlinear codebooks
raw edge/self gain mismatch and calibration residuals
raw -PREV/terminal-copy mismatch and trim residuals
switch-charge autozero residuals
8/12/8/10/8 edge/self/drive/error/sense quantization
credit-path noise, offset, curvature and leakage
circuit-native selected-edge thermal packets at b=1e-5
```

## Claim boundary / next thermal gates

This qualification covers the sampled **reciprocal edge** thermal contribution.
It does not yet cover thermal noise associated with:

```text
node-local self coefficient transfer
-PREV/history transfer
terminal A->B state-copy switches
state-bank reset/initialization
sense path / calibration measurement noise
layout-correlated and reference/substrate noise
```

Bodies 1800–1809 are now spent.

The next circuit-native noise model should attach kT/C to the node-local self and
history primitives according to their actual switched-cap topology, then run a
fresh simultaneous gate rather than falling back to the rejected arbitrary
full-node-noise abstraction.
