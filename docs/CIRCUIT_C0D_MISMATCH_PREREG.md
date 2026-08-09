# TW-1A C0d capacitor mismatch study — frozen plan

Status: **physical architecture diagnostic**, frozen before mismatch results are
inspected.  This study does not use temporal-order bodies and therefore does not
create a new learning qualification.

## Question

Given the C0c result that a nominal seven-bit magnitude capacitor array is
compatible with v0.5 learning, how should the same 127 unit capacitors be
selected so fabricated unit mismatch does not create non-monotonic codes or
large calibrated gaps?

## Common physical model

```text
127 unit capacitors total
nominal Cunit/Csum = 0.001
unit capacitor i = Cunit * (1 + eps_i)
eps_i iid Normal(0, sigma_unit)
```

At the largest frozen `sigma_unit=10%`, a negative unit value is astronomically
unlikely; any generated nonpositive unit is nevertheless rejected as an invalid
sample rather than clipped silently.

For effective selected capacitance `c` in nominal-Cunit units, the raw
charge-sharing level is

```text
f(c) = (c*r) / (1 + 2*c*r),  r=0.001.
```

Each fabricated cell is assumed to undergo foreground codebook measurement.
Therefore its measured level set is normalized by its own code-127 full scale
before calibrated nearest-code error is evaluated.

## Selection architectures

### A — pure binary

Seven physical branches contain disjoint groups of

```text
1, 2, 4, 8, 16, 32, 64 unit capacitors.
```

Magnitude code bits select the corresponding branches.  Critical carry examples
are `1->2`, `3->4`, `7->8`, ..., `63->64`.

### B — segmented 4+3

The lower four bits are binary groups

```text
1, 2, 4, 8 units
```

and the upper three-bit magnitude value is represented by seven thermometer
segments of 16 unit capacitors each.  Code `m` selects the first `m>>4`
thermometer segments plus the four lower binary branches for `m&15`.

Total units remain

```text
15 + 7*16 = 127.
```

The hardest carry is reduced from nominal `64 versus 63` to `16 versus 15`.

### C — full thermometer

Magnitude code `m` selects the first `m` of 127 positive unit capacitors.
Monotonicity is structural as long as every unit capacitance remains positive.

## Frozen Monte Carlo

```text
sigma_unit = 0.001, 0.003, 0.01, 0.03, 0.05, 0.10
samples per architecture per sigma = 5000
rng seed = 20260809
```

The same generated unit-cap samples are used across all three architectures at
a given Monte Carlo index where possible, so architecture comparisons do not
hide behind different random draws.

## Metrics

For every fabricated cell:

1. **monotonic** — all 127 adjacent measured magnitude steps are strictly
   positive;
2. **minimum step** — smallest adjacent normalized physical level spacing;
3. **largest gap** — largest adjacent normalized physical level spacing;
4. **calibrated half-gap** — half of the largest gap, the worst nearest-code
   coefficient error for a target lying midway between two measured codes;
5. **worst carry location** — index of the smallest adjacent step.

For each architecture/sigma report:

```text
monotonic yield
median minimum step
1st percentile minimum step
median calibrated half-gap
99th percentile calibrated half-gap
most common failing carry, if any
```

## Interpretation rule

Do not choose a topology merely because its mean transfer error is small.
Priority order is:

```text
1. structural / statistical monotonicity;
2. calibrated gap size;
3. circuit/control complexity.
```

The result will choose which selection topology deserves the next SPICE mismatch
and per-edge-codebook learning gate.  No tolerance will be retroactively changed
inside this study.
