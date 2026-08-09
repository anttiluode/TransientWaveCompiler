# TW-1A v0.9 drift-shear switch residual — result

Date: 2026-08-09

Status: **both independent axes clean through 10 ppm on spent bodies; boundary not sought. No fresh seed authorized yet.**

Preregistration: `docs/CIRCUIT_V09_DRIFT_KICK_PREREG.md`

The full kick-drift thermal learner had already passed with

```text
b_edge = b_kick_self = b_drift = 2e-5.
```

This gate added the missing static post-cancellation switch-injection residual at the node-local unity drift interface. The physical model was

```text
q_C = q_common + q_diff/2
q_D = q_common - q_diff/2,
```

with forward and terminal inverse drift using the C-side residual. Dedicated unit Gaussian spatial fields were held fixed while each RMS axis was scaled, so sweep points did not redraw static silicon.

## Differential-only axis

| C/D differential RMS | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|:---:|
| 0 ppm | 10/10 | 10/10 | +0.561704 | +0.234039 | +0.533367 | YES |
| 0.5 ppm | 10/10 | 10/10 | +0.562731 | +0.215196 | +0.546928 | YES |
| 1 ppm | 10/10 | 10/10 | +0.571001 | +0.228398 | +0.553386 | YES |
| 2 ppm | 10/10 | 10/10 | +0.572684 | +0.203250 | +0.540363 | YES |
| 3 ppm | 10/10 | 10/10 | +0.580715 | +0.208633 | +0.547098 | YES |
| 5 ppm | 10/10 | 10/10 | +0.564425 | +0.222475 | +0.539612 | YES |
| 10 ppm | 10/10 | 10/10 | +0.567571 | +0.214625 | +0.548330 | YES |

## Common-only axis

| common RMS | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|:---:|
| 0 ppm | 10/10 | 10/10 | +0.561704 | +0.234039 | +0.533367 | YES |
| 0.5 ppm | 10/10 | 10/10 | +0.553297 | +0.219803 | +0.543403 | YES |
| 1 ppm | 10/10 | 10/10 | +0.556934 | +0.233962 | +0.543567 | YES |
| 2 ppm | 10/10 | 10/10 | +0.570672 | +0.229170 | +0.560250 | YES |
| 3 ppm | 10/10 | 10/10 | +0.572476 | +0.245176 | +0.555817 | YES |
| 5 ppm | 10/10 | 10/10 | +0.570353 | +0.253494 | +0.566924 | YES |
| 10 ppm | 10/10 | 10/10 | +0.573134 | +0.253622 | +0.558762 | YES |

No failure boundary appeared inside the preregistered 0--10 ppm range. In particular, the unity drift shear does **not** reproduce the old v0.7-style pass-to-pass coherence cliff: both an absolute/common residual and a C/D differential residual are tolerated at least into the 10 ppm class with strong learning margin on these bodies.

## Decision

Do not spend compute merely to manufacture a boundary. Use a 2x inward first-chip emulator reference:

```text
drift residual common RMS       <= 5 ppm state FS
C/D differential drift RMS      <= 5 ppm state FS
```

This is a **post-cancellation residual contract**, not a raw switch-injection claim. The raw kick amplitude and cancellation/autozero implementation remain transistor/layout questions.

Before fresh qualification, test the two residuals simultaneously on the same spent silicon. Independent-axis passes do not mathematically guarantee the combined corner.
