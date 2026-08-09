# TW-1A v0.8 combined edge + self thermal budget sweep

Status: **diagnostic only; seeds 2300--2309 are spent by the fresh self-thermal
qualification**.

The fresh v0.8 gate has now passed with both active edge sampling and local self
sampling at the same thermal base `b=1e-5`.  The next question is economically
important because the state-cap lower bound scales as

```text
Cstate = kT / (b * VFS)^2,
```

so a 2x/3x increase in tolerable `b` reduces thermal capacitance by 4x/9x.

## Same-silicon / same-noise-stream rule

Every condition uses the exact fresh-qualified static v0.8 operating point and
seed mapping from `CIRCUIT_V08_SELF_THERMAL_PREREG.md`:

- common/difference reverse coordinates;
- active virtual charge summing;
- structural `-PREV`;
- 0.265 nominal edge range;
- 3% independent edge unit-cap mismatch;
- 1% site-common edge ratio mismatch;
- 0.5% kick-cancellation measurement error;
- unchanged 2 ppm / 1 ppm kick floors;
- all retained converter, self calibration, C/D hold, leakage, LCC and credit
  background unchanged.

Only the two dynamic thermal amplitudes are changed together:

```text
b_edge = b_self = b.
```

All frozen `b` values are nonzero, so the edge and self thermal generators make
the same number of random draws in every condition. Their RNG seeds do not
depend on `b`; therefore the same normalized noise samples are simply rescaled.
Static fabrication also does not depend on either thermal amplitude.

## Frozen thermal points

```text
b = 1e-5   # fresh-qualified reference
    2e-5
    3e-5
    5e-5
```

No intermediate point is added after results are observed.

## Spent bodies

```text
2300--2309
```

## Readout

At each `b` report:

```text
count improvement >= +0.10
count final exact > shuffled
median/min improvement
median/min placement gap
```

Also report the implied scalar thermal `Cstate` at 300 K for effective voltage
swings 0.5 V, 1.0 V and 2.0 V, plus the corresponding known v0.8 capacitor
subtotal

```text
256*Cstate state banks
+ 112*0.265*Cstate edge banks
+ 64*1.5*Cstate reusable self banks
= 381.68*Cstate.
```

Area conversion uses the same **illustrative** 1 fF/um^2 MIM assumption as the
cost report; it is not a foundry claim.

## Decision rule

A point is `clean` only if it satisfies the unchanged formal learning predicate:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

If 5e-5 is clean, reserve a future fresh gate at the already-tested inward point
3e-5.  If 3e-5 is clean but 5e-5 fails, reserve 2e-5.  If 2e-5 is clean but
3e-5 fails, retain 1e-5 as the only fresh-qualified point and do not spend fresh
seeds merely to reconfirm it.  If even the 1e-5 replay fails, investigate RNG /
implementation consistency before drawing any thermal conclusion.

This sweep does not change the fresh-qualified v0.8 operating point by itself.
