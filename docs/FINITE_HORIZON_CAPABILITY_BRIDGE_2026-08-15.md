# Finite-horizon / finite-measurement capability bridge

Date: 2026-08-15  
Status: **cross-project engineering note / prior-art-aware proposal**

This note imports one conservative object from `anttiluode/Dig` into the active TWC line.

It does **not** claim a new observability theorem, a new Fisher-information construction, or a new experiment-design principle.

The practical question is:

> TWC already asks whether a measurement can distinguish a physical candidate from fitted model/nuisance directions. Can the same capability audit be made explicitly dependent on **measurement budget** — samples, channels, and perturbation states?

TWC's current published-filter model is natively frequency-domain. Therefore the first executable gate should stay in that domain rather than manufacture a time axis with a band-limited IFFT.

---

## Existing TWC capability layers

### 1. Exact topology gauge

`topology_gauge.py` asks whether opening a proposed absent coupling re-opens an exact response-equivalent internal realization direction.

If yes, one static external response cannot uniquely label the literal internal edge.

### 2. Response-space local identifiability

`identifiability.py` forms a realified response Jacobian `J` and candidate derivative `g`, then reports

```text
eta = ||(I-P_J) g|| / ||g||.
```

This distinguishes raw sensitivity from candidate sensitivity that remains new after the fitted physical+nuisance model has been allowed to compensate.

The capability-map documentation already points toward whitening the residual by measured sweep covariance for real-data experiment design.

---

# The exact candidate-information scalar

For a chosen set of measurement rows `S` — frequencies, channels, perturbation states, or any fixed combination — let

```text
J_S
```

be the fitted physical+nuisance tangent matrix and

```text
g_S
```

the derivative for one proposed hidden physical parameter.

Under equal independent white measurement noise, define

```text
I_c(S)
    = min_beta ||g_S - J_S beta||^2
    = ||(I-P_J_S) g_S||^2.
```

Up to the noise variance, this is the **conditional Fisher information** for the candidate parameter after the fitted/nuisance parameters are allowed to compensate. It is the squared residual already implicit in TWC's novelty calculation.

With a known whitening operator `W_S^(1/2)`, replace both blocks by their whitened versions:

```text
I_c(S)
  = min_beta || W_S^(1/2) (g_S - J_S beta) ||^2.
```

## Important correction: this quantity is monotone for nested measurement sets

If `S1` is a subset of `S2`, then

```text
I_c(S2) >= I_c(S1).
```

Reason: for every coefficient vector `beta`, the `S2` objective equals the old nonnegative residual on `S1` plus nonnegative residual from the added rows. Taking the minimum cannot make it smaller than the old minimum.

So the earlier warning in this note that the accumulated orthogonal candidate energy might decrease under re-projection was too pessimistic. The **fraction**

```text
eta(S) = sqrt(I_c(S)) / ||g_S||
```

can still move non-monotonically, but the conditional residual energy `I_c(S)` itself is monotone for a fixed parameterization and nested row sets.

This is the closest TWC analogue of Dig's monotone pairwise discrimination energy.

---

# Structural impossibility versus practical immaturity

The existing exact gauge and the finite-measurement scalar now separate two cases cleanly:

```text
STRUCTURAL IMPOSSIBILITY
    exact gauge / exact response-equivalent direction
    I_c(full allowed experiment) = 0 in the ideal model
    more samples of the same experiment cannot help

PRACTICAL IMMaturity / CONDITIONING
    I_c(full allowed experiment) > 0
    but a small measurement subset has accumulated little of it
```

For a frozen full protocol `S_full`, define descriptive candidate maturity

```text
M_c(S) = I_c(S) / I_c(S_full)
```

when the denominator is nonzero.

This is a measurement-budget CDF-like object, not a new probability or time coordinate.

---

# What TWC could report

For each candidate physical direction and declared protocol:

```text
exact gauge alias?                         existing
full-protocol novelty eta                  existing
conditional information I_c(S)            proposed
measurement maturity M_c(S)                proposed
candidate information by channel           proposed
candidate information by perturbation      proposed
frequency localization of residual signal  proposed
best next measurement block                proposed
```

