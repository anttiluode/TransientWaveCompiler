# TW-1A v0.8 self-sampling thermal diagnostic

Status: **diagnostic only; seeds 2200--2209 are spent by the fresh-qualified
kick-calibrated v0.8 gate**.

The fresh-qualified v0.8 operating point includes active edge-sampling kT/C but
not the local programmable self-sample capacitor. C1e2/C1e3 have now made the
self actuator concrete: the worst |self|=3 coefficient is delivered as two
equal samples through one reusable half-range bank.

For a physical self coefficient magnitude |d|, two independent equal slices
have total sampling-noise variance

```text
sigma_self^2 / VFS^2 = |d| * b_self^2
```

so

```text
sigma_self / VFS = b_self * sqrt(|d|).
```

The law is independent of the equal slice count; slicing changes timing/load,
not total ideal kT/C variance.

## Same-silicon / RNG rule

Both conditions use the exact fresh-qualified v0.8 static physical operating
point:

- 0.265 nominal edge range;
- 3% unit-cap mismatch;
- 1% site-common edge ratio mismatch;
- edge thermal `b=1e-5`;
- 0.5% foreground kick-cancellation measurement error;
- unchanged 2 ppm / 1 ppm kick floors;
- all other retained mixed-signal background unchanged.

Self thermal uses a dedicated RNG derived from the tile seed. Enabling it does
not redraw static silicon and does not perturb the inherited edge-thermal or
credit RNG streams.

## Frozen conditions

Exactly two:

```text
self_b0      self_ktc_base_fraction = 0
self_b1e-5   self_ktc_base_fraction = 1e-5
```

No intermediate self-noise point or other idealization is added after results
are observed.

## Spent bodies

```text
2200--2209
```

## Reported predicate

For each condition report:

```text
count improvement >= +0.10
count final exact > shuffled
median/min improvement
median/min placement gap
```

Also report the maximum programmed |self| coefficient and corresponding maximum
self thermal RMS fraction observed on each target tile.

## Decision

If `self_b1e-5` satisfies the unchanged fresh learning predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

then reserve fresh 2300--2309 for a self-thermal-inclusive qualification at the
same physical point. If it fails, no fresh seeds are reserved; freeze a self
thermal scale sweep on 2200--2209 first.
