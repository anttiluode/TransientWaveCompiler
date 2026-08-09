# TW-1A common-realization differential readout — result v0.1

Preregistration: `docs/COMMON_REALIZATION_DRIFT_PREREG_V01.md`

Workflow: `common-realization-drift-v01`

Data status: Stage A used already-spent seeds 970–979. Stage B fresh confirmation was not released because Stage A did not qualify.

## Challenge

Q/DAC/ADC 8/8/8 with the v0.7 50% simultaneous damage context, but reverse-operator drift restored to **0.002 RMS = 0.2%**.

Independent control redraws a reciprocal drift realization independently for REVERSE_PLUS and REVERSE_MINUS. The common-realization variant reuses one complete drifted reverse Q for both phase states.

## Result

### Independent reverse drift

FAIL:

- median exact DeltaC: **+0.1131**;
- median placement gap: **+0.0319**;
- 5/10 reached DeltaC >=0.10;
- exact final beat shuffled final in 6/10.

### Common PLUS/MINUS reverse drift

Strong improvement, but still FAIL:

- median exact DeltaC: **+0.6068**;
- median placement gap: **+0.3825**;
- 7/10 reached DeltaC >=0.10;
- exact final beat shuffled final in 8/10;
- two exact learners remained negative.

Therefore fresh seeds 990–999 were not consumed.

## Interpretation

Making PLUS and MINUS share one drifted reverse operator removes much of the false differential credit, but it does not fully restore the mathematical object being differentiated.

The normalized temporal-order objective is

`C(Q) = [E_AB(Q)-E_BA(Q)]/[E_AB(Q)+E_BA(Q)]`.

Its chain-rule gradient combines both energy gradients **at one common Q**. If the AB and BA physical measurements see different drift realizations, the host combines derivatives of different systems. Likewise, if forward propagation uses nominal Q while reverse retracing uses a drifted Q, exact retracing/adjoint consistency is broken even if PLUS and MINUS match each other.

The next positive control must therefore hold one quasi-static physical Q realization across the **entire contrast update**: AB forward/reverse PLUS/reverse MINUS and BA forward/reverse PLUS/reverse MINUS. Drift may change between optimizer updates, but not inside one gradient evaluation.
