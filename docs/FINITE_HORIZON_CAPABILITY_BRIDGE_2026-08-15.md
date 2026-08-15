# Finite-horizon / finite-measurement capability bridge

Date: 2026-08-15  
Status: **cross-project engineering bridge; first native-domain gate passed**

This note imports one conservative object from `anttiluode/Dig` into the active TWC line.

It does **not** claim a new observability theorem, a new Fisher-information construction, or a new experiment-design principle.

The practical question is:

> TWC already asks whether a measurement can distinguish a physical candidate from fitted model/nuisance directions. Can the same capability audit be made explicitly dependent on **measurement budget** — samples, channels, and perturbation states?

TWC's current published-filter model is natively frequency-domain, so the first executable gate stayed in that domain rather than manufacturing a time axis with a band-limited IFFT.

---

## Existing TWC capability layers

### Exact topology gauge

`topology_gauge.py` asks whether opening a proposed absent coupling re-opens an exact response-equivalent internal realization direction.

For the published folded four-pole topology the two exact static aliases are:

```text
(0,3)   frees R1 <-> R3 rotation
(2,5)   frees R2 <-> R4 rotation
```

The capability map predicts which known resonator detunings break each ambiguity.

### Response-space local identifiability

`identifiability.py` forms a realified response Jacobian `J` and candidate derivative `g`, then reports

```text
eta = ||(I-P_J) g|| / ||g||.
```

This distinguishes raw sensitivity from candidate sensitivity that remains new after the fitted physical+nuisance model has been allowed to compensate.

---

# The candidate-information scalar

For a chosen set of measurement rows `S` — frequencies, channels, perturbation states, or any fixed combination — define

```text
I_c(S)
    = min_beta ||g_S - J_S beta||^2
    = ||(I-P_J_S) g_S||^2.
```

Under equal independent white measurement noise this is conditional Fisher information up to the noise variance. It is the squared residual already implicit in TWC's novelty calculation.

With known measurement covariance, whiten the rows before applying the same construction.

## Monotonicity for nested measurements

For a fixed parameterization,

```text
S1 subset S2  =>  I_c(S1) <= I_c(S2).
```

For every compensation vector `beta`, the larger objective is the old residual plus additional nonnegative row residuals. Taking the minimum preserves the inequality.

The normalized angle-like novelty fraction `eta` need not be monotone because the raw candidate norm also changes. The accumulated conditional information `I_c` is the monotone quantity.

This is the closest TWC analogue of Dig's monotone pairwise discrimination energy.

---

# Structural impossibility versus finite-measurement weakness

```text
STRUCTURAL IMPOSSIBILITY
    exact gauge survives the declared experiment
    candidate conditional information remains zero

FINITE-MEASUREMENT WEAKNESS
    candidate is identifiable in principle
    but the selected states/channels/samples expose little unique information
```

For a frozen full protocol one can define a descriptive acquisition maturity

```text
M_c(S) = I_c(S) / I_c(S_full)
```

when the denominator is nonzero.

This is a measurement-budget bookkeeping quantity, not a new time coordinate.

---

# Native-domain gate actually run

Gate:

- `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_GATE_2026-08-15.md`

Result:

- `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_RESULT_2026-08-15.md`

The run used the existing published target and the exact v0.7 measurement ingredients:

```text
OMEGA imported from published_cross_coupled_filter_v03.py
    np.unique(concatenate([
        linspace(-30,+30,601),
        linspace(-3,+3,601),
    ]))

actual floating-point grid rows in the benchmark: 1189

states:
    BASE
    R1_UP    d1=+0.080
    R2_DOWN  d2=-0.070
    R4_UP    d4=+0.060

channels:
    S11
    S21
    joint S11+S21

candidate panel:
    all eight absent reciprocal edges
```

No candidate subset was selected after seeing the result.

---

# Main result

The two exact static aliases calibrated at numerical zero in BASE.

Then their conditional information appeared almost exclusively in the physical anchor states predicted independently by the topology-gauge calculation.

## `(0,3)`

```text
BASE                                  ~7.8e-27
BASE + R1_UP                           5.8095
+ R2_DOWN                              5.8108
+ R4_UP                                5.8115
```

Full residual-information allocation:

```text
R1_UP       99.974%
all other states combined ~0.026%
```

## `(2,5)`

```text
BASE                                  ~5.5e-27
BASE + R1_UP                          ~9.5e-27
+ R2_DOWN                              3.1364
+ R4_UP                                5.4394
```

Full allocation:

```text
R2_DOWN      57.11%
R4_UP        42.32%
BASE+R1_UP    0.57%
```

The six non-gauge absent-edge controls instead allocate roughly one quarter of their residual information to each state.

Therefore the finite-budget view adds a real experiment-design statement beyond the old full-window novelty scalar:

> **it localizes which known physical perturbation creates the information that breaks an otherwise exact response ambiguity.**

---

# Channel choice also matters

Candidate directions have different readout ceilings.

Examples of one-channel conditional information divided by joint S11+S21 information:

```text
candidate     S11       S21

(0,2)         0.938     0.059
(0,4)         0.355     0.616
(1,3)         0.704     0.278
(2,4)         0.560     0.393
(3,5)         0.877     0.095
```

The two gauge aliases also benefit from joint channels because the same compensating physical parameters must satisfy both responses simultaneously.

So `ROUTE / CHANGE CHANNEL` has a concrete capability meaning here.

---

# Frequency targeting is secondary

The full-fit residual can be localized by frequency, but the first gate did **not** find a tiny set of magic bins.

Across candidates, roughly 265--573 of the existing 1189 benchmark rows carry 90% of the fixed full-fit residual energy.

After re-fitting compensation on reduced frequency subsets, 512 oracle-selected rows recover about 74%--99% of full conditional information depending on candidate; 256 rows give a much broader range.

Thus frequency selection is a plausible candidate-specific compression optimization, not the headline result.

The current row counts are properties of this synthetic benchmark grid and are not VNA point-count recommendations.

---

# Practical report shape

TWC can now plausibly expose a capability report such as:

```text
candidate (2,5)

STATIC STATUS
    exact BASE gauge alias

PERTURBATION
    R1_UP       no useful new information
    R2_DOWN     opens direction
    R4_UP       adds complementary information

CHANNELS
    S11 and S21 complementary; keep both

FREQUENCY BUDGET
    moderate concentration only; do not collapse to a tiny sweep yet
```

This is more useful than returning a literal hidden-edge ranking when the measurement does not support that confidence.

---

# Prior-art boundary

Finite-horizon observability/reachability Gramians, Fisher information, conditional information after nuisance projection, and experiment/sensor design are established mathematics.

TWC should not claim those constructions.

The useful software intersection is narrower:

> **combine topology-gauge impossibility, nuisance-aware reciprocal response sensitivities, and finite-measurement conditional information into one capability report that can recommend acquire / channel / perturb / stop rather than over-identifying a physical topology.**

Next technical requirement before hardware claims: replace identity weighting with covariance estimated from repeated sweeps and test whether capability-guided protocols improve the existing noisy topology-recovery failures.
