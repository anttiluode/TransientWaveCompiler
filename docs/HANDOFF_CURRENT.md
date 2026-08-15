# TransientWaveCompiler — CURRENT HANDOFF

**Updated:** 2026-08-15  
**Active branch:** `agent/tw1a-common-diff-v08`  
**Status:** measurement-capability / experiment-design diagnostic has survived both nominal and original noisy fitted-point gates. It has **not** yet earned topology-recovery or hardware claims.

## Read first

1. `docs/NOISY_FITTED_CAPABILITY_RESULT_2026-08-15.md` — strongest current robustness result.
2. `docs/NOISY_FITTED_CAPABILITY_GATE_2026-08-15.md` — frozen 15-cell fitted-point gate.
3. `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_RESULT_2026-08-15.md` — nominal published-filter capability result.
4. `docs/MEASUREMENT_BUDGET_IDENTIFIABILITY_GATE_2026-08-15.md` — its preregistration.
5. `docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md` — independent exact realization-gauge map.
6. `docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md` — frozen old recovery failure.
7. `docs/FINITE_HORIZON_CAPABILITY_BRIDGE_2026-08-15.md` — Dig/TWC mathematical bridge and prior-art boundary.
8. `transientwave/measurement_capability.py` — reusable primitive.
9. `tests/test_measurement_capability.py` — primitive tests; normal full CI passed.

Cross-project origin only:

- `anttiluode/Dig/DISCRIMINATION_CLOCK_RECEIPT.md`
- `anttiluode/Dig/OBSERVABILITY_CLOCK_COLLISION.md`

Do not import Clockfield/GeometricNeuron physics claims from those repos. Only ordinary measurement-information mathematics survived the collision.

---

# Correct old baseline: v0.7 was 9/15, not 13/15

A previous version of this handoff accidentally transcribed the old result as `13/15`. That was wrong.

Frozen v0.7 run `31359232293` actually reported:

```text
true hidden edge top-1      9 / 15
true hidden edge top-3      9 / 15
augmented recovery          9 / 15
```

The six failures were perfectly structured:

```text
hidden (2,5): A/C/D ranks 6,8,7    0/3
hidden (0,3): A/C/D ranks 4,6,6    0/3
```

All three starts for hidden `(1,5)`, `(3,5)`, and `(0,4)` succeeded.

Those two difficult hidden edges are exactly the two static realization-gauge aliases identified independently after the frozen run.

---

# Existing exact capability map

For the published folded four-pole model:

```text
candidate (0,3)
    frees R1 <-> R3 realization rotation
    known R1 or R3 detuning anchors the gauge

candidate (2,5)
    frees R2 <-> R4 realization rotation
    known R2 or R4 detuning anchors the gauge
```

The v0.7 measurement schedule already happened to contain:

```text
BASE
R1_UP      d1 = +0.080
R2_DOWN    d2 = -0.070
R4_UP      d4 = +0.060
```

So exact gauge breaking was present but finite-noise topology ranking still failed. This remains the key distinction:

> **structural identifiability is necessary but not sufficient for practical diagnosis after a flexible wrong-model fit.**

---

# Reusable measurement-capability scalar

For candidate response derivative `g_S`, fitted physical+nuisance tangent `J_S`, and declared measurement rows `S`:

```text
I_c(S)
    = min_beta ||g_S - J_S beta||^2
    = ||(I-P_J_S) g_S||^2.
```

Under equal independent Gaussian measurement noise this is conditional Fisher information up to the noise variance. With real measured covariance, whiten first.

For nested measurement row sets and a fixed fitted parameterization:

```text
S1 subset S2  =>  I_c(S1) <= I_c(S2).
```

This is the monotone accumulated-information quantity.

The normalized novelty fraction

```text
eta = sqrt(I_c) / ||g||
```

need not be monotone because the raw candidate sensitivity changes too.

Reusable code:

```text
transientwave/measurement_capability.py

conditional_candidate_information(...)
nested_conditional_information_curve(...)
```

The normal repository CI passed after adding this primitive.

---

# Nominal gate — positive

Run:

```text
measurement-budget-identifiability
Actions 31895366566
artifact 9249649287
```

All eight absent reciprocal edges were included.

BASE conditional information for the exact aliases was machine-zero.

Then the independently predicted physical anchor states contained essentially all of the new gauge-breaking information:

```text
(0,3)
R1_UP fraction                    99.974%

(2,5)
R2_DOWN fraction                  57.11%
R4_UP fraction                    42.32%
combined R2/R4                    99.43%
```

The six non-gauge absent edges instead allocated approximately one quarter of their residual information to each state.

Channel preference was strongly candidate-specific. Frequency information was only moderately concentrated; no tiny set of magic frequencies emerged.

Nominal verdict:

> **The capability object adds an experiment-design statement beyond the old full-window novelty scalar: it says which physical perturbation and readout create the missing information.**

---

# Noisy fitted-point gate — stronger positive

Rather than create new noise draws, the robustness gate downloaded the exact fifteen original v0.7 stage-1 wrong-topology fitted artifacts from Actions run `31359232293`.

Each capability calculation was performed at the **fitted wrong-topology matrix and fitted state nuisance values**, not at the published truth.

