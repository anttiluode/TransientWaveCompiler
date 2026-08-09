# Published coupled-resonator filter tuning benchmark v0.2 — preregistration

Date: 2026-08-09

Status: **external-domain six-knob tuning benchmark; frozen before optimization outcomes.**

## Purpose

v0.1 recovered the three published reciprocal coupling values from five detuned coupling matrices. v0.2 turns the same published filter into a more realistic tuning problem by allowing both:

```text
resonator self-detuning knobs  M11, M22, M33
inter-resonator couplings      M12, M23, M13
```

All six parameters are wrong at the start. The target remains the published three-resonator response:

```text
M_target = [[0.0, 0.6, 0.2],
            [0.6, 0.0, 0.6],
            [0.2, 0.6, 0.0]]
```

with normalized endpoint loading `r=1` and the same 401-sample `gamma in [-2.5,+2.5]` grid used by v0.1.

The diagonal entries are interpreted as normalized resonator-frequency/self-detuning terms in the coupling-matrix model. This benchmark stays at matrix level; it does not yet claim a particular screw displacement-to-diagonal calibration law.

## Parameter vector

Frozen order:

```text
[d1, d2, d3, m12, m23, m13]
```

where

```text
d1 = M11
d2 = M22
d3 = M33
```

and each off-diagonal coupling stamps its reciprocal matrix pair.

Frozen bounds:

```text
-0.80 <= d1,d2,d3 <= +0.80
+0.05 <= m12,m23   <= +1.20
-0.60 <= m13       <= +0.80
```

The positive main-line coupling convention removes trivial resonator sign-gauge alternatives while retaining the published realization convention.

## Frozen detuned starts

```text
A = [+0.30, -0.20, +0.15, 0.35, 0.82, -0.05]
B = [-0.25, +0.35, -0.10, 0.85, 0.35, +0.45]
C = [+0.40, +0.10, -0.30, 0.30, 0.30, +0.50]
D = [-0.45, +0.20, +0.35, 1.00, 0.75, -0.30]
E = [+0.15, -0.40, +0.25, 0.45, 1.00,  0.00]
```

No random restarts are permitted.

## Objective and derivative audit

Use exactly the v0.1 magnitude-response objective:

```text
mean_gamma [
    (|S11|-|S11_target|)^2 +
    (|S21|-|S21_target|)^2
]
```

The generic matrix-parameter derivative uses

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1
```

for both a one-entry diagonal stamp and a reciprocal two-entry edge stamp.

Before benchmark outcomes are interpreted, the six-variable analytic gradient must pass central finite differences in `tests/test_coupled_resonator_filter.py`.

## Frozen optimizer

Adam, with no schedule or rescue phase:

```text
iterations    = 1200
learning rate = 0.025
beta1         = 0.9
beta2         = 0.999
epsilon       = 1e-8
```

Project to the declared bounds after every step.

## Frozen readouts

For each start record:

```text
initial response loss
final response loss
loss reduction factor
final six-parameter vector
overall parameter RMSE
resonator-detuning RMSE
coupling RMSE
max |S11| magnitude error
max |S21| magnitude error
iterations
```

Response recovery and knob recovery are reported separately because a response-equivalent coupling matrix must not silently be called a physical-knob recovery.

## Frozen pass criteria

Call v0.2 a **RESPONSE PASS** only if all five starts satisfy:

```text
final response loss <= 2e-5
loss reduction factor >= 1e3
max |S11| magnitude error <= 0.02
max |S21| magnitude error <= 0.02
```

Call it a **SIX-KNOB RECOVERY PASS** only if RESPONSE PASS also holds and all five starts satisfy:

```text
overall parameter RMSE <= 0.03
resonator-detuning RMSE <= 0.03
coupling RMSE <= 0.03
```

A stronger **EXACT SIX-KNOB RECOVERY** label requires all five overall parameter RMSE values <= 0.01.

## Frozen decision

- **Exact six-knob recovery:** promote diagonal resonator tuning to the application layer and proceed directly to a larger published cross-coupled filter with transmission-zero structure.
- **Response pass but knob-recovery fail:** preserve response tuning, then diagnose coupling-matrix equivalence/gauge structure before claiming tuner-setting recovery. Do not change starts or objective post hoc.
- **Response fail:** diagnose the exact-gradient optimizer on these same spent starts before expanding the application.

This benchmark is independent of TW-1A small-cap on-device learning and uses an ordinary high-accuracy computer-side optimizer.
