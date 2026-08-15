# TransientWaveCompiler — CURRENT HANDOFF

**Updated:** 2026-08-15  
**Active branch:** `agent/tw1a-common-diff-v08`  
**Status:** a new measurement-capability primitive has passed a synthetic engineering gate. Do not confuse this with a new observability theorem or with topology recovery success.

## Read first

1. `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_RESULT_2026-08-15.md` — strongest current result.
2. `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_GATE_2026-08-15.md` — frozen gate that produced it.
3. `docs/FINITE_HORIZON_CAPABILITY_BRIDGE_2026-08-15.md` — Dig/TWC mathematical bridge and prior-art boundary.
4. `docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md` — exact realization-gauge map that predicted which physical anchors should break the two aliases.
5. `docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md` — previous noisy topology-recovery result and the reason this capability work exists.
6. `transientwave/measurement_capability.py` — reusable model-agnostic primitive added after the gate.
7. `experiments/measurement_budget_identifiability_gate.py` — published-filter consumer / receipt-generating experiment.

Cross-project origin:

- `anttiluode/Dig/DISCRIMINATION_CLOCK_RECEIPT.md`
- `anttiluode/Dig/OBSERVABILITY_CLOCK_COLLISION.md`

Do **not** import Clockfield/GeometricNeuron claims from those repos. Only the ordinary measurement-information object is reused here.

---

# Where TWC was before this bridge

TWC had already learned the hard distinction:

```text
large response sensitivity
!=
unique physical identifiability.
```

`transientwave/identifiability.py` measures local novelty of one proposed hidden physical derivative `g` after projecting away the fitted physical+nuisance tangent `J`:

```text
eta = ||(I-P_J) g|| / ||g||.
```

Separately, `topology_gauge.py` / the capability map identify exact reciprocal realization directions that external response cannot label uniquely without an additional physical anchor.

For the published folded four-pole model the exact static aliases are:

```text
(0,3)   realization rotation mixing R1 <-> R3
(2,5)   realization rotation mixing R2 <-> R4
```

The capability map independently predicted:

```text
(0,3) should be broken by known R1 or R3 detuning
(2,5) should be broken by known R2 or R4 detuning
```

The existing v0.7 noisy four-state topology-recovery benchmark used:

```text
BASE
R1_UP     d1 = +0.080
R2_DOWN   d2 = -0.070
R4_UP     d4 = +0.060
```

and achieved only

```text
13 / 15 = 86.7%
```

below its preregistered 95% gate.

The important lesson was already that **correct physics / gauge breaking does not guarantee practical recoverability under finite noise and conditioning**.

---

# The new scalar

For candidate response derivative `g_S`, fitted physical+nuisance tangent `J_S`, and any declared set of measurement rows `S`, define

```text
I_c(S)
    = min_beta ||g_S - J_S beta||^2
    = ||(I-P_J_S)g_S||^2.
```

Under equal independent Gaussian noise this is conditional Fisher information up to the noise variance.

With measured correlated/heteroscedastic noise, whiten the measurement rows first.

For nested row sets and fixed fitted parameterization:

```text
S1 subset S2
    => I_c(S1) <= I_c(S2).
```

This monotone accumulated information is the practical quantity.

The normalized novelty fraction

```text
eta = sqrt(I_c) / ||g||
```

can move differently because the raw candidate norm changes too.

Reusable implementation:

```text
transientwave/measurement_capability.py

conditional_candidate_information(...)
nested_conditional_information_curve(...)
```

Unit tests cover:

```text
exact alias -> zero information
orthogonal candidate -> all information retained
information_fraction == novelty_fraction^2
no fitted columns -> candidate untouched
nested measurement information is nondecreasing
column-shape validation
```

---

# The positive published-filter gate

GitHub Actions:

```text
measurement-budget-identifiability
run       31895366566
artifact  9249649287
all frozen guards PASS
```

All eight absent reciprocal edges were included; candidates were not selected after looking at results.

## Calibration: aliases really are invisible in BASE

Joint S11+S21 BASE conditional-information fractions of raw sensitivity:

```text
(0,3)    ~1.07e-29
(2,5)    ~7.72e-30
```

Numerical zero as predicted by the exact static gauge.

The six non-gauge absent edges are already strongly conditionally identifiable in BASE.

---

# Strongest result: the predicted anchor coordinates contain the new information

## Candidate `(0,3)`

Cumulative joint S11+S21 information:

```text
BASE                                  ~7.81e-27
BASE + R1_UP                           5.80947
+ R2_DOWN                              5.81082
+ R4_UP                                5.81149
```

Full four-state residual-information allocation:

```text
BASE           0.0087%
R1_UP         99.9740%
R2_DOWN        0.0087%
R4_UP          0.0087%
```

The exact gauge said the ambiguity was an R1<->R3 realization rotation. The actual conditional-information calculation says almost all the unique information appears in the known **R1_UP** anchor state.

## Candidate `(2,5)`

```text
BASE                                  ~5.48e-27
BASE + R1_UP                          ~9.53e-27
+ R2_DOWN                              3.13637
+ R4_UP                                5.43938
```

Residual allocation:

```text
BASE           0.2860%
R1_UP          0.2862%
R2_DOWN       57.1073%
R4_UP         42.3205%
```

