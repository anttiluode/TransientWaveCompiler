# Published filter with systematic measurement/model nuisance v0.5 — result

Date: 2026-08-09

Status: **PASS — 15/15 AWARE SYSTEMATIC RECOVERY; NAIVE hidden-matrix recovery 0/15.**

Preregistration: `docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_PREREG.md`

Workflow: `published-filter-systematic-nuisance-v05`, run `31331249454`.

## Frozen stress

Every synthetic measurement contains all of the following simultaneously:

```text
published seven-knob cross-coupled matrix
uniform normalized resonator loss lambda = 0.020
unknown S11 phase offset + linear phase slope
unknown S21 phase offset + linear phase slope
0.5% RMS pointwise amplitude noise
0.5 degree RMS pointwise phase noise
8 complex sweeps averaged pointwise
```

Five frozen systematic phase settings were crossed with three substantially different matrix starts (`A`, `C`, `D`) for 15 measurement/start cells.

Each cell was fitted twice against the exact same measured data:

```text
NAIVE : 7 matrix knobs, lossless response, no phase nuisance
AWARE : 7 matrix knobs + lambda + phi11 + tau11 + phi21 + tau21
```

The full 12-variable aware derivative passed its preregistered central finite-difference audit before benchmark outcomes were interpreted.

## Headline result

```text
AWARE full frozen nuisance clause       15/15
NAIVE hidden seven-knob matrix clause    0/15
```

The stronger preregistered label therefore applies:

```text
15/15 SYSTEMATIC RECOVERY
```

The preregistered usefulness test also passes:

```text
median AWARE matrix RMSE <= 0.25 * median NAIVE matrix RMSE.
```

So the extra nuisance variables are not merely reducing fit residual. They materially improve recovery of the **hidden physical coupling matrix**.

## What the first completed cells already showed

Two early completed cells illustrate the size of the effect before aggregation:

```text
NAIVE overall matrix RMSE: roughly 0.023 .. 0.053
NAIVE mSL error:            roughly 0.0014 .. 0.0035
```

on a hidden direct source-load target of only

```text
mSL = 0.0005.
```

In those same measured traces the AWARE fit recovered the matrix at roughly `2e-5 .. 6e-5` overall RMSE, recovered the uniform loss within about `7e-5`, and recovered phase offsets within hundredths of a degree.

The full 15-cell pass establishes that this separation is not peculiar to those first cells.

## Why the naive failure matters

This is qualitatively different from v0.4 zero-mean measurement noise.

A constrained reciprocal matrix is a strong regularizer against pointwise random noise, so eight-sweep averaging allowed the clean hidden matrix to be recovered accurately.

Systematic phase delay and resonator dissipation do not average away. If the model omits them, the optimizer has only one place to put the discrepancy:

```text
change the resonator/coupling matrix.
```

The resulting low-level lesson is important for any automated filter tuner:

> **measurement-chain physics must be modeled as nuisance parameters, or the optimizer can convert calibration/reference-plane error into false coupling corrections.**

The AWARE model supplies separate degrees of freedom for exactly those effects and recovers the hidden matrix on all 15 frozen cells.

## What v0.5 earns

Per preregistration, the measurement nuisance model is now justified as part of the product-side filter tuner rather than experiment-only scaffolding.

The application evidence ladder is now:

```text
v0.1  published 3-resonator couplings                 5/5 exact
v0.2  resonator offsets + couplings                   5/5 exact
v0.3  published 6x6 four-zero cross-coupled topology 5/5 exact
v0.4  zero-mean repeated complex measurement noise   15/15 robust
v0.5  systematic loss + reference-plane nuisance     15/15 aware
                                                     0/15 naive matrix recovery
```

## Current boundary

v0.5 still uses a deliberately simple systematic model:

```text
one common loss lambda for every resonator
linear reference-plane phase versus normalized frequency
known matrix topology
no actuator hysteresis
no frequency-dependent parasitic coupling
no outliers or slow drift
```

So this is not yet a claim of universal automatic cavity tuning.

But the compiler/tuner has now crossed an important line: it has survived both random measurement corruption and a preregistered case where **model mismatch actively creates wrong physical knob estimates unless the nuisance physics is represented**.

## Next product move

Promote optional

```text
uniform resonator loss
S11 phase offset/slope
S21 phase offset/slope
```

into the `twc-filter` JSON/CLI model surface while retaining the simple lossless mode for already-calibrated synthetic data.

After that, the next research gate should target one of the remaining genuinely physical mismatches rather than another clean matrix:

```text
nonuniform per-resonator loss
unknown extra parasitic topology edge
actuator calibration/nonlinearity
real Touchstone/CSV measurement ingestion and reference-plane preprocessing.
```

This result concerns computer-side filter tuning only. It does not change the negative conclusion on TW-1A small-cap stochastic on-device gradient learning.
