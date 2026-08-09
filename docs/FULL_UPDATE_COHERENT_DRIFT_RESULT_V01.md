# TW-1A full-update coherent drift — result v0.1

Preregistration: `docs/FULL_UPDATE_COHERENT_DRIFT_PREREG_V01.md`

Workflow: `full-update-coherent-drift-v01`

## Challenge

Rank-one Q/DAC/ADC 8/8/8 with the v0.7 50% damage context and **0.2% RMS spatial operator variation**, but one complete drifted Q realization is frozen across the entire AB+BA physical contrast-gradient evaluation and redrawn only between optimizer updates.

## Stage A — spent seeds 970–979

**PASS.**

- median exact DeltaC: **+0.7213**;
- median placement gap: **+0.8109**;
- 9/10 reached DeltaC >=0.10;
- exact final contrast beat shuffled final in 10/10;
- every exact learner improved.

This released the preregistered fresh block.

## Stage B — fresh seeds 990–999

**Registered result: FAIL narrowly.**

- median exact DeltaC: **+0.6097**;
- median placement gap: **+0.5511**;
- 9/10 reached DeltaC >=0.10;
- exact final contrast beat shuffled final in **10/10**;
- all values finite;
- but seed 998 had `DeltaC = -0.02885`, violating the frozen requirement that every exact learner improve.

All other fresh seeds improved by at least +0.2426.

## Interpretation

The progression is strong evidence that the damaging quantity is not absolute quasi-static Q error by itself:

1. independent 0.2% PLUS/MINUS drift fails badly;
2. sharing Q only across PLUS/MINUS greatly improves performance but still fails on the spent block;
3. sharing one Q across the **whole AB+BA gradient evaluation** passes the spent block and nearly passes fresh confirmation.

This matches the mathematical object being estimated. The normalized contrast gradient combines `E_AB(Q)`, `dE_AB(Q)`, `E_BA(Q)`, and `dE_BA(Q)` and therefore requires those terms to refer to one physical operator realization.

The severe 10-ppm v0.8 requirement is thus best understood as a **within-gradient differential stability** requirement. Full-gradient coherence appears capable of relaxing the absolute Q variation by roughly two orders of magnitude, though 0.2% itself has not yet met the strict all-positive robustness criterion.

The next development step may use only the now-spent 990–999 block to locate the full-update-coherent drift boundary, then preregister one inward point on new seeds.
