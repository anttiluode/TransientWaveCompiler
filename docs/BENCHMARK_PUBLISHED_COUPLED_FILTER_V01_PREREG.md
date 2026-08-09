# Published coupled-resonator filter tuning benchmark v0.1 — preregistration

Date: 2026-08-09

Status: **external-domain compiler benchmark; frozen before optimization outcomes.**

## Published target

Use the three-resonator reciprocal coupling matrix reported by S. Gruszczynski and K. Wincza, *Extraction of Parallel-Coupled and End-Coupled TEM Resonator Networks from a Coupling Matrix in the Design of Coupled-Resonator Filters*, Electronics 11(8), 1250 (2022), DOI 10.3390/electronics11081250:

```text
M_target = [[0.0, 0.6, 0.2],
            [0.6, 0.0, 0.6],
            [0.2, 0.6, 0.0]]
```

The paper states source/load impedance parameter `r = 1` for this example and describes coupling-matrix optimization by minimizing mismatch between target and matrix-derived `|S21|` / `|S11|` characteristics.

For the benchmark use the standard narrowband reciprocal coupling-matrix response

```text
A(gamma) = gamma I - j R + M
S11      = 1 + 2j R1 [A^-1]11
S21      = -2j sqrt(R1 R2) [A^-1]N1
```

with

```text
R1 = R2 = 1
R = diag(1, 0, 1)
gamma in [-2.5, +2.5], 401 equally spaced samples.
```

The target data are generated once from the published matrix using this same standard response convention. This deliberately tests **matrix recovery/tuning**, not reproduction of the paper's separate physical transmission-line extraction stage.

## Trainable topology

Keep the published three-edge topology exactly:

```text
m12
m23
m13 cross-coupling
```

The resonator self-detuning diagonal remains fixed at zero in v0.1. This first benchmark therefore asks whether TWC can tune the **couplings** of the published example, not yet cavity-frequency screws.

Frozen parameter bounds:

```text
0.05 <= m12 <= 1.20
0.05 <= m23 <= 1.20
-0.60 <= m13 <= 0.80
```

The positive bounds on the two main-line couplings remove trivial internal resonator sign-gauge equivalents while preserving the published realization sign convention. The cross-coupling may change sign.

## Frozen detuned starts

Five starts are fixed before outcomes:

```text
A = [0.35, 0.82, -0.05]
B = [0.85, 0.35,  0.45]
C = [0.30, 0.30,  0.50]
D = [1.00, 0.75, -0.30]
E = [0.45, 1.00,  0.00]
```

Parameter order is `[m12, m23, m13]`.

## Objective and exact gradient

At every frequency sample minimize

```text
(|S11| - |S11_target|)^2 + (|S21| - |S21_target|)^2
```

and average over the frozen grid.

The response derivative uses the exact identity

```text
d A^-1 / dm = -A^-1 (dA/dm) A^-1
```

for one reciprocal symmetric edge stamp. Unit tests must compare the analytic objective gradient with central finite differences before benchmark results are interpreted.

## Frozen optimizer

Use Adam on the three coupling values:

```text
iterations = 800
learning rate = 0.03
beta1 = 0.9
beta2 = 0.999
epsilon = 1e-8
```

Project parameters to the frozen bounds after every step. No learning-rate schedule, random restart, line search, regularizer or post-outcome hyperparameter change is allowed in v0.1.

## Frozen readouts

For every start record:

```text
initial response loss
final response loss
loss reduction factor
final [m12,m23,m13]
parameter RMSE to published target
max |S11| magnitude error
max |S21| magnitude error
iterations
```

Also save the full target and final magnitude responses in the JSON artifact so the result can be plotted later without rerunning optimization.

## Frozen pass criterion

Call the published tuning benchmark a **PASS** only if all five detuned starts satisfy all of:

```text
final response loss <= 1e-5
loss reduction factor >= 1e3
parameter RMSE <= 0.02
max |S11| magnitude error <= 0.02
max |S21| magnitude error <= 0.02
```

and the analytic-gradient finite-difference unit test passes.

A stronger **EXACT RECOVERY** label requires all five parameter RMSE values <= 0.005.

## Frozen decision

- **PASS / exact recovery:** promote coupling-matrix tuning to a first-class TWC application layer. Next add resonator self-detuning parameters and a larger published filter with a prescribed transmission-zero topology.
- **Response pass but parameter recovery fail:** preserve the tuning result but diagnose coupling-matrix gauge/non-uniqueness before claiming physical knob recovery.
- **Fail:** do not change the published target or hand-pick a friendlier start. Diagnose the optimizer/gradient convention on these spent starts first.

This benchmark is independent of the TW-1A on-device learning claim. It is explicitly testing whether the compiler's sparse symmetric-operator machinery has value as an ordinary computer-aided resonator tuning tool.
