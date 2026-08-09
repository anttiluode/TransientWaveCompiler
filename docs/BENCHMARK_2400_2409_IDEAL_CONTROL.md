# Temporal-order benchmark 2400..2409 — ideal physical-credit control

Date: 2026-08-09

Status: **benchmark diagnostic; does not alter any previous formal gate.**

After the fresh v0.9 gate failed 8/10, the same task seeds were run through an ideal physical-credit reference with:

```text
no weight/DAC/ADC quantization
no state noise
no leakage
no clipping
no mirror error
no differential pass drift
no credit offset
no credit readout noise
same 30 updates
same step size 0.20
same physical-credit learning rule
```

## Results

| seed | ideal DeltaC | ideal placement gap | exact > shuffled |
|---:|---:|---:|:---:|
| 2400 | +0.864382 | +0.607612 | yes |
| 2401 | +0.841869 | +0.384828 | yes |
| 2402 | +0.555789 | +0.753083 | yes |
| 2403 | +0.843161 | +0.449618 | yes |
| 2404 | +0.993097 | +0.981668 | yes |
| 2405 | +0.052904 | +0.280339 | yes |
| 2406 | +0.744431 | +0.453466 | yes |
| 2407 | +0.998321 | +1.095082 | yes |
| 2408 | +0.757526 | +0.653489 | yes |
| 2409 | +0.491374 | +0.432632 | yes |

Summary:

```text
ideal improvement >= +0.10       9/10
ideal exact > shuffled           10/10
median ideal improvement        +0.800343
minimum ideal improvement       +0.052904
median ideal placement gap      +0.530539
minimum ideal placement gap     +0.280339
```

## Consequence

The existing absolute qualification clause

```text
10/10 improvement >= +0.10 after 30 updates
```

cannot be interpreted purely as a hardware-fidelity criterion on arbitrary fresh task cohorts: seed 2405 violates it even with the modeled hardware made ideal.

This does **not** retroactively pass the red v0.9 fresh gate. The preregistered rule was the rule and the historical result remains a formal fail.

For future fresh cohorts, a hardware qualification statistic should be preregistered against each task's ideal/reference learnability, for example by measuring degradation relative to an ideal physical-credit control, while retaining exact-over-shuffled placement and fabrication clauses. Any revised benchmark must be frozen before the next fresh seeds are released.

Seed 2400 remains a useful hardware diagnostic because its ideal improvement is +0.864382 while the formal mixed-signal v0.9 body achieved only +0.025219.
