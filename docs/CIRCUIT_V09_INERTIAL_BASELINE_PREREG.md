# TW-1A v0.9 fixed inertial baseline — preregistration

Status: **architecture diagnostic on spent bodies 2300..2309**.

The v0.8 thermal path split localized the first kT/C wall to the node-local self sample. The compiler audit then showed that, on the qualified continuous-wave tasks, the active-node self term is almost entirely the universal second-order inertial coefficient:

```text
old programmable self |d|       1.9937595
kick residual |d-2|             0.00624048
coefficient-magnitude reduction ~319.5x
sampled-noise amplitude ratio   ~17.87x
```

v0.9 therefore asks whether the universal `+2 * CUR` contribution can be moved to a **fixed measured inertial path**, while only the small residual `d-2` remains on a programmable sampled-capacitor path.

This keeps the existing v0.8 position-history state representation, structural `-PREV`, common/difference reverse coordinates and single signed error lane. The kick-drift algebra is used to justify the split; this diagnostic does not yet require storing momentum as a new physical state.

## Circuit abstraction under test

Per node:

```text
NEXT = g_inertial * CUR
     + k_residual * CUR
     + reciprocal_edges(CUR)
     - PREV
     + source
```

with foreground measurement

```text
k_residual_target = d_logical - g_inertial_measured.
```

The fixed path may have raw static mismatch. That is measured and compensated by the residual path as long as residual range remains available. Only its **dynamic additive noise** is swept here.

Frozen v0.9 provisional hardware values:

```text
nominal inertial gain                  2.0
raw inertial gain mismatch             1% RMS
foreground inertial measurement error  0.1% RMS
residual self range                    +/-0.125
residual self signed resolution        10 bits
residual path inherited gain/cal error v0.8 values
```

The residual range is audited on every body before learning; saturation is an immediate fail.

## Frozen background

Everything not named above remains at the fresh-qualified v0.8 self-thermal point, except that the already-earned edge thermal margin is used:

```text
edge b                 = 2e-5
residual-self b        = 2e-5
edge nominal range     = 0.265
edge unit mismatch     = 3% RMS
site ratio mismatch    = 1% RMS
kick cancellation err  = 0.5% RMS
kick floors            = 2 ppm common / 1 ppm differential
all converter/leakage/LCC/credit settings unchanged
iterations             = 30
step size              = 0.20
```

Using `2e-5` for the residual-self sampler is deliberately conservative: the residual coefficient is tiny, so its delivered RMS is `2e-5*sqrt(|k_residual|)`.

## Inertial-path noise sweep

Independent additive inertial-path RMS per node per wave tick, as fraction of state full scale:

```text
0
1e-5
1.5e-5
2e-5
2.5e-5
3e-5
```

A dedicated RNG stream is used so adding this block cannot redraw any existing v0.8 disorder.

## Frozen learning predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Interpretation

- If `2e-5` inertial noise is clean, the architecture has a credible path to the 4x-smaller thermal capacitance scale associated with `b=2e-5`, subject to a later physical implementation of the fixed inertial path.
- If only around `1e-5` is clean, the algebra removes the large programmable self capacitor but does not yet buy the full state-capacitance reduction.
- If even zero inertial noise is not clean, the split/quantization/static compensation itself is invalid and v0.9 is rejected.

No fresh seeds are authorized by this experiment. A passing noise target must first be translated into a circuit primitive / SPICE gate rather than declared free.
