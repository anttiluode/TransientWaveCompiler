# TW-1A hardware-emulator envelope — preregistration v0.1

Date frozen: 2026-08-09

This document is written **before** the TW-1A physical emulator is used to inspect learning results or choose failure boundaries.

The purpose is to prevent the emulator from becoming a parameter-tuning exercise.

The experiment asks:

> How far can a compiled 8x8 TW-1A mixed-signal tile be damaged before its four-pass local echo credit ceases to support useful closed-loop learning?

The answer must be reported as a hardware requirements envelope, including failures.

---

## 1. Frozen task family

Use five deterministic irregular arbor tasks, task seeds

```text
810, 811, 812, 813, 814
```

Each task is generated directly on the legal 8x8 four-neighbor TW-1A fabric.

Frozen task construction:

```text
physical grid          8 x 8
active arbor cells     40
active topology        connected acyclic tree grown from physical node 0
input                   root node 0
output                  graph-distance-farthest active node
source form             continuous_damped_wave
integration             semi_implicit_euler
dt                      0.08
steps                   56
gamma                   0.40
onsite H term           1.0
initial edge stiffness  10.0
trainable bounds        [2.0, 18.0]
trainable edges         every active arbor edge
objective               minimize quadratic output energy
```

The drive waveform is a frozen deterministic broadband signed sequence generated from the task seed, active during the first half of the horizon and zero afterwards. It is normalized before source lowering so no task receives a hand-selected amplitude after inspection.

The graph, drive and output are fixed by the task seed before hardware-noise seeds are drawn.

---

## 2. Frozen optimizer

Use host-side RMS-normalized SGD. This is intentionally simple and global; v0.1 is testing the physical credit direction, not an autonomous analog optimizer.

For the trainable parameter vector `theta` and measured physical credit `g`:

```text
g_scale = sqrt(mean(g^2)) + 1e-12
theta <- clip(theta - 0.25 * g/g_scale, min, max)
```

Frozen training length:

```text
iterations = 30
```

No momentum, Adam, line search, per-seed learning-rate tuning or early stopping is allowed in v0.1.

The programmed parameter is retained at host precision; every physical traversal re-quantizes the resulting `Q` according to the selected hardware bit depth. This models a digitally programmed low-resolution physical coefficient rather than permanently rounding the host optimizer state.

---

## 3. Loss measurement

For each iteration record:

1. the noisy physical objective reported by the emulated tile;
2. a deterministic evaluation objective using the same programmed/quantized coefficients and deterministic leakage, but with stochastic state noise, pass drift and readout noise disabled.

The **deterministic physical evaluation loss** is the primary learning metric. This avoids declaring failure because the final scalar measurement happened to receive a bad noise draw while retaining the actual quantized/leaky hardware transfer function.

Define fractional loss reduction

```text
R = (L_initial - L_final) / max(L_initial, 1e-30).
```

---

## 4. Baseline configuration requested for the end-to-end proof

Unless an axis is being swept, freeze:

```text
weight bits                8
weight quantizer            uniform
DAC bits                    8
ADC bits                    8
analog state noise sigma    0
state leakage rate/tick     0
leakage spatial CV          0
time-mirror gain error      0.05
differential +/- drift RMS  0.002   (0.2%)
credit offset fraction      0
credit readout noise        0.05    (5%)
state full scale            2.0
DAC full scale              schedule-normalized per drive port
ADC full scale              2.0
```

The baseline intentionally includes exactly the four imperfections named in the requested proof — 8-bit quantization, 0.2% differential pass drift, 5% time-mirror error and 5% credit readout noise — without silently adding leakage/state noise.

---

## 5. Baseline PASS / FAIL rule

The baseline is a **PASS** only if all of the following hold across the five frozen arbor seeds:

```text
A. all 5/5 have R > 0
B. at least 5/5 have R >= 0.10
C. median R >= 0.15
D. exact-placement physical credit beats a norm-matched shuffled-credit control
   in at least 4/5 tasks on final deterministic loss
E. median R_exact - median R_shuffle >= 0.10
F. no run produces NaN, Inf, unstable state overflow or illegal Q coefficients.
```

Otherwise the requested baseline learning proof fails and the failure is retained.

---

## 6. Axis-sweep PASS / FAIL rule

For a particular hardware level to count as **usable**, require:

