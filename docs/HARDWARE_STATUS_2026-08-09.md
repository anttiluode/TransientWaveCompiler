# TW-1A hardware status — 2026-08-09

This note is the shortest current map of what the emulator/compiler branch has actually earned.

## 1. The physical trainable object

The most important hardware correction was not adding precision. It was representing the compiled trainable object correctly.

A trainable physical bond is **one reciprocal rank-one edge cell**:

```text
Q += a_e (e_i-e_j)(e_i-e_j)^T
```

One edge coefficient is quantized once and then stamps the two diagonal and two off-diagonal contributions together. Disabled edges have an exact zero/off code.

Entrywise Q quantization used in emulator versions through v0.4 was invalid for this compiler contract and produced misleading/nonmonotone precision behavior.

The v0.5 edge-cell model is the current physical semantic.

## 2. Benchmark that actually tests credit placement

The original "minimize one output's energy" benchmark was rejected because shuffled gradients could improve it by merely weakening/detuning transmission.

The accepted benchmark is temporal-order contrast:

- same irregular 40-cell arbor;
- same two leaf events and total source energy;
- target AB versus distractor BA;
- only temporal order differs;
- soma/root output;
- normalized contrast

```text
C = (E_AB - E_BA)/(E_AB + E_BA)
```

The combined physical contrast credit matches finite differences in the ideal machine.

Ideal frozen seeds 840–849 passed 10/10 with median `DeltaC = +0.655` and median placed-vs-shuffled improvement gap `+0.621`.

## 3. Dynamic-range math

TW-1 uses signed zero-preserving mid-tread converter semantics. With B bits the positive code count is

```text
K = 2^(B-1) - 1.
```

If the weakest relevant signal must occupy at least `m` code steps across a relative span `S`, require

```text
K/S >= m
B >= 1 + ceil(log2(m*S + 1)).
```

For the compiler's architecture-wide `max_boundary_gain = G = 8` promise and the frozen four-code margin:

- amplitude compensation span: `8x = 18.06 dB`;
- worst-case broadband drive envelope: 8x -> **7 signed bits**;
- an impulse has only one nonzero temporal amplitude -> **4 signed bits** for the four-code margin;
- quadratic returned-error envelope: `G^2 = 64x = 36.12 dB` -> **10 signed bits**.

The 10-bit returned-error budget is an architecture-wide promise. It must not be confused with the lower task-specific DAC floor measured below.

## 4. Task-specific precision floors

Fresh v0.5 seeds 910–915, one axis at a time:

| path | stable measured floor within tested grid |
|---|---:|
| reciprocal rank-one edge cell | **5 bits** |
| drive/error DAC | **4 bits (lowest tested)** |
| sense ADC with static PGA | **5 bits** |

Clean simultaneous 8/8/8 passed strongly on fresh seeds 916–921.

A practical reference profile therefore remains 8-bit edge cells, 8-bit drive DAC, 8-bit sense ADC, with a separate approximately 10-bit returned-error path if the implementation promises the full `G=8` compiler envelope without task-specific rescaling.

## 5. Static sense PGA

A fixed +/-2 ADC range erased legitimate small soma/root signals on some geometries. TW-1A therefore uses a compiler-predicted static binary PGA:

1. model initial target/distractor root traces with the candidate programmed Q and DAC precision;
2. choose the largest binary gain keeping the larger predicted initial peak <=25% ADC full scale;
3. use one common gain for the task pair;
4. freeze it for training;
5. digitally de-gain after ADC conversion.

This is static range setting, not per-sample AGC.

## 6. Independent physical-error boundaries at 8/8/8

Frozen v0.5/v0.6 sweeps produced:

| imperfection | measured independent boundary | preregistered inward recommendation |
|---|---:|---:|
| mean leakage / tick | **0.002** | **0.001** |
| mirror gain error | **0.50** | **0.30** |
| independent PLUS/MINUS pass drift | **0.001 = 0.1% RMS** | **0.0005 = 0.05%** |
| analog state noise | **3e-8 FS RMS/tick** | **1e-8 FS** |
| systematic local credit offset | **0.001 = 0.1%** | **0.0003 = 0.03%** |
| zero-mean local credit noise | **>=1.0 RMS tested** | **0.50** |
| leakage spatial CV @ mean leakage .001 | **>=1.5 tested** | **1.0** |

