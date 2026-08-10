# Published filter multi-state topology diagnosis v0.7 — preregistration

Date: 2026-08-10

Status: **PREREGISTERED BEFORE OUTCOME INSPECTION**

## Why this gate exists

The v0.6 single-state missing-edge experiment failed its primary discovery clause. Four of five hidden-edge locations were recovered perfectly, but hidden `(2,5)=-0.025` ranked `8,8,7` after the knowingly wrong topology had compensated by moving its allowed matrix and nuisance variables.

A post-hoc, non-qualifying microscope then gave every candidate edge a full same-state refit. The true edge still ranked only `7,5,3`, with several wrong candidate models reaching nearly indistinguishable final losses.

The next test therefore changes the **information available**, not just the optimizer.

The same hidden reciprocal device is measured in several deliberately known resonator-detuning states. The hidden base matrix/topology is shared across all states; the controlled diagonal perturbations are known and fixed; measurement nuisance may vary by state.

This is not claimed as a new general concept. Deliberate detuning/perturbation for parasitic-coupling localization exists in microwave-filter prior art. The question here is narrower: whether TWC's direct-response exact-sensitivity formulation can use multiple known states to repair the specific compensated-model ambiguity exposed by v0.6.

## Fixed published base model

Use the same six-node explicit source–four-resonator–load matrix and seven declared trainable entries as v0.3–v0.6:

```text
mS1  (0,1)   +1.0200
m12  (1,2)   -0.8600
m23  (2,3)   +0.7700
m34  (3,4)   -0.8600
m4L  (4,5)   +1.0200
m14  (1,4)   -0.1900
mSL  (0,5)   +0.0005
```

The stage-1 fitter does not know the hidden parasitic edge.

Use the existing published-filter frequency grid, base matrix bounds, and optimizer starts `A`, `C`, `D`.

## Fresh hidden cases

The v0.7 outcome cells use new case IDs, strengths, and measurement-noise realizations. One case intentionally revisits the difficult load-side edge class from v0.6, but with a new hidden strength and completely fresh measurements.

```text
case 4400   hidden edge (2,5)   -0.032
case 4401   hidden edge (1,5)   +0.028
case 4402   hidden edge (0,3)   -0.026
case 4403   hidden edge (3,5)   +0.033
case 4404   hidden edge (0,4)   -0.022
```

Across starts `A`, `C`, `D` this gives 15 frozen cells.

## Known physical perturbation states

Every hidden physical device is observed in the same four states:

```text
state BASE      no added diagonal perturbation
state R1_UP     add d1 = +0.080 at resonator node 1
state R2_DOWN   add d2 = -0.070 at resonator node 2
state R4_UP     add d4 = +0.060 at resonator node 4
```

These additional diagonal stamps are **known exactly to the fitter** and are not trainable.

The shared unknown physical parameters are the seven base matrix entries and, after topology selection, one candidate hidden reciprocal edge.

## State-specific measurement nuisance

Every state has the same physical normalized resonator loss truth:

```text
lambda = 0.020
```

but is fitted independently per state together with its own:

```text
phi11, tau11, phi21, tau21.
```

For implementation simplicity and to avoid granting the estimator extra knowledge, the global optimizer carries all five nuisance variables independently for every state. Thus even the common true loss is not constrained to be shared.

Frozen phase settings are generated deterministically from `(case_id, state_index)` before measurement noise is added, with magnitudes kept inside the same broad v0.5 bounds:

```text
phase offsets within approximately +/-12 degrees
phase slopes within +/-0.050 per normalized Omega
```

The exact deterministic values are written into each result JSON.

Measurement noise remains:

```text
0.5% RMS pointwise amplitude noise
0.5 degree RMS pointwise phase noise
8 complex sweeps averaged independently per state
```

Noise RNG is derived only from the frozen case/state identifiers and does not depend on optimizer start.

## Stage 1 — multi-state knowingly wrong topology fit

Fit one shared seven-knob base matrix to all four states while fitting five nuisance variables independently per state:

```text
7 shared physical variables
+ 4 states * 5 nuisance variables
= 27 variables
```

