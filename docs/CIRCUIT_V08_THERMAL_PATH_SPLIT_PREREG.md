# TW-1A v0.8 edge/self thermal path split — preregistration

Status: **diagnostic only on spent fresh-qualified bodies 2300..2309**.

The combined edge+self thermal sweep showed that the fresh-qualified `b=1e-5` point is clean, while tying both paths to `b=2e-5` is not. This experiment asks which sampled path is responsible. It does **not** spend new bodies and it does not change any learning tolerance, iteration count, converter setting, kick-calibration target, fabrication model, or shuffled-credit control.

## Frozen silicon and task bodies

Use exactly seeds `2300..2309`, already spent by the fresh self-thermal gate. For each seed, all static fabricated disorder and all thermal RNG stream seeds remain identical across conditions. Only the amplitudes of the edge and self kT/C laws change.

## Frozen operating point

All non-thermal settings are inherited from `experiments/circuit_v08_self_thermal_corner.py`, including:

- v0.8 common/difference reverse coordinates;
- structural `-PREV`;
- 0.265 nominal edge range;
- 1% RMS site-common Cunit/Cstate variation;
- 3% unit-cap mismatch;
- 0.5% kick-cancellation measurement error;
- unchanged 2 ppm common / 1 ppm differential kick floors;
- same converter, leakage, LCC and credit-path settings;
- 30 learning iterations, step size 0.20;
- same fixed task-specific sense PGA selection;
- same shuffled-credit control.

## Conditions

Reference:

```text
edge b = 1e-5
self b = 1e-5
```

Edge-only outward sweep, holding self at the qualified point:

```text
edge b = 2e-5, 3e-5, 5e-5
self b = 1e-5
```

Self-only outward sweep, holding edge at the qualified point:

```text
edge b = 1e-5
self b = 2e-5, 3e-5, 5e-5
```

The formal predicate is unchanged:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Interpretation frozen before results

- If edge-only 2e-5 fails while self-only 2e-5 passes, the reciprocal edge sample path is the thermal bottleneck.
- If self-only 2e-5 fails while edge-only 2e-5 passes, the node-local self sample path is the bottleneck.
- If both fail independently, the present 1e-5 base is a distributed thermal requirement and selective oversizing is unlikely to buy much.
- If both pass independently but the tied 2e-5 condition fails, the problem is an interaction of independent thermal sources; the next experiment should allocate a two-dimensional edge/self noise budget instead of scaling both together.

No fresh seed is authorized by this diagnostic. A later qualification point must be preregistered separately.
