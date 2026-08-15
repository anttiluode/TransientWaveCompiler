# Noisy fitted-point measurement capability — result

Date: 2026-08-15  
Status: **PRIMARY ROBUSTNESS PASS / experiment-design diagnostic survives**

Gate:

- `docs/NOISY_FITTED_CAPABILITY_GATE_2026-08-15.md`

Frozen source benchmark:

- v0.7 Actions run `31359232293`
- exact 15 original stage-1 wrong-topology fitted artifacts

Robustness run:

```text
workflow  noisy-fitted-capability
run       31896167839
artifact  9249853272
```

All numerical guards passed.

The computational implementation was cached after the first attempt proved unnecessarily slow: all eight zero-valued candidate derivatives were evaluated together once per fitted state and then reused. This changed no fitted point, candidate panel, threshold, measurement row, or interpretation rule.

---

# Frozen primary rule

For both exact static gauge aliases:

```text
BASE conditional-information fraction < 1e-10 in all 15 fits
```

and anchor consistency had to hold in at least 12/15 fitted cells.

For `(0,3)`:

```text
R1_UP must be the largest state contribution
and carry >=80% of full residual information.
```

For `(2,5)`:

```text
largest state must be R2_DOWN or R4_UP
and R2_DOWN + R4_UP must carry >=80%.
```

These rules were frozen before inspecting the remaining fourteen fitted points.

---

# Result: 15/15 for both aliases

## `(0,3)` — R1 <-> R3 realization gauge

```text
BASE-dark calibration             15 / 15
anchor-consistent                  15 / 15
```

R1_UP fraction of full conditional residual information across fitted points:

```text
min       0.9997388
q10       0.9997400
median    0.9997415
q90       0.9997614
max       0.9997615
```

So after the original noisy wrong-topology fit has distorted the matrix and nuisance values, **99.974--99.976%** of the information that breaks this gauge still sits in the independently predicted R1 anchor state.

The other three state rows each carry only about `8e-5` of the full residual energy when the full four-state compensation is solved.

BASE itself remains structurally dark at every fitted point:

```text
median I_c(BASE) / ||g_BASE||^2  = 1.88e-30
maximum                           = 6.29e-30
```

Cumulative median absolute conditional information:

```text
BASE                     ~1.40e-27
+ R1_UP                    5.7966
+ R2_DOWN                  5.7979
+ R4_UP                    5.7986
```

Thus the relevant intervention is not merely stable in sign or rank. Almost the entire finite information opening is still attributable to the R1 anchor after noisy fitting.

---

# `(2,5)` — R2 <-> R4 realization gauge

```text
BASE-dark calibration             15 / 15
anchor-consistent                  15 / 15
```

Combined R2_DOWN + R4_UP fraction:

```text
min       0.9936966
q10       0.9936978
median    0.9942567
q90       0.9942739
max       0.9942757
```

Individual full-protocol state fractions are also extremely stable:

```text
R2_DOWN median      0.57113
R4_UP median        0.42314
BASE median         0.00287
R1_UP median        0.00288
```

BASE remains structurally dark in the standalone BASE projection:

```text
median I_c(BASE) / ||g_BASE||^2  = 2.61e-30
maximum                           = 4.41e-30
```

Cumulative median absolute information:

```text
BASE                     ~1.85e-27
+ R1_UP                   ~4.98e-27
+ R2_DOWN                  3.1579
+ R4_UP                    5.4745
```

So the irrelevant R1 anchor still does essentially nothing; the direction opens only when the independently predicted R2/R4 coordinates are perturbed.

---

# The channel map is also stable at every fitted point

For **all eight** absent-edge candidates, the identity of the better single channel is identical in all 15 wrong-topology fitted cells.

```text
candidate   modal single channel   agreement   median I_channel / I_joint

(0,2)       S11                    15/15       S11 .938   S21 .059
(0,3)       S11                    15/15       S11 .646   S21 .225
(0,4)       S21                    15/15       S11 .355   S21 .616
(1,3)       S11                    15/15       S11 .704   S21 .278
(1,5)       S21                    15/15       S11 .396   S21 .576
(2,4)       S11                    15/15       S11 .561   S21 .393
(2,5)       S11                    15/15       S11 .541   S21 .310
(3,5)       S11                    15/15       S11 .877   S21 .096
```

