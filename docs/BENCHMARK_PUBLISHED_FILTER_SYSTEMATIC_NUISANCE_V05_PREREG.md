# Published filter with systematic measurement/model nuisance v0.5 — preregistration

Date: 2026-08-09

Status: **synthetic systematic-mismatch benchmark; frozen before outcomes.**

## Purpose

v0.4 recovered the published seven-knob cross-coupled matrix in 15/15 fits when the only measurement corruption was zero-mean pointwise amplitude/phase noise averaged across eight sweeps.

v0.5 adds two qualitatively different effects that **do not average away**:

1. resonator dissipation / finite-Q represented by a uniform normalized resonator loss term;
2. unknown complex reference-plane phase offsets and linear electrical-delay slopes on measured `S11` and `S21`.

The same synthetic measurement is fitted in two preregistered ways:

```text
NAIVE : seven matrix knobs only, lossless model, no phase nuisance
AWARE : seven matrix knobs + uniform resonator loss + four phase nuisance terms
```

Both models are fixed before outcomes. The naive fit is a baseline, not a straw-man pass criterion.

## Frozen hidden physical matrix

Use the v0.3 published target:

```text
[mS1,m12,m23,m34,m4L,m14,mSL]
=
[1.02,-0.86,0.77,-0.86,1.02,-0.19,0.0005].
```

Use the same composite normalized frequency grid

```text
Omega = unique(linspace(-30,+30,601) union linspace(-3,+3,601)).
```

## Frozen lossy physical response

The hidden synthetic physical filter uses

```text
A(Omega) = M + Omega U - j(q + lambda U)
lambda_target = 0.020.
```

`U` is one on resonator diagonals and zero at source/load; `q` is one only at source/load. Positive `lambda` therefore adds equal normalized dissipation to all four resonators.

This is a controlled matrix-level finite-Q surrogate. v0.5 does **not** claim that one scalar `lambda` captures all real resonator losses.

## Frozen systematic reference-plane nuisance

Before zero-mean measurement noise, apply

```text
S11_sys = S11_lossy * exp(j(phi11 + tau11*Omega))
S21_sys = S21_lossy * exp(j(phi21 + tau21*Omega)).
```

Five nuisance settings are fixed:

| ID | phi11 | tau11 [rad/Omega] | phi21 | tau21 [rad/Omega] |
|---|---:|---:|---:|---:|
| 4200 | +5 deg | +0.020 | -7 deg | -0.015 |
| 4201 | -9 deg | +0.035 | +4 deg | -0.025 |
| 4202 | +12 deg | -0.030 | -11 deg | +0.040 |
| 4203 | -6 deg | -0.045 | +10 deg | +0.030 |
| 4204 | +8 deg | +0.050 | -5 deg | -0.045 |

The slope acts over the entire `Omega=+-30` stress grid, so the far-frequency phase nuisance is intentionally substantial.

## Frozen zero-mean sweep noise

After systematic loss/phase effects, generate eight independent sweeps using the v0.4 model:

```text
S_meas = S_sys * (1 + eps_A) * exp(j eps_phi)

eps_A   ~ Normal(0,0.005)
eps_phi ~ Normal(0,0.5 deg).
```

Arithmetic-average the eight complex sweeps pointwise. Derived independent RNG streams are used for `S11` and `S21`, deterministically rooted at the nuisance ID.

## Frozen starts

Cross every nuisance setting with the three already-spent matrix starts:

```text
A, C, D
```

from v0.3/v0.4, for 15 measurement/start cells. Each cell is fitted once by the NAIVE model and once by the AWARE model.

## NAIVE model

Fit only the seven matrix knobs with the existing lossless generalized coupling-matrix model and existing bounds.

Frozen optimizer:

```text
iterations=1600
Adam learning_rate=0.015
beta1=0.9
beta2=0.999
epsilon=1e-8.
```

No naive pass/fail threshold is preregistered. Its purpose is to quantify how much a perfect matrix model is distorted when systematic measurement physics is omitted.

## AWARE model

Fit the 12-vector

```text
[mS1,m12,m23,m34,m4L,m14,mSL,
 lambda, phi11, tau11, phi21, tau21].
```

Initial nuisance values:

```text
lambda=0.010
phi11=phi21=0
tau11=tau21=0.
```

Frozen nuisance bounds:

```text
0 <= lambda <= 0.080
-pi/2 <= phi11,phi21 <= +pi/2
-0.10 <= tau11,tau21 <= +0.10 rad/Omega.
```

The seven matrix bounds remain exactly those of v0.3/v0.4.

Frozen optimizer:

```text
iterations=3000
Adam learning_rate=0.010
beta1=0.9
beta2=0.999
epsilon=1e-8.
```

No staged fit, restarts, schedules or post-outcome per-parameter learning-rate changes are allowed.

The aware gradient must be audited against central finite differences for the full 12-vector before benchmark outcomes are interpreted.

## Frozen scoring

For both models record:

```text
fit-to-noisy-measurement loss
hidden seven-knob matrix RMSE
main-path RMSE
m14 absolute error
mSL absolute error
```

For AWARE also record:

```text
lambda absolute error
wrapped phi11/phi21 errors
tau11/tau21 absolute errors
hidden systematic-response complex MSE
max complex S11/S21 error against the noiseless systematic target.
```

## Frozen AWARE pass criterion

Call v0.5 an **AWARE SYSTEMATIC ROBUSTNESS PASS** only if at least 14/15 aware fits satisfy all:

```text
matrix overall RMSE <= 0.010
main-path RMSE <= 0.010
|m14-target| <= 0.010
|mSL-0.0005| <= 0.0005
|lambda-0.020| <= 0.005
wrapped |phi11 error| <= 2 deg
wrapped |phi21 error| <= 2 deg
|tau11 error| <= 0.005 rad/Omega
|tau21 error| <= 0.005 rad/Omega
hidden systematic-response complex MSE <= 5e-5
```

A stronger **15/15 SYSTEMATIC RECOVERY** label requires all 15 aware cells to satisfy the same clauses.

## Frozen comparison to NAIVE

Report median and worst hidden matrix RMSE for NAIVE and AWARE. Also report how many NAIVE fits happen to satisfy the seven-knob matrix clauses above, but do not require NAIVE to fail.

Call the nuisance layer **materially useful** if

```text
median AWARE matrix RMSE <= 0.25 * median NAIVE matrix RMSE.
```

This comparison was frozen before either model saw v0.5 data.

## Decision

- **15/15 aware pass + materially useful:** promote measurement nuisance terms into the `twc-filter` model surface. Next test nonuniform resonator losses / topology error or a real measured CSV/Touchstone ingestion path.
- **14/15 aware pass:** retain the measurement-aware direction, diagnose only the spent failure before expanding nuisance complexity.
- **<14/15 aware pass:** do not reduce the systematic stress post hoc. Diagnose identifiability/optimizer scaling on these same cells.

This is a computer-side tuning benchmark. It is unrelated to rescue of TW-1A small-cap on-device stochastic gradient learning.
