# TW-1A v0.9 full kick-drift thermal diagnostic — result

Date: 2026-08-09

Status: **PASS on spent bodies through `b_drift=2e-5`; no fresh seed authorized yet.**

Preregistration: `docs/CIRCUIT_V09_KICK_DRIFT_THERMAL_PREREG.md`

This is the first complete learner executed in exact kick-drift coordinates:

```text
Z = z[n]
P = z[n] - z[n-1]
K = Q - 2 I

P <- P + K Z + source
Z <- Z + P
```

The same two stored vectors per common/difference context are reused. Reciprocal
edge coefficients are unchanged; only the local self path is shifted by `-2`.
The v0.8 common/difference credit sensor still observes the current Z fields.

Frozen sampled thermal bases:

```text
edge b                 = 2e-5
kick-residual self b   = 2e-5
```

The unity drift `Z<-Z+P` received an independent kT/C sample every tick. The
terminal inverse drift `Z<-Z-P` was charged one sample of the same noise model.
No drift-specific switch-kick residual was included in this first thermal gate.

## Results

| drift b | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | minimum gap | clean |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0 | 10/10 | 10/10 | +0.622551 | +0.326954 | +0.609661 | +0.354220 | YES |
| 2.5e-6 | 10/10 | 10/10 | +0.615628 | +0.357317 | +0.600975 | +0.341057 | YES |
| 5e-6 | 10/10 | 10/10 | +0.627867 | +0.327927 | +0.581345 | +0.321875 | YES |
| 7.5e-6 | 10/10 | 10/10 | +0.622487 | +0.341922 | +0.591644 | +0.327111 | YES |
| 1e-5 | 10/10 | 10/10 | +0.617806 | +0.332487 | +0.592642 | +0.353567 | YES |
| 1.5e-5 | 10/10 | 10/10 | +0.598330 | +0.290273 | +0.562269 | +0.278695 | YES |
| 2e-5 | 10/10 | 10/10 | +0.561704 | +0.234039 | +0.533367 | +0.196891 | YES |

Every preregistered drift-noise point is clean. The full `b_drift=2e-5` point
therefore survives with the same fourfold-smaller kT/C capacitance scale already
used by edge and residual-self sampling.

The complete-tile residual-self audit also remains inside the provisional
`+/-0.125` bank. The maximum target seen in this diagnostic was about 0.06478.

## Why this differs from the rejected fixed-gain-2 experiment

The earlier fixed-inertial-baseline emulator added a fresh independent full-node
noise source to a near-2 analog multiplier every recurrence tick. That failed at
only `1e-5 FS/tick`.

Kick-drift does not implement `2*CUR` as a noisy multiplier. It changes the
state coordinates and performs two shears. The programmable sampled self
coefficient is small, and the remaining unity drift receives its own physically
located sample noise. Under that model the complete learner has much larger
margin.

## Known capacitor consequence

At the old v0.8 point:

```text
state banks       256.00 C_old
edge banks         29.68 C_old
self banks         96.00 C_old
subtotal          381.68 C_old
```

At `b=2e-5`, `C_new=C_old/4`. A first kick-drift provision including one reusable
full-size drift sample capacitor per node is

```text
state banks       256.00 C_new
edge banks         29.68 C_new
kick-self bank      8.00 C_new   # 64 * 0.125
unity-drift bank   64.00 C_new
subtotal          357.68 C_new
```

Thus

```text
A_new/A_v08 = 357.68 / (4 * 381.68) = 0.23428
```

or about **4.27x smaller known capacitor area** before active-circuit overhead.
With the same illustrative `1 fF/um^2`, 1 V, 300 K assumptions used by the cost
model, the known-cap estimate moves from roughly 15.81 mm^2 to roughly 3.70
mm^2. An 8-bit, 2.5 um^2/bit SRAM-tape comparison then crosses around 2.9k ticks.

These remain assumption-explicit lower-bound capacitor numbers, not foundry or
total-chip area claims.

## Next gate

The result does **not** authorize fresh seeds because C1f's drift shear uses
switches and the thermal emulator has not yet modeled drift-specific residual
charge injection. The next spent-body gate must add a fixed/common and
context-differential residual packet for the unity drift switch path, then map
the learned tolerance to a cancellation/autozero circuit requirement.
