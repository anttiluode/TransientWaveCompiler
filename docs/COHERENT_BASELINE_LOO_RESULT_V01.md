# TW-1A coherent zero-drift baseline — leave-one-out diagnostic result v0.1

Data status: development-only, already-spent seeds 990–999.

This diagnostic was run after the full-update-coherent drift-boundary experiment showed that the same seed 998 failed slightly even at **zero coherent drift** and continued to fail across 0–0.5% coherent Q variation.

## Baseline context

Full-gradient operator drift was set to zero. The remaining simultaneous v0.7 50% damage terms were retained:

- Q/DAC/ADC = 8/8/8;
- leakage = 0.0005/tick;
- leakage CV = 0.50;
- mirror error = 0.15;
- credit noise = 0.25;
- credit offset = 0.00015;
- state noise = 5e-9 FS.

Baseline result:

- strict predicate: FAIL;
- median exact DeltaC: +0.6312;
- median placement gap: +0.6173;
- 9/10 DeltaC >=0.10;
- exact final > shuffled final in 10/10;
- seed 998 DeltaC = -0.01628.

## Leave-one-damage-out result

Removing each term one at a time:

| removed term | predicate | seed 998 DeltaC | interpretation |
|---|---|---:|---|
| mean leakage | PASS | +0.00386 | rescues all-positive tail |
| leakage CV | FAIL | -0.01155 | not the tail source |
| mirror error | FAIL | -0.01347 | not the tail source |
| zero-mean credit noise | PASS | +0.02372 | rescues tail |
| credit DC offset | PASS | +0.04901 | rescues tail |
| state noise | PASS | +0.01376 | rescues tail |

No unique single damage mechanism remains. Several different small stochastic/systematic terms can move the same marginal geometry across the strict all-positive threshold.

## Conclusion

The residual seed-998 failure is an **interaction/robustness tail**, not evidence for a tighter coherent-drift limit. In this spent block, changing coherent Q variation from 0 to 0.5% had little effect compared with removing small leakage/noise/bias terms.

This closes the tolerance-search branch for now. The earned hardware contract should therefore distinguish:

- a demonstrated 10-ppm within-gradient independent-mismatch corner (v0.8);
- a strong architectural requirement that all terms in one physical gradient evaluation refer to one common reciprocal operator realization;
- an unresolved absolute quasi-static coherent-Q tolerance;
- independent one-axis noise/leakage/bias boundaries that must not be assumed to compose as a Cartesian box.
