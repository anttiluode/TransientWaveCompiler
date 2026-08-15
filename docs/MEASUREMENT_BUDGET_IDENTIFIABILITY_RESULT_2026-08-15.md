# Measurement-budget identifiability gate — result

Date: 2026-08-15  
Status: **positive engineering result / not a topology-recovery benchmark**

Gate:

- `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_GATE_2026-08-15.md`

Implementation:

- `experiments/measurement_budget_identifiability_gate.py`
- `.github/workflows/measurement-budget-identifiability.yml`

GitHub Actions:

```text
run       31895366566
artifact  9249649287
```

All frozen monotonicity/projection guards passed.

---

# What was tested

The experiment stayed in TWC's native swept-frequency reciprocal coupling-matrix model.

It used:

```text
published TARGET_VALUES
existing OMEGA imported by v0.7
existing four-state schedule:
  BASE
  R1_UP    known d1=+0.080
  R2_DOWN  known d2=-0.070
  R4_UP    known d4=+0.060
loss = 0.020
all eight absent reciprocal edges
S11, S21, and joint S11+S21 routes
```

For candidate derivative `g_S` and fitted physical+nuisance tangent `J_S`, the measured scalar was

```text
I_c(S) = min_beta ||g_S - J_S beta||^2.
```

Under equal white noise this is conditional Fisher information up to the noise variance. It is the squared residual already implicit in TWC's existing novelty score.

The two exact static gauge aliases were fixed independently by the pre-existing topology capability map:

```text
(0,3)   R1 <-> R3 realization rotation
(2,5)   R2 <-> R4 realization rotation
```

---

# 1. The exact aliases calibrate correctly in BASE

Joint S11+S21 BASE information fractions of raw candidate sensitivity:

```text
(0,3)   1.07e-29
(2,5)   7.72e-30
```

Numerically zero, as required by the exact static gauge.

The six non-gauge absent edges are already strongly identifiable in BASE, with conditional-information fractions of raw sensitivity ranging roughly from 0.61 to 0.99.

This is calibration, not a new finding.

---

# 2. The predicted physical anchor states carry essentially all new information

## Gauge candidate `(0,3)`

Joint S11+S21 conditional information:

```text
BASE                                  7.81e-27
BASE + R1_UP                          5.80947
+ R2_DOWN                             5.81082
+ R4_UP                               5.81149
```

Full-protocol residual-information allocation by state:

```text
BASE          0.0087%
R1_UP        99.9740%
R2_DOWN       0.0087%
R4_UP         0.0087%
```

The topology-gauge map predicted that `(0,3)` frees an R1<->R3 rotation and that known R1 or R3 detuning should anchor it.

The finite-budget calculation says almost all newly unique response information in the actual v0.7 schedule comes from the **R1_UP** state.

## Gauge candidate `(2,5)`

Joint S11+S21 conditional information:

```text
BASE                                  5.48e-27
BASE + R1_UP                          9.53e-27
+ R2_DOWN                             3.13637
+ R4_UP                               5.43938
```

Full residual allocation:

```text
BASE          0.2860%
R1_UP         0.2862%
R2_DOWN      57.1073%
R4_UP        42.3205%
```

The topology-gauge map predicted that `(2,5)` frees an R2<->R4 rotation and that known R2 or R4 detuning should anchor it.

That is exactly where the conditional information appears.

This is the strongest result of the gate.

---

# 3. Non-gauge controls do not show this anchor specificity

For every non-gauge absent edge, the four full-protocol residual state fractions are close to 25% each.

Examples:

```text
(0,2)   24.98, 25.00, 25.03, 24.99 %
(0,4)   25.01, 25.04, 24.96, 24.99 %
(1,3)   25.02, 24.95, 25.01, 25.03 %
(3,5)   25.10, 25.08, 24.83, 24.99 %
```

Thus the anchor concentration is not a generic artifact of stacking more measurement states.

It is specific to the two directions that were structurally invisible in BASE.

---

# 4. Channel choice is strongly candidate dependent

Absolute final conditional information with one channel versus both channels varies substantially.

Examples:

```text
candidate   S11 / joint I_c    S21 / joint I_c

(0,2)           0.938              0.059
(0,4)           0.355              0.616
(1,3)           0.704              0.278
(2,4)           0.560              0.393
(3,5)           0.877              0.095
```

