# Published coupled-resonator filter tuning benchmark v0.1 — result

Date: 2026-08-09

Status: **PASS — EXACT RECOVERY on all 5/5 preregistered detuned starts.**

Preregistration: `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_PREREG.md`

Workflow: `published-coupled-filter-v01`, successful run `31330164100`.

## External target

The target is the published three-resonator reciprocal coupling matrix from S. Gruszczynski and K. Wincza, Electronics 11(8), 1250 (2022), DOI `10.3390/electronics11081250`:

```text
M_target = [[0.0, 0.6, 0.2],
            [0.6, 0.0, 0.6],
            [0.2, 0.6, 0.0]]
```

with endpoint loading parameter `r=1`.

The benchmark uses the standard narrowband coupling-matrix response

```text
A(gamma) = gamma I - jR + M
S11      = 1 + 2j R1 [A^-1]11
S21      = -2j sqrt(R1 R2) [A^-1]N1
```

and fits the target `|S11|` and `|S21|` response over 401 normalized-frequency samples.

Before any optimization result was interpreted, the exact inverse-matrix derivative

```text
d A^-1 / dm = -A^-1 (dA/dm) A^-1
```

passed a central finite-difference unit audit.

## Results

Parameter order is `[m12, m23, m13]`.

| start | detuned values | final values | initial loss | final loss | reduction | parameter RMSE | pass | exact |
|---|---|---|---:|---:|---:|---:|:---:|:---:|
| A | `[0.35, 0.82, -0.05]` | `[0.5998695, 0.6001304, 0.1999998]` | 1.251e-1 | 5.172e-12 | 2.419e10 | 1.065e-4 | yes | yes |
| B | `[0.85, 0.35, 0.45]` | `[0.5998609, 0.6001391, 0.1999998]` | 1.228e-1 | 6.657e-12 | 1.844e10 | 1.136e-4 | yes | yes |
| C | `[0.30, 0.30, 0.50]` | `[0.6000000, 0.6000000, 0.2000000]` | 8.728e-2 | 4.277e-32 | 2.041e30 | 1.623e-14 | yes | yes |
| D | `[1.00, 0.75, -0.30]` | `[0.6001212, 0.5998787, 0.1999999]` | 2.219e-1 | 3.868e-12 | 5.738e10 | 9.897e-5 | yes | yes |
| E | `[0.45, 1.00, 0.00]` | `[0.6001198, 0.5998801, 0.1999999]` | 9.381e-2 | 3.698e-12 | 2.537e10 | 9.786e-5 | yes | yes |

All five starts satisfy the frozen PASS clauses by many orders of magnitude.

The stronger **EXACT RECOVERY** clause required parameter RMSE <= `0.005` for all starts. The worst observed RMSE is about `1.14e-4`, so exact recovery passes comfortably.

Worst final magnitude-response errors across the five runs are also tiny:

```text
max |S11| error < 5.0e-5
max |S21| error < 3.0e-7
```

## Why this result matters

This is the first benchmark in the project whose target comes directly from a published coupled-resonator filter realization rather than from the temporal-order learning harness.

The mathematical overlap is concrete:

```text
TW compiler core:        sparse reciprocal symmetric operator
filter coupling matrix:  sparse reciprocal symmetric operator
local derivative:        inverse/adjoint response to one symmetric edge stamp
```

The physical normalization differs — narrowband frequency-domain coupling matrices are not literally the TW kick-drift recurrence — so the repository now keeps the filter application in a separate module rather than pretending the two models are identical. But the topology, sparse symmetric parameterization and edge-local gradient structure are genuinely shared.

## Comparison with the chip-learning wall

The controlled v0.9 hardware work found that independent sampled thermal noise makes tape-free stochastic reverse credit extremely noisy and partly biased. Capacitor-only rescue, 64x physical-gradient averaging, one-direction forward SPSA, and a 64-direction forward Hadamard learner all failed their frozen on-device robustness criteria at the attractive small-cap point.

The published filter problem has no such requirement. Its response can be measured accurately and tuned slowly/offline. Under that regime the compiler-side exact gradient is extremely well conditioned: all five deliberately detuned matrices recover the published coupling values.

This is therefore positive evidence for the project split:

```text
TW-1A small-cap on-device gradient learner -> research result / not qualified
TWC sparse reciprocal tuning compiler      -> externally relevant application path
```

## Frozen next step

The preregistration authorized, after exact recovery:

1. add resonator self-detuning (diagonal coupling-matrix entries) as tunable physical knobs;
2. move to a larger published filter with a prescribed cross-coupled / transmission-zero topology;
3. preserve response and parameter recovery as separate criteria so coupling-matrix gauge equivalences cannot be mistaken for tuning failure.

Those are now the mainline compiler experiments. No chip fabrication claim follows from this result.