These are one-axis measurements. They are **not** a Cartesian simultaneous-safe box.

## 7. First demonstrated simultaneous mixed-signal corner

v0.8 is the first preregistered simultaneous corner that passed every criterion on ten untouched arbors (seeds 980–989):

```text
edge Q bits             8
DAC bits                8
ADC bits                8 + static PGA
mean leakage/tick       0.0005
leakage CV              0.50
mirror error            0.15
PLUS/MINUS differential drift RMS
                        1e-5 = 10 ppm
zero-mean credit noise  0.25
credit DC offset        0.00015 = 0.015%
state noise             5e-9 FS RMS/tick
```

Result:

- 10/10 exact learners improved by at least +0.10 contrast;
- 10/10 exact final contrast beat shuffled final contrast;
- median `DeltaC = +0.9552`;
- median placement advantage `+0.8983`.

This corner is demonstrated. It does not imply that the independent one-axis maxima can all be used simultaneously.

## 8. What the drift experiments actually say

The severe number is specifically **differential operator change inside a physical gradient evaluation**.

### Small-N averaging is killed

At 0.2% independent PLUS/MINUS drift, averaging N complete physical gradients for `N=1,2,4,8,16` never qualified. N=16 already costs 128 physical traversals per contrast update.

Simple variance scaling would need about 10,000 independent measurements to reduce 0.2% to the ~20-ppm combined-context boundary seen in development.

### Sharing Q only across PLUS/MINUS is not enough

Making PLUS and MINUS use one common drifted reverse Q dramatically improved learning but did not satisfy the strict tail predicate.

### The correct coherence scope is the complete gradient evaluation

For

```text
C(Q) = [E_AB(Q)-E_BA(Q)]/[E_AB(Q)+E_BA(Q)],
```

the host combines `E_AB`, `dE_AB`, `E_BA`, and `dE_BA`. These quantities must refer to one physical operator realization.

Freezing one reciprocal Q across the complete AB+BA gradient evaluation, while allowing Q to redraw between optimizer updates, nearly qualified at **0.2% absolute spatial Q variation** on fresh seeds 990–999:

- median `DeltaC = +0.610`;
- 9/10 `DeltaC >=0.10`;
- 10/10 exact final > shuffled;
- one marginal seed was slightly negative, so the strict preregistration remained FAIL.

A development sweep from 0 to **0.5% coherent Q variation** on those same spent seeds left essentially the same single tail failure. Therefore **no absolute coherent-drift boundary has been earned**; the data do not support interpreting 0.2% or 0.5% as a confirmed tolerance.

The architectural lesson is nevertheless clear enough to encode:

> One physical gradient evaluation should be acquired while the reciprocal operator is effectively one common realization.

## 9. Residual robustness tail

At zero coherent drift on spent seeds 990–999, the same marginal seed could be rescued independently by removing mean leakage, state noise, credit offset, or zero-mean credit noise. Removing mirror error or leakage CV did not rescue it.

Therefore the remaining failure is an interaction/tail phenomenon, not one uniquely identifiable tolerance axis. This is why the current branch stops sweeping tolerances and moves the earned requirements into the compiler contract.

## 10. Compiler-visible hardware contract

`transientwave/hardware_contract.py` now reports, for every strict TW-1A manifest:

- signed zero-preserving converter semantics;
- one reciprocal rank-one edge cell per physical bond;
- static sense PGA expectation;
- per-program drive schedule kind and amplitude span;
- per-program compiled objective/error multiplier span;
- exact signed bit requirements for those spans at the frozen code margin;
- architecture-wide `max_boundary_gain` drive/error budgets;
- reference profile checks;
- empirical evidence labels and source documents;
- complete-gradient operator coherence as the preferred acquisition scope.

The contract currently **reports rather than rejects** mixed-signal margin misses. Mathematical legality, stability and routing remain hard compiler errors. Empirical hardware sufficiency is not yet promoted into a universal compile-time theorem.

## Shortest current picture

TW-1A is no longer well described as "a symmetric Q matrix with some noisy ADCs."

It is:

> a sparse reciprocal mesh of one-parameter rank-one edge cells, with exact zero/off codes, compiler-managed temporal dynamic range and sense gain, whose local +/- energy readout is useful only when all physical measurements combined into one gradient refer to a sufficiently coherent operator realization.

That is the current hardware target.
