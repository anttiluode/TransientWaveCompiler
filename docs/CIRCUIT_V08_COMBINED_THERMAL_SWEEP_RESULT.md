# TW-1A v0.8 combined edge+self thermal sweep — result

Date: 2026-08-09

Status: **diagnostic on spent bodies 2300..2309; only `b=1e-5` is clean. No fresh seed authorized.**

Preregistration: `docs/CIRCUIT_V08_COMBINED_THERMAL_SWEEP_PREREG.md`

The fresh-qualified v0.8 point uses both active-integrator edge sampling noise and reusable-self-bank sampling noise with

```text
b_edge = b_self = 1e-5
```

where `b = sqrt(kT/Cstate)/VFS` in the current common-capacitance abstraction. This diagnostic scaled both paths together on the already-spent fresh bodies 2300..2309 while preserving all non-thermal circuit settings and the underlying random streams.

## Frozen predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Results

| combined b | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|:---:|
| 1e-5 | 10/10 | 10/10 | +0.396735 | +0.150625 | +0.310108 | YES |
| 2e-5 | 5/10 | 10/10 | +0.100997 | -0.000138 | +0.090951 | NO |
| 3e-5 | 2/10 | 8/10 | +0.041522 | -0.007822 | +0.051924 | NO |
| 5e-5 | 1/10 | 6/10 | +0.009561 | -0.022604 | +0.012208 | NO |

The first outward point is already a real failure. In particular, at `2e-5` the machine still places the exact-credit learner above the same-credit shuffled control on **10/10** bodies, but the magnitude of learning collapses: only 5/10 clear the +0.10 improvement threshold and the median placement gap falls to +0.091.

This suggests that the local credit retains substantial ordering information before it retains enough signal-to-noise ratio to drive the frozen 30-step update protocol strongly. That is a diagnostic observation, not a relaxed success criterion.

## Capacitor economics under the same abstraction

Known provisioned capacitor subtotal:

```text
state banks  = 256 Cstate
edge banks   = 112 * 0.265 Cstate = 29.68 Cstate
self banks   = 64 * 1.5 Cstate    = 96.00 Cstate
subtotal     = 381.68 Cstate
```

Using the deliberately illustrative assumptions

```text
300 K
1 fF/um^2 MIM
2.5 um^2 per SRAM bit
8 digital bits/state
```

at effective 1 V state full scale:

```text
b=1e-5: Cstate=41.419 pF, known capacitor area ~15.809 mm^2,
        8-bit tape crossover ~12,351 ticks

b=2e-5: Cstate=10.355 pF, known capacitor area ~3.952 mm^2,
        but this thermal point fails learning on the spent bodies

b=3e-5: Cstate=4.602 pF, known capacitor area ~1.757 mm^2,
        but this point fails strongly
```

These are not foundry estimates and still exclude OTA, credit sensor/integrator, dummy/calibration capacitors, switches, reference buffers, control, clocking, routing and guard structures.

## Decision

The preregistered outward sweep does **not** earn a looser common thermal target and does not authorize fresh seeds.

The next diagnostic is a path split on the same spent bodies:

```text
hold self at 1e-5 and move edge outward;
hold edge at 1e-5 and move self outward.
```

That determines whether the present thermal cost is dominated by reciprocal edge sampling, node-local self sampling, or interaction between the two. Only after that should the area model be changed from one common thermal knob to independently sized physical sampling resources.
