# TW-1A v0.8 complete-gradient averaging — result

Date: 2026-08-09

Status: **M=8 is the first clean point on spent bodies 2300..2309. No fresh seed is authorized.**

At `b_edge=b_self=2e-5`, each parameter update averaged M independent complete physical contrast-gradient estimates on the same held fabricated tile. The total update count remained 30.

| M | >= +0.10 | exact > shuffled | median DeltaC | minimum DeltaC | median gap | clean |
|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 5/10 | 10/10 | +0.100997 | -0.000138 | +0.090951 | NO |
| 2 | 9/10 | 10/10 | +0.164903 | -0.011011 | +0.174895 | NO |
| 4 | 9/10 | 10/10 | +0.217294 | +0.020139 | +0.208055 | NO |
| 8 | 10/10 | 10/10 | +0.313416 | +0.135016 | +0.310913 | YES |

At fixed voltage and temperature, moving from `b=1e-5` to `2e-5` quarters the kT/C capacitance. Under the deliberately limited ideal switched-cap work model, the capacitor contribution per update therefore scales as `M/4`: M=2 -> 0.5x, M=4 -> 1x, M=8 -> 2x. OTA, clock, converter, reference and credit-path energy are excluded.

Because M=8 is the first clean point, averaging is a valid area/latency fallback but is not the preferred first-chip remedy. It gives 4x smaller thermal capacitance at 8x echo traversal count and about 2x the idealized capacitor switching work before active overhead.

Decision: keep v0.8 M=8 as a documented fallback; continue the structural self/inertia path. Exact `(Z,P)` coordinates use the same two state vectors and C1f has already passed deterministic two-bank shear topology. The next audit is P-bank dynamic range followed by explicit unity-drift noise.
