# TW-1A corrected hardware envelope — preregistration v0.2

Date frozen: 2026-08-09

Reason for new version: `HARDWARE_ENVELOPE_V01_INVALID.md` documents that the v0.1 endpoint quantizer did not preserve zero, turning disabled edges and silent DAC samples into nonzero signals. v0.2 uses `transientwave/emulator_v02.py`, whose signed mid-tread quantizer obeys

```text
weight_Q(0) = DAC(0) = ADC(0) = 0
```

exactly.

No v0.1 noisy threshold is reused as evidence.

---

# 1. Two-stage design

v0.1 showed why hardware-tolerance sweeps cannot be interpreted around a failing precision operating point.

v0.2 therefore has two independently seeded stages.

```text
Stage A — precision qualification
fresh task seeds 820-824
joint weight-bit x converter-bit grid
select an operating point by a frozen rule

Stage B — tolerance envelope
fresh task seeds 830-834
use only the Stage-A-selected precision point
sweep leakage, leakage CV, mirror error, +/- drift, credit noise and state noise
```

Stage B may run only if Stage A earns a precision point. If no point satisfies the frozen selection rule, v0.2 ends with `NO QUALIFIED PRECISION POINT` and no tolerance specification is claimed.

---

# 2. Frozen task construction

Use the same benchmark generator semantics as v0.1, but never reuse the inspected v0.1 seeds.

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
active onsite H         1.0
parked onsite H         10.0
initial edge stiffness  10.0
trainable bounds        [2.0, 18.0]
trainable edges         every active arbor edge
objective               minimize quadratic output energy
```

The deterministic broadband drive remains seed-generated, signed, normalized, active for the first half of the horizon and **exactly zero** for the second half after v0.2 DAC quantization.

---

# 3. Frozen optimizer and controls

Use exactly the v0.1 host optimizer:

```text
g_scale = sqrt(mean(g^2)) + 1e-12
theta <- clip(theta - 0.25 * g/g_scale, min, max)
iterations = 30
```

No momentum, Adam, line search, early stop or seed-specific tuning.

Every run has the same fixed-permutation norm/value-preserving shuffled-credit control.

Primary metric remains deterministic physical evaluation loss with programmed quantization and fixed leakage retained but stochastic state noise, differential pass drift and credit noise disabled during evaluation.

```text
R = (L_initial - L_final) / max(L_initial, 1e-30)
```

---

# 4. Common learning PASS rule

A configuration is a PASS only if, across its five frozen tasks,

```text
1. >= 4/5 tasks have exact R >= .10
2. median exact R >= .15
3. median exact R - median shuffled R >= .08
4. exact final loss < shuffled final loss on >= 4/5 tasks
5. no NaN/Inf/state overflow/illegal physical coefficient.
```

This is the same axis-usable rule frozen before v0.1.

---

# 5. Stage A — joint precision qualification

Fresh tasks:

```text
820, 821, 822, 823, 824
```

All non-precision imperfections are frozen at the requested baseline:

```text
state noise                0
state leakage              0
mirror error               .05
+/- differential drift     .002
credit offset              0
credit readout noise       .05
state full scale           2.0
ADC full scale             2.0
weight quantizer           uniform signed mid-tread
```

Sweep the full grid

```text
weight bits     W = [12, 10, 8, 7, 6]
DAC/ADC bits    C = [12, 10, 9, 8, 7, 6]
```

DAC and ADC are tied in Stage A only to keep the first silicon requirement compact.

The task-specific analytical representation check from `DYNAMIC_RANGE_BUDGET_V02.md` is applied first. A converter point that cannot represent the frozen task's compiled envelope at four-code margin is **representation-fail** even if stochastic learning happens to improve.

## Stable-corner rule

A passing pair `(W,C)` becomes a **stable-corner candidate** only if every tested grid point with

```text
weight_bits >= W
converter_bits >= C
```

also passes.

This prevents a lucky isolated coarse-quantization resonance from being reported as a precision requirement.

If one or more stable-corner candidates exist, select the one minimizing, in order:

```text
1. W + C
2. max(W,C)
3. C
4. W
```

The selected `(W*,C*)` is the Stage-A precision operating point.

If no stable corner exists, do not hand-pick a cell. Stage B is not interpreted as a build envelope.

## Stage-A deliverable

Report:

```text
full pass/fail grid
selected stable precision corner or NONE
minimum qualified weight bits implied by the corner
minimum qualified tied DAC/ADC bits implied by the corner
```

Do not equate the task-specific selected converter precision with the architecture-wide worst-case `G<=8` requirement; the latter remains 10 signed bits at the frozen four-code error-envelope margin.

---

# 6. Stage B — tolerance sweeps to failure

Fresh tasks:

```text
830, 831, 832, 833, 834
```

Use `(W*,C*)` from Stage A with baseline

```text
mirror error               .05
+/- differential drift     .002
credit noise               .05
state leakage              0
leakage CV                 0
state noise                0
```

Before any axis is interpreted, the selected operating point must PASS the common learning rule on seeds 830-834. If it fails this fresh baseline transfer, report `PRECISION POINT DID NOT TRANSFER` and do not claim tolerance maxima.

Each axis then changes alone.

## 6.1 Common state leakage

```text
rate/tick = [0, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2]
```

Report both rate and 56-tick retention `exp(-56 rate)`.

## 6.2 Spatial leakage disorder

Freeze mean leakage rate

```text
.002 / tick
```

and sweep fixed nodewise coefficient of variation

```text
CV = [0, .10, .20, .30, .50, .75, 1.0, 1.5]
```

with nonnegative clipped Gaussian rates as implemented by the emulator.

## 6.3 Time-mirror error

```text
mirror_error = [0, .02, .05, .10, .20, .30, .50, .75, 1.0]
```

## 6.4 Differential PLUS/MINUS pass drift

```text
RMS drift = [0, .0005, .001, .002, .005, .01, .02, .05]
```

Each reverse pass remains reciprocal internally; PLUS and MINUS receive independent quasi-static coefficient perturbations.

## 6.5 Credit readout noise

```text
fraction = [0, .02, .05, .10, .20, .50, 1.0]
```

## 6.6 Analog state noise

Additive Gaussian noise is quoted as fraction of `state_full_scale` per node per tick:

```text
sigma = [0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
```

---

# 7. Failure-boundary rule

For a monotone damage axis, the empirical requirement is the largest damage value that passes **before the first fail**, provided every less-damaged tested value also passes.

If pass/fail is non-monotone, do not collapse it to a scalar requirement. Report the complete pattern and state `NO MONOTONE BOUNDARY EARNED`.

For bits, the Stage-A stable-corner rule replaces this one-dimensional rule.

---

# 8. Required v0.2 hardware-envelope sentence

Only if Stage A finds a stable corner and that corner transfers to Stage B may the report state:

```text
For the frozen 40-cell / 56-tick task family, TW-1A v0.2 requires at least
W* programmable-weight bits and C* tied DAC/ADC bits at the selected operating
point, with empirical tolerance bounded by the Stage-B monotone failure limits.
```

The report must separately state:

```text
The architecture-wide G<=8 compiler promise still requires a 10-bit signed
zero-preserving quadratic error-envelope path at the four-code representation margin.
```

No emulator result constitutes a fabrication-ready claim.

---

# 9. No post-hoc changes

After the first Stage-A result on seeds 820-824 is inspected, do not change:

- task generator;
- optimizer;
- iteration count;
- precision grid;
- stable-corner rule;
- PASS thresholds;
- Stage-B seed block;
- Stage-B sweep grids.

A semantic bug requires another version and untouched seeds.
