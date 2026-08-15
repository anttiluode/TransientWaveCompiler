# Gate — measurement-budget conditional identifiability on the published filter

**Frozen:** 2026-08-15, before running the analysis.  
**Status:** engineering gate; no novelty claim for Fisher information or experiment design.

## Question

Can TWC's existing local candidate-identifiability calculation be turned into a useful **measurement capability map** that says which known state, which measured channel, and which frequency samples carry the conditional information for a proposed hidden edge?

The gate earns value only if it changes a protocol decision beyond the current one-number full-sweep novelty score.

---

# Frozen model

Use the active published-filter benchmark without refitting:

```text
n = 6 coupling-matrix nodes
published TARGET_VALUES from published_cross_coupled_filter_v03.py
OMEGA exactly as imported by v0.7 from that file:
    unique union of
      linspace(-30, +30, 601)
      linspace(-3,  +3,  601)
resonator loss = 0.020
```

Use the exact v0.7 known-state schedule:

```text
BASE      no fixed diagonal perturbation
R1_UP     d1 = +0.080
R2_DOWN   d2 = -0.070
R4_UP     d4 = +0.060
```

Evaluate nuisance phase/delay at zero, but include their tangent columns. The state-specific nuisance tangent is

```text
loss, phi11, tau11, phi21, tau21
```

matching the existing multistate identifiability model.

The seven declared shared physical parameter columns remain exactly `PARAMETERS` from the published benchmark.

Known state detunings are fixed coordinates, not fitted columns.

---

# Frozen candidate panel

Use **all absent reciprocal edges** returned by TWC's existing topology declaration.

The capability map already classifies exactly these two as static gauge aliases:

```text
(0,3)
(2,5)
```

All other absent edges are non-gauge controls.

Do not select candidates after seeing the information curves.

---

# Core scalar

For candidate derivative `g_S` and fitted physical+nuisance tangent `J_S` on measurement row set `S`, define

```text
I_c(S) = min_beta ||g_S - J_S beta||^2.
```

This is the squared orthogonal residual already implicit in TWC's local novelty score. Under equal independent white noise it is conditional Fisher information up to the noise variance.

For nested row sets it is monotone:

```text
S1 subset S2  =>  I_c(S1) <= I_c(S2).
```

Numerical implementation uses the same `rcond=1e-10` convention as `orthogonal_novelty_fraction`.

No detection threshold is introduced.

---

# Measurement A — state accumulation

For every candidate and each channel route below, compute `I_c` on:

```text
BASE
BASE + R1_UP
BASE + R1_UP + R2_DOWN
BASE + R1_UP + R2_DOWN + R4_UP
```

Channel routes:

```text
S11 only
S21 only
S11 + S21
```

Report:

```text
conditional information I_c
novelty fraction eta
candidate raw norm^2
I_c / raw candidate norm^2
```

Hard guard:

```text
I_c must not decrease as states are appended,
within absolute tolerance 1e-12 * max(final I_c, raw_norm^2, 1).
```

For the two exact static gauge aliases, BASE should reproduce numerical near-zero conditional information. This is a calibration check, not a hypothesis.

---

# Measurement B — full-protocol residual allocation

For each candidate under the full four-state, S11+S21 protocol, fit the nuisance/physical compensation once on the full frequency grid and retain the complex residual candidate signal.

Decompose its squared norm exactly by:

```text
frequency bin
known state
channel
```

Report:

```text
state fractions of final residual energy
channel fractions
frequency bins needed for 50% and 90% of fixed full-fit residual energy
normalized frequency-support entropy
top 12 frequency bins by residual energy
```

These allocations are descriptive. They do not by themselves prove that the same subset retains the same conditional information after re-fitting.

---

# Measurement C — reduced-frequency validation

For each candidate, order frequency bins by the frozen full-protocol residual energy from Measurement B.

For nested top-k sets

```text
k = 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, all
```

(clipped to the actual grid size), rebuild `J_S,g_S`, re-fit the compensating tangent, and compute the true conditional information again.

Report

```text
I_c(top-k) / I_c(full)
```

when `I_c(full)` is numerically nonzero.

This is intentionally an oracle/descriptive compression test because the frequency ordering was derived from the full candidate residual. It asks whether the information is *concentrated enough to make targeted measurement plausible*, not whether TWC can yet discover the optimal frequencies without a model.

Hard monotonicity guard applies along the nested top-k sequence.

---

# Measurement D — perturbation usefulness for the two gauge aliases

The capability map predicts:

```text
(0,3) gauge mixes R1 <-> R3
    R1_UP should break it

(2,5) gauge mixes R2 <-> R4
    R2_DOWN and/or R4_UP should break it
```

For each gauge candidate, report the first cumulative state schedule with conditional information exceeding

```text
1e-8 * raw_candidate_norm_squared
```

This numerical threshold is only a machine-scale `nonzero after projection` diagnostic, **not** a detectability threshold.

Also report state-specific residual-energy fractions under the full protocol.

---

# Interpretation / kill branches

## Useful engineering result

The extension earns another implementation step if at least one of these occurs:

```text
1. channel route changes the conditional-information ceiling by a large factor;
2. the predicted gauge-breaking state contributes most of the new residual information for an alias;
3. a small frequency subset recovers most of the full-protocol conditional information for some candidates while others remain diffuse;
4. the capability map cleanly distinguishes exact BASE impossibility from finite-measurement weakness after gauge-breaking.
```

No universal ratio is preregistered; report the full panel and do not select only winners.

## Kill / downgrade

If all eight candidates have essentially the same state/channel/frequency allocation and the curves merely reproduce the full-sweep novelty ordering, keep the existing identifiability scalar and stop this branch.

---

# What this cannot establish

It cannot establish:

```text
new Fisher-information mathematics
a new observability theorem
hardware performance
absolute detectability without a measured noise covariance
topology recovery success
Clockfield physics
```

The output is a **capability audit of the declared model and measurement protocol**.
