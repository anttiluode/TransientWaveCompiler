# Published filter parasitic-topology discovery v0.6 — preregistration

Date: 2026-08-10

Status: **PREREGISTERED BEFORE OUTCOME INSPECTION**

## Question

The v0.5 tuner assumes the declared reciprocal topology is correct. This benchmark deliberately violates that assumption by adding one weak hidden reciprocal coupling that is absent from the declared seven-knob published matrix.

The test asks two separate questions:

1. After fitting the wrong declared topology together with the already-qualified measurement nuisance, does the remaining complex residual identify the **correct missing reciprocal edge**?
2. If the top-ranked edge is added, can a joint refit recover the intended seven-knob matrix, the parasitic strength, and the measurement nuisance?

This is a topology-diagnosis test, not another clean parameter-recovery test.

## Fixed published base model

Use the same six-node explicit source–four-resonator–load matrix and seven declared trainable entries as v0.3–v0.5:

```text
mS1  (0,1)   +1.0200
m12  (1,2)   -0.8600
m23  (2,3)   +0.7700
m34  (3,4)   -0.8600
m4L  (4,5)   +1.0200
m14  (1,4)   -0.1900
mSL  (0,5)   +0.0005
```

The declared fitter does **not** know the parasitic edge during stage 1.

Frequency grid, matrix bounds, Adam beta values, and starts `A`, `C`, `D` remain the same as the existing published-filter experiments.

## Frozen hidden parasitic cases

Five physically small absent reciprocal edges are frozen before running outcomes:

```text
case 4300   hidden edge (0,2)   +0.030
case 4301   hidden edge (1,3)   -0.040
case 4302   hidden edge (2,4)   +0.035
case 4303   hidden edge (2,5)   -0.025
case 4304   hidden edge (0,4)   +0.020
```

These are not members of the declared v0.3 seven-edge topology.

Across three starts this gives 15 frozen cells.

## Frozen measurement corruption

Every hidden physical target also contains the already-qualified v0.5 nuisance model:

```text
uniform normalized resonator loss lambda = 0.020
unknown S11 phase offset + linear phase slope
unknown S21 phase offset + linear phase slope
0.5% RMS pointwise amplitude noise
0.5 degree RMS pointwise phase noise
8 complex sweeps averaged pointwise
```

The five phase settings are frozen one-to-one with cases 4300..4304:

```text
4300  phi11= +5 deg   tau11=+0.020   phi21= -7 deg   tau21=-0.015
4301  phi11= -9 deg   tau11=+0.035   phi21= +4 deg   tau21=-0.025
4302  phi11=+12 deg   tau11=-0.030   phi21=-11 deg   tau21=+0.040
4303  phi11= -6 deg   tau11=-0.045   phi21=+10 deg   tau21=+0.030
4304  phi11= +8 deg   tau11=+0.050   phi21= -5 deg   tau21=-0.045
```

Noise RNG is derived only from the case id and is identical across starts for a given physical/measurement case.

## Stage 1 — knowingly wrong declared-topology fit

Fit only the original seven matrix knobs plus

```text
lambda, phi11, tau11, phi21, tau21
```

for 12 variables total.

Use:

```text
iterations = 3000
learning rate = 0.010
matrix bounds = frozen v0.3 bounds
lambda bounds = [0.000, 0.080]
phase offset bounds = [-pi/2, +pi/2]
phase slope bounds = [-0.10, +0.10]
```

The stage-1 fit is allowed to distort declared matrix and nuisance values. That distortion is part of the test: the parasitic edge is intentionally absent from its model.

## Stage 2 — residual-driven absent-edge score

Enumerate every absent off-diagonal reciprocal edge in the six-node matrix.

At the completed stage-1 solution, hold the fitted declared matrix and nuisance fixed. For each absent edge `c`:

1. compute the exact complex response derivative `dy/dc` at `c=0`;
2. compute residual gradient `g`;
3. use Gauss-Newton curvature `h` to propose

```text
c_probe = clip(-g/h, -0.12, +0.12);
```

4. evaluate that probe response exactly;
5. rank candidates by actual probe loss, lowest first.

No candidate-specific tuning is allowed before the ranking is frozen.

## Stage 3 — augmented joint refit

Take the **top-1 ranked edge only**, append it to the physical matrix, initialize it at its stage-2 probe value, and jointly refit:

```text
8 physical matrix variables
+ lambda
+ phi11, tau11
+ phi21, tau21
= 13 variables
```

Use 3000 Adam iterations at learning rate 0.010. The added edge bound is `[-0.12,+0.12]`. Existing physical/nuisance variables start at the stage-1 fitted values.

This stage does not get to try the second-ranked edge if the top-1 choice is wrong.

## Per-cell recorded outcomes

Record at least:

- hidden edge and hidden strength;
- full candidate ranking;
- true-edge rank;
- top-1 proposed value;
- stage-1 matrix RMSE and residual loss;
- stage-3 base seven-knob matrix RMSE;
- recovered parasitic edge/value and absolute error;
- nuisance errors;
- hidden clean systematic response MSE;
- measured residual reduction from stage 1 to stage 3.

## Frozen clauses

### Discovery clause

Per cell:

```text
DISCOVERY_TOP1 := true hidden reciprocal edge is ranked #1.
DISCOVERY_TOP3 := true hidden reciprocal edge is ranked in top 3.
```

Aggregate primary discovery pass:

```text
TOP1 >= 12/15
AND
TOP3 = 15/15.
```

### Recovery clause

Only meaningful when stage 3 uses the selected top-1 edge. Per cell:

```text
base seven-knob matrix RMSE          <= 0.010
selected edge is the true edge
parasitic absolute-value error       <= 0.005
lambda absolute error                <= 0.005
S11 phase-offset wrapped error       <= 2 degrees
S21 phase-offset wrapped error       <= 2 degrees
S11 phase-slope absolute error       <= 0.005
S21 phase-slope absolute error       <= 0.005
hidden clean systematic response MSE <= 5e-5
stage-3 measured fit loss             < stage-1 measured fit loss
```

Aggregate primary recovery pass:

```text
RECOVERY >= 12/15.
```

### Strong label

Only if both are true:

```text
DISCOVERY_TOP1 = 15/15
RECOVERY       = 15/15
```

may the result be labeled:

> **15/15 PARASITIC TOPOLOGY DISCOVERY AND RECOVERY**

## Interpretation boundary

Passing this benchmark would not establish arbitrary graph reconstruction. It would establish a narrower and practically useful capability:

> starting from a mostly correct reciprocal filter topology, one weak missing reciprocal edge can leave a structured complex residual whose exact sensitivity points back to the omitted physical coupling, even in the presence of the already-tested loss/reference-plane nuisance and measurement noise.

Failure is also informative. In particular, if the true edge is consistently top-3 but not top-1, the local single-edge probe is useful as a shortlist but not yet an automatic topology diagnosis. If rankings collapse across nuisance/noise, then a stronger conditional-refit or model-selection method is required.