```text
1. >= 4/5 tasks have R >= 0.10
2. median R >= 0.15
3. median R_exact - median R_shuffle >= 0.08
4. exact credit finishes below shuffled credit on >= 4/5 tasks
5. no numerical/hardware instability.
```

The **failure boundary** for a monotone damage sweep is the first worsened level that fails this rule after at least one less-damaged level passed.

If the sweep is non-monotone, do not invent a threshold. Report the complete pass/fail set and state that no single scalar boundary was earned.

---

## 7. Frozen sweeps to failure

Only one named axis changes at a time; all other settings remain at the baseline configuration unless a fixed nonzero value is explicitly stated below.

### 7.1 Programmable coupling resolution

```text
weight_bits = [12, 10, 8, 7, 6, 5, 4, 3]
```

Report the minimum passing weight resolution.

### 7.2 DAC/ADC resolution

Tie DAC and ADC resolution together for the first converter sweep:

```text
converter_bits = [12, 10, 8, 7, 6, 5, 4, 3]
```

The analytical representation budget in `DYNAMIC_RANGE_BUDGET.md` remains a separate hard constraint; empirical learning cannot waive clipping/under-resolution of a program at the compiler boundary.

Report the minimum passing converter resolution.

### 7.3 Common state leakage

Leakage is parameterized as a nonnegative exponential rate per tile tick:

```text
state <- exp(-leakage_rate) * state
```

for both live state registers between updates.

Sweep

```text
leakage_rate = [0, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2]
```

Report the largest passing leakage rate and its full-horizon retention `exp(-rate*T)`.

### 7.4 Spatial leakage disorder

A coefficient of variation is meaningless at zero mean loss. Freeze

```text
mean leakage_rate = 0.002 / tick
```

and assign each node one fixed nonnegative leakage rate for the run from a clipped Gaussian distribution with the requested coefficient of variation.

Sweep

```text
leakage_cv = [0, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0, 1.5]
```

Report the largest passing CV at the frozen mean leakage.

### 7.5 Time-mirror error

The exact discrete mirror swaps the terminal second-order state pair. The emulator preserves their midpoint and scales the reversed state difference by `(1 - mirror_error)`.

Sweep

```text
mirror_error = [0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0]
```

Report the largest passing mirror error.

### 7.6 Differential +/- pass drift

Within each reverse pass reciprocity is preserved. For each physical edge/diagonal coefficient, the PLUS and MINUS trials receive independent quasi-static multiplicative perturbations with the requested RMS fraction.

Sweep

```text
pass_drift = [0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
```

Report the largest passing RMS differential pass drift.

### 7.7 Credit readout noise

The requested baseline includes this axis, so record its margin even though it is not one of Claude's five primary build-envelope axes.

```text
credit_noise = [0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0]
```

Report the largest passing additive final-credit RMS fraction.

---

## 8. Controls

Every baseline and sweep point must have a shuffled-credit control.

For each physical training step:

1. acquire the same corrupted credit vector as the exact-placement learner;
2. apply a fixed RNG permutation to its edge locations;
3. preserve the credit vector's values and norm;
4. run an independent copy of the programmed parameters.

This asks whether the **placement/sign structure** of physical credit matters, rather than merely whether noisy updates or clipping regularize the wave body.

The shuffled arm is not allowed to receive a different learning rate or optimizer.

---

## 9. No post-hoc changes

After the first result from task seeds 810-814 is inspected, do not change:

- topology generator;
- steps;
- drive normalization;
- optimizer;
- iteration count;
- PASS/FAIL thresholds;
- sweep grids;
- baseline noise settings.

A bug fix that changes semantics requires a new preregistration version and a new untouched task-seed block.

Execution-only fixes that restore the frozen semantics may retain the seeds if no scientific result was inspectable before the fix; the reason must be recorded.

---

## 10. Deliverable

The v0.1 hardware envelope report must include:

```text
baseline requested configuration: PASS / FAIL
minimum passing weight bits
minimum passing DAC/ADC bits
maximum passing common leakage/tick + T-step retention
maximum passing leakage CV at mean rate .002
maximum passing mirror error
maximum passing +/- drift
maximum passing credit noise
analytical maximum compiled decay from converter/SNR budget
```

and the sentence

```text
TW-1A v0 is buildable under this task family iff the measured device lies inside
all preregistered representation and learning envelopes simultaneously.
```

No single sweep establishes general hardware viability. This is a first requirements envelope for the frozen 40-cell transient task family.
