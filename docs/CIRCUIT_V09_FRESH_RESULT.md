# TW-1A v0.9 fresh kick-drift qualification — result

Date: 2026-08-09

Status: **FORMAL FAIL. Seeds 2400..2409 are spent.**

Preregistration: `docs/CIRCUIT_V09_FRESH_PREREG.md`

The complete fresh v0.9 point was frozen before release:

```text
exact kick-drift Z/P state coordinates
v0.8 common/difference C/D reverse coordinates
edge b = 2e-5
kick-self b = 2e-5
drift b = 2e-5
post-cancel drift common residual = 5 ppm RMS
post-cancel drift C/D differential = 5 ppm RMS
kick-self range = +/-0.125, 10 signed bits
edge range/mismatch/site-ratio/converters/leakage/LCC/credit inherited unchanged
30 normalized parameter updates, step size 0.20
```

## Formal result

```text
fabrication audit                    10/10 PASS
improvement >= +0.10                 8/10 FAIL
final exact > shuffled              10/10 PASS
median improvement              +0.332201 PASS
minimum improvement             -0.000036
median placement gap            +0.332194 PASS
minimum placement gap           +0.041920
minimum edge positive range      0.254769
maximum |kick-self target|       0.064785
```

Per body:

| seed | DeltaC | placement gap | exact > shuffled |
|---:|---:|---:|:---:|
| 2400 | +0.025219 | +0.073758 | yes |
| 2401 | +0.340742 | +0.468777 | yes |
| 2402 | +0.767169 | +0.967691 | yes |
| 2403 | +0.501860 | +0.347424 | yes |
| 2404 | +0.974718 | +0.896829 | yes |
| 2405 | -0.000036 | +0.041920 | yes |
| 2406 | +0.130286 | +0.117120 | yes |
| 2407 | +0.725336 | +0.685004 | yes |
| 2408 | +0.323659 | +0.316964 | yes |
| 2409 | +0.201298 | +0.229856 | yes |

The workflow exited red exactly as preregistered. The passing median and shuffled-control clauses do **not** override the failed 10/10 improvement clause.

## What subsequent spent-body controls established

The failure is not a single statement about the v0.9 circuit:

1. Removing **all edge, kick-self and drift thermal noise** still leaves v0.9 at 8/10 on the same bodies. Therefore the fresh failure is not evidence that `b=2e-5` thermal scaling itself failed to generalize.
2. Running the previously fresh-qualified **v0.8** architecture at its stricter `b_edge=b_self=1e-5` point on these same tasks is worse overall: only 7/10 clear +0.10 and 9/10 beat shuffled. Thus the 2400..2409 batch contains a harder benchmark tail than earlier cohorts.
3. An **ideal exact physical-credit** control with no quantization/noise/leakage/mirror/pass/credit errors gives seed 2405 only +0.052904 after the same 30 updates. The current absolute `10/10 >= +0.10` benchmark is therefore impossible on this cohort even for the ideal physical-credit algorithm.
4. Seed 2400 is different: ideal physical credit gives +0.864382, while mixed-signal v0.9 gives +0.025219. Seed 2400 is therefore a genuine circuit/support diagnostic body.

The formal result remains red. These controls change its interpretation, not its historical outcome.

## Next diagnosis

Seed 2400 is being split on the exact same fabricated draw. Thermal noise is held at zero and already-drawn static/support blocks are surgically removed **after construction** to avoid Monte Carlo redraw artifacts.

Seed 2405 is retained as evidence that future qualification should distinguish hardware fidelity from intrinsic task difficulty rather than demanding an absolute learning gain that the ideal reference itself cannot attain.