So an acquisition tool that knows which candidate direction matters can make a real route/channel choice.

For the two gauge aliases, joint S11+S21 is especially useful:

```text
(0,3)
I_s11   = 3.7550
I_s21   = 1.3052
I_joint = 5.8115

(2,5)
I_s11   = 2.9404
I_s21   = 1.6870
I_joint = 5.4394
```

`I_joint` is larger than `I_s11 + I_s21` because the shared compensating physical parameters must explain both channels simultaneously. Two separately ambiguous views can constrain the common compensation when taken together.

That is a concrete multi-readout benefit, not merely duplicated energy.

---

# 5. Frequency targeting is possible but not magical

The existing imported `OMEGA` contains 1189 numerical rows spanning -30 to +30, with a denser central region inherited from the published benchmark construction.

Fixed-full-fit residual energy is not concentrated in a dozen magic bins.

Number of frequency rows carrying 90% of the fixed residual energy ranged from about:

```text
265 to 573 of 1189
```

across the eight candidates.

After **re-fitting the physical+nuisance compensation on the reduced frequency set**, the top-residual ordering recovered the following fractions of full conditional information at 512 rows:

```text
(0,2)   0.744
(0,3)   0.909
(0,4)   0.843
(1,3)   0.911
(1,5)   0.829
(2,4)   0.992
(2,5)   0.990
(3,5)   0.989
```

At 256 rows the range is much broader, roughly 0.39 to 0.83.

So frequency selection looks like a candidate-specific **moderate compression opportunity**, not the main discovery.

Important caveat: the ordering is an oracle diagnostic derived from the full candidate residual. A production selector needs its own model/noise-aware design rule and should be validated independently.

Also, frequency-row counts refer to this existing benchmark grid. They are not yet VNA point-count recommendations.

---

# 6. What the gate added beyond the existing novelty scalar

The old full-window scalar could say:

```text
candidate (0,3) novelty ~ 0.0445
candidate (2,5) novelty ~ 0.0438
```

That correctly says both are weak after the four-state schedule.

The measurement-budget decomposition additionally says:

```text
(0,3)
    BASE impossible
    R1_UP supplies essentially all gauge-breaking information
    R2_DOWN / R4_UP add almost nothing for this direction

(2,5)
    BASE and R1_UP remain impossible
    R2_DOWN opens the direction
    R4_UP adds the remaining independent information
```

That changes an experiment-design decision.

Therefore the gate passes its engineering usefulness criterion.

---

# 7. The practical TWC object

For a proposed candidate direction, TWC can now in principle report:

```text
STRUCTURAL STATUS
    exact static gauge? yes/no

BASE CAPABILITY
    conditional information under current measurement

PERTURBATION MAP
    which known physical state creates unique information

CHANNEL MAP
    which measured channel carries the candidate information
    and whether joint channels add complementary constraints

FREQUENCY BUDGET
    where the residual signal lives
    and how much conditional information survives a reduced sweep
```

That suggests a future command/report closer to:

```text
candidate (2,5)

BASE:      structurally aliased
R1_UP:     no useful new information
R2_DOWN:   opens candidate direction
R4_UP:     adds complementary information
channels:  keep both S11 and S21
sweep:     information moderately concentrated; do not collapse to a tiny point set yet
```

This is much more useful than returning a candidate-edge ranking with false physical confidence.

---

# 8. What remains unearned

This run uses a nominal model point and equal uncorrelated noise weighting.

Before hardware/product claims:

1. replace identity noise weighting with covariance estimated from repeated sweeps;
2. repeat at fitted/noisy model points, not only the published target;
3. test whether a capability-guided state/channel schedule improves the existing v0.7 recovery failures;
4. treat frequency-subset design as a separate gate;
5. preserve exact-gauge negative capability even if an optimizer happens to return a literal edge label.

The result does **not** establish absolute hardware detectability or topology recovery success.

---

## Verdict

> **PASS as an engineering extension.** The finite-measurement information geometry does something the existing full-sweep novelty scalar does not: it localizes *which physical perturbation and which readout channel create the information needed to distinguish a candidate direction*. The two exact aliases provide unusually clean controls because the predicted gauge-breaking coordinates are exactly where the measured conditional information appears.
