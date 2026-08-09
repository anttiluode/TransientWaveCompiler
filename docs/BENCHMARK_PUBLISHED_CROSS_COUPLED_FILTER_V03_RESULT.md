# Published cross-coupled four-transmission-zero filter benchmark v0.3 — result

Date: 2026-08-09

Status: **PASS — EXACT CROSS-COUPLED RECOVERY on all 5/5 preregistered detuned starts.**

Preregistration: `docs/BENCHMARK_PUBLISHED_CROSS_COUPLED_FILTER_V03_PREREG.md`

Workflow: `published-cross-coupled-filter-v03`, successful run `31330625097`.

## Published target

v0.3 uses the explicit source–four-resonator–load matrix published by Shuang Li, Shengxian Li and Jianrong Yuan, Electronics 12(11), 2539 (2023), DOI `10.3390/electronics12112539`:

```text
M = [[0,      1.02,  0,     0,     0,      0.0005],
     [1.02,   0,    -0.86,  0,    -0.19,   0     ],
     [0,     -0.86,  0,     0.77,  0,      0     ],
     [0,      0,     0.77,  0,    -0.86,   0     ],
     [0,     -0.19,  0,    -0.86,  0,      1.02  ],
     [0.0005, 0,     0,     0,     1.02,   0     ]]
```

The seven trainable nonzero matrix knobs are

```text
[mS1, m12, m23, m34, m4L, m14, mSL]
=
[1.02, -0.86, 0.77, -0.86, 1.02, -0.19, 0.0005].
```

The paper uses the resonator cross-coupling and direct source-load coupling to produce two pairs of transmission zeros. The benchmark used the proper generalized explicit-port model

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S).
```

## Structural audit

Before optimization results were interpreted, the generalized module passed all frozen tests:

```text
published 6x6 matrix stamping             PASS
lossless |S11|^2 + |S21|^2 conservation  PASS
7-variable analytic gradient vs FD        PASS
```

The exact parameter derivative remains

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

## Results

The starts deliberately detuned every nonzero matrix path, including source-load coupling values tens of times larger than the target `0.0005`.

| start | final seven-parameter vector | final complex-response loss | overall RMSE | `m14` error | `mSL` error | response | knob | exact |
|---|---|---:|---:|---:|---:|:---:|:---:|:---:|
| A | exact target | 0 | 0 | 0 | 0 | PASS | PASS | PASS |
| B | exact target | 0 | 0 | 0 | 0 | PASS | PASS | PASS |
| C | exact target | 0 | 0 | 0 | 0 | PASS | PASS | PASS |
| D | target except floating-point `mSL=0.0005000000000000042` | 2.896e-33 | 1.60e-18 | 0 | 4.23e-18 | PASS | PASS | PASS |
| E | exact target | 0 | 0 | 0 | 0 | PASS | PASS | PASS |

Therefore:

```text
RESPONSE PASS                    5/5
TOPOLOGY / KNOB RECOVERY PASS    5/5
EXACT CROSS-COUPLED RECOVERY     5/5
```

The tiny direct source-load path is not lost inside the larger mainline couplings: it is recovered to numerical precision from all five starts.

## Why v0.3 matters more than v0.1/v0.2

v0.1 and v0.2 established that a small reciprocal resonator matrix can be tuned and that diagonal resonator offsets can be separated from couplings.

v0.3 adds three important complications simultaneously:

1. explicit source and load nodes rather than hidden endpoint loading;
2. a sign-sensitive resonator cross-coupling used to shape transmission zeros;
3. a direct source-load coupling roughly **three orders of magnitude smaller** than the main source/resonator coupling.

The same sparse local-stamp derivative handles all of them without a hand-derived optimizer for each topology.

## What this does and does not prove

It **does** show that the compiler/tuning layer can recover two published coupling-matrix structures from substantially detuned starts using one audited reciprocal-matrix sensitivity engine.

It does **not** yet show robustness to:

```text
VNA measurement noise
reference-plane phase error
unmodeled loss / finite Q
actuator nonlinearity
frequency-dependent parasitics
matrix topology error
```

Those are now more important than adding another clean synthetic filter.

## Next mainline experiment

Per the frozen decision, exact recovery promotes the application from clean matrix algebra to a synthetic-measurement problem:

> corrupt the published complex S-parameter target with frozen VNA-like amplitude/phase noise and systematic reference-plane phase nuisance, then determine whether matrix knobs can still be recovered from multiple noisy sweeps without changing the topology.

That is the first benchmark that begins to resemble automated filter tuning rather than inverse reconstruction of exact equations.