Frozen primary rule:

```text
both aliases BASE-dark in 15/15
and
anchor-consistent >= 12/15 for each alias.
```

Result:

```text
(0,3)
BASE-dark                         15/15
correct R1_UP anchor              15/15
R1_UP information fraction
    min                           0.9997388
    median                        0.9997415
    max                           0.9997615

(2,5)
BASE-dark                         15/15
correct R2/R4 anchor family       15/15
combined R2/R4 fraction
    min                           0.9936966
    median                        0.9942567
    max                           0.9942757
```

Primary robustness verdict:

```text
PASS
```

Run:

```text
noisy-fitted-capability
Actions 31896167839
artifact 9249853272
```

All numerical guards passed.

---

# Why that robustness result matters

The six old v0.7 topology-discovery failures are precisely all starts for the two gauge-alias truths `(2,5)` and `(0,3)`.

Those six stage-1 fits are also the badly distorted tail:

```text
stage-1 matrix RMSE, all cells
median                 0.002180
max                    0.017109

six old failures
min                    0.013990
median                 0.015543
max                    0.017109
```

Yet the candidate-specific perturbation prescription remains essentially invariant.

Therefore:

> **The topology-gauge -> physical-anchor capability map is substantially more stable to wrong-model fit distortion than the old hidden-edge ranking itself.**

That is currently the strongest practical finding in TWC.

---

# Channel map also survives 15/15

For every one of the eight absent-edge candidates, the identity of the better single measured channel is unchanged across all fifteen fitted points:

```text
candidate   modal channel    agreement   median I_channel / I_joint

(0,2)       S11              15/15       .938 / .059
(0,3)       S11              15/15       .646 / .225
(0,4)       S21              15/15       .355 / .616
(1,3)       S11              15/15       .704 / .278
(1,5)       S21              15/15       .396 / .576
(2,4)       S11              15/15       .561 / .393
(2,5)       S11              15/15       .541 / .310
(3,5)       S11              15/15       .877 / .096
```

Joint S11+S21 can exceed the sum of separately residualized channel informations because both channels constrain the same shared compensating physical parameters.

This gives `CHANGE CHANNEL / ROUTE` a concrete, stable meaning in this benchmark family.

---

# What has actually been earned

TWC can defensibly expose a capability report such as:

```text
candidate (2,5)

STRUCTURAL STATUS
    BASE response has exact realization gauge

PERTURBATION
    R1_UP       irrelevant to this gauge
    R2_DOWN     opens the direction
    R4_UP       adds complementary information

CHANNEL
    S11 stronger single route
    joint S11+S21 supplies extra shared-parameter constraint

ACQUISITION
    more BASE samples cannot fix an exact gauge;
    acquire a physically anchored state instead
```

That is already useful even if no automatic topology recovery is attempted.

A good product phrase is:

> **measurement capability auditor**

rather than claiming a validated universal `measurement compiler` yet.

---

# What remains unearned

Even after the strong fitted-point pass, we have **not** shown:

```text
improved hidden-edge recovery
reduced real measurement cost
absolute hardware detectability
noise-optimal state/channel selection
robustness to correlated VNA noise
robustness on another filter/device family
```

The current metric still uses identity/equal-white-noise weighting because the old v0.7 artifacts do not contain an empirical repeated-sweep covariance estimate.

---

# Important stop line: do not tune a synthetic v0.8 on the six old failures

The frozen v0.7 result explicitly said not to manufacture more synthetic hit-rate ladders merely to improve the score.

Respect that.

Today’s capability result is independently useful because its state predictions came from the exact gauge map and were then tested at the frozen fitted points.

Do **not** now tune state weights or scoring rules on those same truth-labelled six failures until they rank first.

Legitimate next steps:

1. expose the capability report/API without a recovery claim;
2. on real repeated measurements, estimate covariance, whiten the tangent, and recommend the next perturbation/channel;
3. preregister a new independent device/noise family before testing capability-guided acquisition/recovery;
4. if synthetic cost/recovery is revisited, freeze the entire acquisition/scoring rule before generating new held-out devices/noise.

---

# Clockfield / GeometricNeuron boundary

This line was reached because Dig stripped old Clockfield/GeometricNeuron intuitions about receiver, horizon, spectrum, phase, and magnitude down to an ordinary information geometry.

What TWC imports:

```text
measurement/readout induces a geometry over alternative physical explanations;
additional independent observations add conditional information;
different ports and physical perturbations expose different directions;
exact null directions cannot be repaired by simply waiting/acquiring more of the same observation.
```

What it does **not** import:

```text
state-dependent spacetime
black-hole/event-horizon physics
Connes spectral distance
thermodynamic entropy
biological neuron mechanisms
```

The old metaphor was useful as search noise. The surviving object is ordinary observability/Fisher/experiment-design mathematics.

---

## One-line state

> **TWC can now robustly go from 'this candidate direction is structurally invisible in the current response' to 'this specific physical perturbation and this readout create the missing conditional information,' even at the original noisy wrong-topology fitted points where the old topology selector failed. The next honest step is external/held-out measurement design, not another tuned synthetic rescue ladder.**