The known diagonal perturbation for each state is inserted into that state's forward model but is not optimized.

Use:

```text
iterations = 3000
learning rate = 0.010
matrix bounds = frozen v0.3 bounds
lambda bounds = [0.000, 0.080] independently per state
phase offset bounds = [-pi/2, +pi/2]
phase slope bounds = [-0.10, +0.10]
```

The objective is the mean complex-response MSE across all four states.

## Stage 2 — multi-state absent-edge score

At the completed stage-1 solution, hold the shared wrong-topology matrix and all fitted state nuisance fixed.

Enumerate every absent off-diagonal reciprocal edge. For each candidate edge `c`, shared across all states:

1. compute the exact complex response derivative `dy_s/dc` in each known physical state;
2. average residual gradient and Gauss-Newton curvature across states;
3. propose one shared bounded edge value

```text
c_probe = clip(-g/h, -0.12, +0.12);
```

4. evaluate the candidate with that same shared value in all four states;
5. rank candidates by the actual mean four-state probe loss.

No candidate-specific optimizer or second-ranked rescue is allowed before the ranking is frozen.

## Stage 3 — top-1 augmented multi-state refit

Append only the stage-2 top-ranked edge to the shared physical matrix and initialize it at the stage-2 probe value.

Jointly refit:

```text
8 shared physical variables
+ 4 states * 5 nuisance variables
= 28 variables
```

for 3000 Adam iterations at learning rate `0.010`.

The candidate-edge bound is `[-0.12,+0.12]`. The original seven physical values and four nuisance blocks start from the stage-1 solution.

The selected edge cannot be swapped for a second-ranked edge after fitting.

## Recorded outcomes

Per cell record at least:

- hidden edge and strength;
- known state perturbations;
- exact state nuisance truths;
- stage-1 shared seven-knob matrix RMSE;
- stage-1 mean measured loss;
- complete absent-edge ranking;
- true-edge rank;
- selected probe value;
- stage-3 shared base-matrix RMSE;
- recovered selected-edge value/error;
- nuisance errors for every state;
- mean hidden clean systematic response MSE across states;
- measured-loss reduction stage 1 -> stage 3.

## Frozen discovery clauses

Per cell:

```text
DISCOVERY_TOP1 := true hidden edge ranked #1
DISCOVERY_TOP3 := true hidden edge ranked in top 3
```

Primary discovery pass:

```text
TOP1 >= 12/15
AND
TOP3 = 15/15.
```

## Frozen recovery clause

Per cell:

```text
selected edge is the true edge
shared base seven-knob matrix RMSE       <= 0.010
parasitic absolute-value error           <= 0.005

for every state:
    lambda absolute error                <= 0.0075
    S11 phase-offset wrapped error       <= 3 degrees
    S21 phase-offset wrapped error       <= 3 degrees
    S11 phase-slope absolute error       <= 0.0075
    S21 phase-slope absolute error       <= 0.0075

mean hidden clean systematic response MSE <= 5e-5
stage-3 mean measured fit loss             < stage-1 mean measured fit loss
```

The nuisance thresholds are slightly wider than v0.6 because each state now has an independently fitted five-variable nuisance block.

Primary recovery pass:

```text
RECOVERY >= 12/15.
```

## Strong label

Only if

```text
DISCOVERY_TOP1 = 15/15
RECOVERY       = 15/15
```

may the result be labeled:

> **15/15 MULTI-STATE TOPOLOGY DIAGNOSIS AND RECOVERY**

## Interpretation boundary

Passing v0.7 would not establish arbitrary graph reconstruction and would not establish novelty of perturbation-aided parasitic localization.

It would establish a narrower TWC result:

> a compensated single-state ambiguity that defeated the v0.6 direct residual estimator can be reduced by jointly evaluating the same shared reciprocal topology across several known physical perturbation states, even while each state is allowed its own measurement nuisance.

Failure would also be useful. If the difficult load-side case remains ambiguous across these four states, then this particular perturbation schedule is insufficient and topology diagnosis should remain a deliberately perturbed physical experiment rather than a software-only inference claim.
