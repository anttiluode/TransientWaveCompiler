# Published cross-coupled four-transmission-zero filter benchmark v0.3 — preregistration

Date: 2026-08-09

Status: **external-domain topology/knob-recovery benchmark; frozen before optimization outcomes.**

## Published target

Use the normalized coupling matrix in Equation (4) of:

Shuang Li, Shengxian Li, Jianrong Yuan, *A Compact Fourth-Order Tunable Bandpass Filter Based on Varactor-Loaded Step-Impedance Resonators*, Electronics 12(11), 2539 (2023), DOI `10.3390/electronics12112539`.

The paper's explicit source–four-resonator–load matrix is

```text
M = [[0,      1.02,  0,     0,     0,      0.0005],
     [1.02,   0,    -0.86,  0,    -0.19,   0     ],
     [0,     -0.86,  0,     0.77,  0,      0     ],
     [0,      0,     0.77,  0,    -0.86,   0     ],
     [0,     -0.19,  0,    -0.86,  0,      1.02  ],
     [0.0005, 0,     0,     0,     1.02,   0     ]]
```

The authors use the cross-coupling `m14=-0.19` to generate the near-band transmission-zero pair and the direct source-load coupling `mSL=0.0005` to generate another pair farther out. Their normalized target places the two zero pairs around `Omega=+-1.7` and `Omega=+-25`.

## Generalized response model

Use the paper's explicit-port equations:

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)
```

where `U` has ones on the four resonator diagonal positions and zeros at source/load, while `q` has ones only at source/load.

This formulation is implemented separately from the simpler three-resonator endpoint-loaded module; no source/load matrix is silently reinterpreted as a TW recurrence.

## Frozen trainable topology

Preserve exactly the seven nonzero reciprocal matrix knobs of the publication:

```text
parameter order = [mS1, m12, m23, m34, m4L, m14, mSL]
target          = [1.02,-0.86,0.77,-0.86,1.02,-0.19,0.0005]
```

All other matrix entries, including resonator diagonals, remain exactly zero in v0.3.

Frozen bounds:

```text
0.40 <= mS1,m4L <= 1.50
-1.50 <= m12,m34 <= -0.20
0.20 <= m23 <= 1.30
-0.70 <= m14 <= 0.40
-0.05 <= mSL <= 0.05
```

These sign conventions preserve the published realization and avoid trivial resonator sign-gauge equivalents.

## Frozen detuned starts

```text
A = [0.80,-0.60,0.95,-1.05,1.15,-0.05,+0.020]
B = [1.18,-1.05,0.55,-0.65,0.82,-0.35,-0.015]
C = [0.70,-0.45,0.50,-0.50,0.75,+0.10,+0.030]
D = [1.25,-1.15,1.00,-1.10,1.25,-0.40,-0.025]
E = [0.92,-0.72,0.90,-0.73,1.12, 0.00,+0.010]
```

The direct source-load coupling is deliberately detuned by factors tens of times larger than its `0.0005` target value.

## Frozen frequency grid and objective

Use a composite normalized-frequency grid to cover both the passband/near zeros and the far source-load zeros:

```text
Omega = unique(
    linspace(-30,+30,601) union
    linspace(-3,+3,601)
)
```

v0.3 uses the **complex calibrated S-parameter** objective

```text
mean [ |S11-S11_target|^2 + |S21-S21_target|^2 ].
```

This is intentionally stricter/more identifiable than magnitude-only fitting and corresponds to a calibrated VNA-style computer-side tuning loop. Reference-plane phase calibration is assumed in this synthetic matrix benchmark; real-measurement phase nuisance terms are future work.

The exact gradient again uses

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

Before outcomes are interpreted, `tests/test_generalized_coupling_matrix.py` must pass:

- exact published matrix stamping;
- lossless power conservation;
- seven-variable analytic gradient versus central finite differences.

## Frozen optimizer

Adam only:

```text
iterations    = 2000
learning rate = 0.015
beta1         = 0.9
beta2         = 0.999
epsilon       = 1e-8
```

Project to the frozen bounds after every step. No restarts, schedules, line search, per-parameter learning-rate tuning or second rescue stage are allowed.

## Frozen readouts

For each start record:

```text
initial complex-response loss
final complex-response loss
loss reduction factor
final seven-parameter vector
overall parameter RMSE
main-path coupling RMSE: mS1,m12,m23,m34,m4L
cross-coupling absolute error: m14
direct source-load absolute error: mSL
max complex S11 error
max complex S21 error
max |S11| magnitude error
max |S21| magnitude error
```

## Frozen pass criteria

Call v0.3 a **RESPONSE PASS** only if all five starts satisfy:

```text
final complex-response loss <= 1e-6
loss reduction factor >= 1e4
max complex S11 error <= 0.01
max complex S21 error <= 0.01
```

Call it a **TOPOLOGY/KNOB RECOVERY PASS** only if RESPONSE PASS also holds and all five satisfy:

```text
overall parameter RMSE <= 0.01
main-path coupling RMSE <= 0.01
|m14 - (-0.19)| <= 0.01
|mSL - 0.0005| <= 0.0005
```

A stronger **EXACT CROSS-COUPLED RECOVERY** label requires all five overall RMSE values <= `0.003` and all five direct source-load errors <= `0.0002`.

## Frozen decision

- **Exact recovery:** the compiler application has survived both a six-knob resonator/coupling problem and a larger published transmission-zero topology. Next move from synthetic target curves to an actuator/measurement calibration layer and measured/noisy S-parameter perturbations.
- **Response pass but knob fail:** preserve the response-tuning result; diagnose identifiability/reference-plane/gauge structure before claiming physical actuator recovery.
- **Response fail:** keep the five starts spent and diagnose optimizer/model conventions there. Do not substitute a friendlier published matrix.

This benchmark is computer-side filter tuning. It makes no claim that TW-1A's small-cap on-device learner has been rescued.