The report can then use ordinary engineering language:

```text
WAIT / ACQUIRE MORE
    current nested measurement is still accumulating useful conditional information

CHANGE CHANNEL
    another measured S-parameter exposes more candidate information

PERTURB
    a known physical state change breaks or weakens an ambiguity

CANNOT RESOLVE
    exact gauge remains under the declared experiment family

STOP
    the requested information fraction has already been captured
```

No novelty claim is made for these decision roles.

---

# First cheap executable gate: stay in TWC's native frequency domain

Do **not** start with a synthetic impulse response.

Use the existing published-filter model exactly where it already lives:

```text
OMEGA = linspace(-2.2, 2.2, 1201)
channels = S11 / S21
v0.7 state schedule:
  BASE
  R1_UP    known d1 = +0.080
  R2_DOWN  known d2 = -0.070
  R4_UP    known d4 = +0.060
```

Frozen candidate classes:

```text
exact-gauge anchors
    (0,3)
    (2,5)

robust non-gauge classes from the capability map
    (0,2)
    (1,4)
    (3,5)
```

At the published target matrix and one frozen nominal loss, build a **shared-physical / state-specific-nuisance** tangent model matching the v0.7 protocol:

```text
shared columns
    q_source, q_load, fitted diagonal/coupling parameters

state-specific nuisance columns
    resonator loss
    S11 phase / delay
    S21 phase / delay
```

The known diagonal perturbation in each state is fixed, not fitted.

For each candidate, compare:

```text
BASE only
BASE + R1_UP
BASE + R1_UP + R2_DOWN
all four states
```

and channel routes:

```text
S11 only
S21 only
S11 + S21
```

## Frequency-budget diagnostic

For the final full-row projection, decompose the squared residual candidate signal by frequency bin. Report:

```text
number/fraction of frequencies carrying 50% and 90% of final residual energy
most informative frequency regions
which state/channel contributes the residual energy
```

Then validate any proposed reduced frequency set by **recomputing** `I_c(S)` on that subset rather than assuming the fixed full-fit residual decomposition remains optimal.

The first gate does not need a noise threshold. It asks only whether the existing full sweep contains a highly concentrated or highly diffuse conditional-information pattern.

---

# Kill conditions

This bridge earns implementation value only if it changes an actual protocol decision beyond the current full-window novelty scalar. For example:

```text
a known perturbation changes an exact/near alias into measurable conditional information;
a channel choice changes the information ceiling substantially;
a small targeted frequency subset recovers most of full-protocol I_c;
or the tool correctly identifies an exact direction for which more of the same measurement cannot help.
```

If all candidates simply acquire information in the same state/channel/frequency proportions and the finite-budget view merely redraws the full-sweep ranking, keep the existing identifiability tools and stop.

---

# Relation to Dig

Dig measured

```text
D_C,T^2(i,j)
    = integral_0^T ||h_i(t)-h_j(t)||^2 dt
```

for alternative source causes under one receiver/readout.

TWC's analogue is parameter-space rather than source-space:

```text
candidate physical direction
        -> response derivative g
fitted/nuisance directions
        -> tangent matrix J
measurement protocol S
        -> conditional information I_c(S)
```

The shared abstraction is simply:

> **A measurement operator induces a finite-budget information geometry over alternatives.**

That is enough. No Geometric-Neuron or Clockfield mechanism is imported.

---

# Prior-art boundary

Finite-horizon observability/reachability Gramians, Fisher information, conditional information after nuisance projection, and experiment/sensor design are established mathematics.

TWC should not claim those constructions.

The potentially useful software contribution is narrower:

> **combine topology-gauge impossibility, nuisance-aware reciprocal response sensitivities, and measurement-budget conditional information into one capability report that can recommend acquire / channel / perturb / stop rather than over-identifying a physical topology.**

That is an engineering hypothesis and needs the executable gate above.