Joint information can exceed the sum of separately residualized channel informations because both channels constrain the **same shared compensating physical parameters** when solved jointly.

This is a robust candidate-dependent measurement-route map in this benchmark family.

---

# Non-gauge controls remain qualitatively different

For all six non-gauge absent edges, the median full-protocol residual allocation remains approximately one quarter per state at the noisy fitted points.

Representative medians:

```text
(0,2)   BASE .2498  R1 .2499  R2 .2503  R4 .2499
(0,4)        .2501     .2504     .2496     .2499
(1,3)        .2502     .2494     .2501     .2502
(3,5)        .2511     .2508     .2483     .2499
```

Their BASE conditional-information fractions remain large rather than machine-zero; median examples range from roughly `0.612` to `0.987` depending on candidate.

So the extreme state localization of the two gauge directions is not a generic artifact of fitting at noisy points.

---

# Important correction to the current handoff: v0.7 was 9/15, not 13/15

The frozen v0.7 result states:

```text
true hidden edge top-1     9 / 15
true hidden edge top-3     9 / 15
augmented recovery         9 / 15
```

The six failures were perfectly structured:

```text
hidden (2,5)   A/C/D true-edge ranks 6,8,7   -> 0/3
hidden (0,3)   A/C/D true-edge ranks 4,6,6   -> 0/3
```

All three starts for each of the other three hidden edges succeeded.

The earlier `13/15` sentence in `docs/HANDOFF_CURRENT.md` was a transcription error and must not be propagated.

---

# Strong robustness fact: the capability prescription survives exactly where discovery failed

The six old v0.7 failures are precisely the two gauge-alias hidden-edge cases across all starts.

Those six stage-1 wrong-topology fits are also unusually distorted:

```text
stage-1 matrix RMSE, all 15 cells
min       0.000494
median    0.002180
max       0.017109

six old discovery failures
min       0.013990
median    0.015543
max       0.017109
```

Yet the fitted-point capability calculation still assigns the gauge-breaking information to the correct physical anchor coordinates in all 15/15 fits for both aliases.

Therefore:

> **The topology-gauge -> perturbation prescription is substantially more stable to wrong-model fit distortion than the old hidden-edge ranking itself.**

That is the main robustness result.

---

# What this means — and what it does not

The new capability layer can robustly say, in this synthetic family:

```text
this direction is impossible in BASE;
this physical perturbation opens it;
this other perturbation is irrelevant;
this channel is the stronger one-dimensional route;
both channels may jointly constrain compensation better.
```

That is enough to support the phrase **measurement capability / experiment-design diagnostic**.

It does **not** yet show:

```text
that following the recommendation recovers the hidden edge;
that fewer measurements beat the full v0.7 schedule;
that the nominal equal-white-noise metric is hardware-optimal;
that the prescription survives a different filter family;
that TWC is already a validated measurement compiler.
```

In particular, v0.7 already contained the mathematically correct anchors and still failed to rank the two hard edges because their post-compensation novelty remained very small under finite noise/conditioning.

So the next question is not `do the anchors exist?` That has now been answered twice.

The real remaining question is whether a capability-guided measurement **allocation / weighting / new acquisition** can improve a decision under a measured noise model.

---

# Stop line against another synthetic hit-rate ladder

The v0.7 result explicitly said not to manufacture v0.8 synthetic rescue ladders merely to improve the score.

Respect that.

Do not now tune state weights on these same 15 truth-labelled cells until the two gauge cases rank first.

A legitimate next step is one of:

1. **measurement API / report only:** expose the proven structural/capability information without claiming recovery;
2. **new independent benchmark family:** preregister a capability-guided protocol before new truth/noise draws;
3. **real repeated measurements:** estimate measurement covariance, whiten the capability geometry, then let it recommend the next physical perturbation/channel;
4. if a cost/recovery gate is run on synthetic data, use fresh held-out devices/noise generated only after the protocol and scoring rule are frozen.

Do not reuse the six old failures as tuning targets.

---

## Verdict

> **PASS, strongly.** The candidate-specific perturbation and channel map survives all 15 noisy wrong-topology fitted points, including the six strongly distorted fits where the old topology selector failed. What has been earned is a robust experiment-design diagnostic, not yet a recovery algorithm.