Again this matches the independent gauge prediction: the R2<->R4 ambiguity opens specifically under the known R2/R4 anchors, not under irrelevant R1 detuning.

## Non-gauge controls

The other six absent edges allocate roughly one quarter of their residual information to each of the four states.

Therefore the gauge-anchor specificity is not a generic consequence of stacking more states.

---

# Channel selection is also a real capability choice

One-channel final conditional information divided by joint S11+S21 information:

```text
candidate       S11       S21

(0,2)           0.938     0.059
(0,4)           0.355     0.616
(1,3)           0.704     0.278
(2,4)           0.560     0.393
(3,5)           0.877     0.095
```

So different candidate directions genuinely prefer different measured channels.

For the exact aliases:

```text
(0,3)
I_S11    3.7550
I_S21    1.3052
I_joint  5.8115

(2,5)
I_S11    2.9404
I_S21    1.6870
I_joint  5.4394
```

Joint measurement can constrain the shared compensating physical parameters more strongly than treating the channels as independent candidate scores.

This gives `ROUTE / CHANGE CHANNEL` an explicit capability meaning.

---

# Frequency targeting is secondary, not the headline

The existing benchmark grid has 1189 numerical rows from the union of broad and central dense sweeps.

The residual information is not concentrated into a dozen magic frequencies:

```text
~265 to 573 rows carry 90% of the fixed full-fit residual energy,
depending on candidate.
```

After re-fitting the compensating tangent on oracle top-residual subsets, 512 rows recover about 74--99% of full conditional information depending on candidate; 256 rows are much less consistent.

Conclusion:

```text
perturbation/state selection   STRONG result
channel selection              STRONG/USEFUL result
frequency compression          plausible, moderate, separate future gate
```

Do not turn current frequency-row counts into VNA point-count recommendations.

---

# What TWC can now plausibly become

The useful output is no longer merely:

```text
candidate hidden edge score = 0.044
```

It can become a measurement capability report:

```text
candidate (2,5)

STRUCTURAL STATUS
    BASE has exact realization gauge

PERTURBATION
    R1_UP       does not open the direction
    R2_DOWN     opens it
    R4_UP       adds complementary information

CHANNEL
    both S11 and S21 useful

FREQUENCY BUDGET
    moderately distributed; do not use a tiny targeted sweep yet

ACTION
    if this candidate distinction matters, acquire an R2/R4 anchored state;
    more BASE data cannot solve the exact gauge.
```

This is an engineering/product direction: a **measurement compiler / capability auditor**, not a theorem generator.

---

# Prior-art boundary

The following are established mathematics and are **not** TWC novelty claims:

```text
observability Gramians
Fisher information
conditional information after nuisance projection
sensor / experiment design
sequential acquisition / stopping
```

The possibly useful software integration is narrower:

> **Combine exact topology-gauge impossibility, nuisance-aware reciprocal response sensitivities, and finite-measurement conditional information into one report that recommends acquire / channel / perturb / stop instead of over-identifying a literal physical topology.**

---

# What remains unearned

The positive gate was evaluated at the published nominal model with identity/equal-white-noise weighting.

It does **not** establish:

```text
absolute hardware detectability
robustness to fitted-point error
robustness to correlated VNA noise
improved topology recovery
hardware savings
universal optimal perturbation schedules
```

---

# Immediate next kill gate

Do **not** build a polished UI yet.

The next question is whether the clean perturbation prescription survives realistic model error/noise.

Use the existing v0.7 noisy-trial machinery rather than inventing another benchmark.

For each noisy trial / fitted stage-1 point:

1. compute the conditional-information allocation for all eight absent candidates at the **fitted** point, not TARGET_VALUES;
2. preserve the independently known gauge labels only for evaluation, not selection;
3. ask whether `(0,3)` still assigns most useful gauge-breaking information to R1_UP and `(2,5)` to R2_DOWN/R4_UP;
4. compare candidate/channel/state recommendations across seeds;
5. ideally whiten with an estimated noise covariance if repeated-noise samples already exist; otherwise keep identity weighting and label it explicitly;
6. then test whether a capability-guided reduced state/channel schedule preserves or improves the existing full v0.7 topology decision.

### Kill branch

If fitted-point/noisy recommendations are unstable or frequently route to the wrong anchor/channel, keep the nominal capability report as an explanatory diagnostic only and do not call it a measurement compiler.

### Survive branch

If the anchor/channel prescription is stable across noisy fitted points, promote it to a reusable capability API and run a preregistered recovery/cost comparison against the full v0.7 schedule.

---

# Clockfield / GeometricNeuron boundary

This branch was reached through Dig after old Clockfield/GeometricNeuron intuitions about spectra, phase, magnitude, receiver and horizon were stripped down by kill gates.

What TWC imports is only:

```text
measurement/readout induces an information geometry over alternatives;
additional independent measurements add information;
different routes/perturbations expose different directions.
```

Do not claim:

```text
state-dependent spacetime
black-hole horizons
Connes spectral distance
new entropy physics
biological neuron mechanisms
```

The fact that an old metaphor led to a useful engineering quantity does not validate the metaphor.

---

## One-line state

> **TWC now has a measured path from 'this topology is not identifiable' to 'here is the physical perturbation and readout that create the missing conditional information.' The next job is to see whether that prescription survives noisy fitted points and actually reduces measurement cost or recovery failure.**
