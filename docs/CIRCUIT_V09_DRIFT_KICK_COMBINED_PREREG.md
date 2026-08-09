# TW-1A v0.9 combined drift residual reference — preregistration

Date: 2026-08-09

Status: **diagnostic on spent bodies 2300..2309. No fresh seeds authorized until this simultaneous point resolves.**

The independent drift-switch residual sweeps remained clean through 10 ppm RMS on both common and C/D differential axes. This experiment tests the deliberately inward first-chip emulator reference with both residuals present at once.

## Frozen circuit point

```text
state coordinates                    exact kick-drift Z/P
reverse coordinates                  v0.8 common/difference C/D
edge thermal base                    2e-5
kick-residual self thermal base      2e-5
unity-drift thermal base             2e-5
kick-residual signed range           +/-0.125
kick-residual resolution             10 bits
post-cancel drift common RMS         5e-6 state FS
post-cancel drift C/D diff RMS       5e-6 state FS
```

All remaining v0.8 fabrication and acquisition settings are unchanged:

- edge nominal positive range 0.265;
- 3% RMS edge unit-cap mismatch;
- 1% RMS site-common Cunit/Cstate ratio mismatch;
- inherited edge switch cancellation model;
- converter, state leakage, LCC curvature, credit noise/offset/leakage;
- 30 parameter updates, step size 0.20;
- same task-specific static sense PGA;
- same fixed same-credit shuffled control.

The exact same spent seeds `2300..2309` are used. Static disorder and all dedicated residual/noise streams are unchanged from the independent-axis implementation; only both 5 ppm amplitudes are enabled simultaneously.

## Frozen physical audit

Every tile must satisfy before learning:

```text
112/112 monotonic edge codebooks
all edge site ratios positive
minimum physical edge full scale >= 0.250
kick-self target within +/-0.125
```

Report realized spatial RMS for C residual, D residual and C-D difference.

## Frozen learning predicate

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Decision

- If this combined point is clean, freeze it unchanged for fresh seeds 2400..2409.
- If it fails, no tolerance is adjusted. Diagnose the interaction on these already-spent bodies before any fresh v0.9 gate.
