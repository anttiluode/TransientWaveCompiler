# TW-1A v0.7 active-summing diagnostic preregistration

Status: **diagnostic only; task bodies already spent by C0e**.

This diagnostic is frozen before observing any v0.7 learning result.  It uses
the previously exercised temporal-order task seeds 1800--1809, so it cannot
qualify v0.7.  Its job is to choose an inward thermal operating point and expose
headroom/yield problems before a fresh formal gate is opened.

## Architectural substitution

Relative to the qualified C0e background, v0.7 makes only these physical-model
changes:

1. passive NEXT charge sharing is rejected; edge packets terminate in an active
   virtual summing / charge-integrator node;
2. each edge coefficient is the measured capacitor ratio directly,
   `a_e=Cselected/Cstate`;
3. nominal code 127 is 0.255, giving 2% nominal physical range beyond the
   compiler edge limit 0.25;
4. unit-cap fabrication sigma remains 3% and every edge keeps its own unsorted
   4-bit-binary + 3-bit-thermometer measured codebook;
5. legacy edge-MDAC gain CV is removed (`edge_gain_cv=0`) because the capacitor
   bank is now the physical coefficient element;
6. legacy common passive-settling gain is removed
   (`edge_common_settling_loss=0`); active-integrator finite gain/settling are a
   separate C1 budget;
7. `-PREV` is structural bank-role inversion: no analog ratio mismatch or trim;
8. sampled-edge thermal noise uses the active-integrator law
   `sigma_edge/VFS=b*sqrt(Cselected/Cstate)`.

All other qualified C0e background errors remain unless structurally obsolete:
self gain/calibration, terminal clone calibration, edge hold A/B mismatch,
switch-kick cancellation residuals, error-DAC asymmetry, LCC curvature, credit
noise/offset/leakage, state leakage and converter widths.

## Frozen task bodies

```text
1800, 1801, ..., 1809
```

## Frozen thermal sweep

```text
b = sqrt(kT/Cstate)/VFS

0
1e-5
3e-5
1e-4
```

The diagnostic must not add intermediate thermal points after seeing results.

## Fabrication audit

For every task body and thermal value, the fabricated target tile must report:

- all 112 edge codebooks strictly monotonic;
- minimum code-127 physical edge range across 112 sites;
- minimum codebook step.

A site whose maximum positive physical level is below 0.25 is a **headroom
failure** even if its codebook is monotonic.  Software is not allowed to sort,
repair or extrapolate the codebook.

## Learning predicate reported at each b

The same predicate used by the recent formal gates is reported, but this is
not a qualification claim:

```text
10/10 exact improvements >= +0.10
10/10 exact final contrasts > shuffled-credit control
median improvement >= +0.30
median placement gap >= +0.25
```

## Decision rule for a fresh v0.7 gate

Choose the largest tested `b` for which:

1. all ten fabricated tiles pass monotonicity and edge-range headroom;
2. all ten task bodies satisfy the learning predicate above.

The fresh v0.7 qualification point must be **at least 3x inward** in thermal
base fraction from that last-clean diagnostic point.  If only `b=0` is clean,
v0.7 is not ready for a fresh formal gate.

Fresh qualification seeds, if opened, are reserved as **2000--2009**.
