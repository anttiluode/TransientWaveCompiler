# Gate — noisy fitted-point measurement capability

**Frozen:** 2026-08-15, before reading the other fourteen stage-1 fitted points.  
**Status:** robustness/engineering gate.

## Question

The nominal published-target calculation found that conditional candidate information for the two exact static topology gauges appears specifically in the independently predicted anchor states:

```text
(0,3)   R1 <-> R3 gauge   -> R1_UP in the existing schedule
(2,5)   R2 <-> R4 gauge   -> R2_DOWN and R4_UP
```

Does that prescription survive the **actual noisy wrong-topology fitted points** from the already-run v0.7 benchmark?

This gate reuses the exact fifteen frozen v0.7 artifacts from Actions run `31359232293`. It does not regenerate noise or re-fit the model.

---

# Frozen panel

The original workflow had:

```text
starts   A, C, D
cases    4400..4404
15 total fitted cells
```

Case truths were frozen independently by v0.7:

```text
4400  hidden (2,5)  -0.032
4401  hidden (1,5)  +0.028
4402  hidden (0,3)  -0.026
4403  hidden (3,5)  +0.033
4404  hidden (0,4)  -0.022
```

For each artifact use only:

```text
stage1_wrong_topology.shared_matrix_values
stage1_wrong_topology.state_nuisance_values
```

to define the linearized capability point.

The truth hidden edge is evaluation metadata only. It must not alter which candidate directions are evaluated.

Evaluate **all eight absent reciprocal edges** at every fitted point.

---

# Fitted-point tangent

For each state, reconstruct the wrong-topology matrix from the fitted seven shared physical values plus the known fixed state detuning.

Use that state's fitted nuisance values exactly:

```text
lambda, phi11, tau11, phi21, tau21
```

Physical and candidate response derivatives are multiplied by the fitted channel reference-plane phases.

Nuisance tangent columns are the exact local derivatives already implied by `measurement_aware_filter.py`:

```text
d/dlambda
d/dphi11 = i y11
d/dtau11 = i omega y11
d/dphi21 = i y21
d/dtau21 = i omega y21
```

The fitted physical parameters are shared across states; nuisance parameters remain state-specific.

No parameter is re-optimized by this gate except the linear least-squares compensation intrinsic to conditional-information calculation.

---

# Core quantity

For each candidate and row set `S`:

```text
I_c(S) = min_beta ||g_S - J_S beta||^2.
```

Identity/equal-white-noise weighting is retained because the old artifacts contain fitted points, not an empirical covariance estimate. Therefore this is a **conditioning robustness test**, not an absolute detectability calculation.

---

# Frozen state-allocation tests

For both gauge candidates use joint S11+S21.

## Calibration: BASE must remain structurally dark

At every fitted point require

```text
I_c(BASE) / ||g_BASE||^2 < 1e-10
```

for `(0,3)` and `(2,5)`.

Failure means the numerical tangent implementation is no longer reproducing the independently established static gauge and invalidates the robustness interpretation.

## `(0,3)` anchor consistency

On the full four-state residual, define

```text
anchor_fraction_03 = residual energy in R1_UP / total residual energy.
```

A fitted cell counts as **anchor-consistent** only if:

```text
R1_UP is the largest individual state contribution
and
anchor_fraction_03 >= 0.80.
```

## `(2,5)` anchor consistency

Define

```text
anchor_fraction_25 = (R2_DOWN + R4_UP residual energy) / total.
```

A cell is anchor-consistent only if:

```text
largest individual state is R2_DOWN or R4_UP
and
anchor_fraction_25 >= 0.80.
```

## Primary robustness pass rule

The nominal `measurement compiler` interpretation survives only if **both** gauge candidates are anchor-consistent in at least

```text
12 / 15 fitted cells.
```

This threshold was frozen before inspecting the remaining fourteen fitted points.

---

# Cumulative opening diagnostic

For every fitted point report conditional information on:

```text
BASE
BASE + R1_UP
BASE + R1_UP + R2_DOWN
all four states
```

and the fraction of raw candidate sensitivity retained after compensation.

This is descriptive. The anchor-allocation criterion above is primary because the cumulative schedule order is inherited from v0.7 rather than optimized for each candidate.

---

# Channel stability

For every candidate at every fitted point compute final four-state conditional information for:

```text
S11 only
S21 only
joint S11+S21
```

For each candidate report:

```text
modal better single channel
fraction of 15 fits agreeing with that modal route
median I_S11/I_joint
median I_S21/I_joint
```

No channel-stability threshold is part of the primary pass rule. This is a secondary product diagnostic.

---

# Non-gauge controls

For the six non-gauge absent edges report across fitted points:

```text
median and range of four state residual fractions
BASE information fraction of raw sensitivity
```

The nominal experiment found roughly equal ~25% state allocations. The noisy gate does not require exact equality; it checks whether gauge-anchor concentration remains qualitatively distinct from ordinary candidate directions.

---

# Relation to the two v0.7 recovery failures

After all capability quantities have been computed, label cells by the old v0.7 discovery outcome:

```text
selected_edge_is_true / true_edge_rank
```

and report the capability values for the failed cells separately.

This is post-hoc explanatory analysis of an already frozen benchmark. Do not use the old failure labels to tune thresholds or candidate selection.

---

# Interpretation branches

## PASS

If both aliases pass >=12/15 anchor consistency and BASE calibration passes in all cells:

> The nominal topology-gauge-to-perturbation prescription is robust to the wrong-topology fitted-point distortions produced by the original noisy benchmark.

This earns a subsequent **cost/recovery** gate where TWC actually chooses a reduced perturbation/channel schedule and is compared against the full v0.7 protocol.

## FAIL / DOWNGRADE

If either alias is anchor-consistent in <12/15 cells:

> The nominal capability map is explanatory at the ideal model point but not stable enough under fitted-point error to act as a measurement compiler.

Do not tune the 0.80 or 12/15 rules after the run.

---

# What this still cannot establish

Even a pass does not establish:

```text
hardware detectability
noise-optimal experiment design
improved topology recovery
cost savings
robustness beyond this synthetic benchmark family
```

Those require the next independent gate.
