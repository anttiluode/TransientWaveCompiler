# v0.6 parasitic-topology conditional-refit microscope — post-hoc result

Date: 2026-08-10

Workflow run: `31358306980`

Status: **POST-HOC / NON-QUALIFYING**

This experiment used the already-inspected v0.6 failure case `4303` and therefore is not a new benchmark or success/failure gate. Its purpose was only to identify the mechanism behind the frozen v0.6 failure.

## Question

In v0.6 the hidden reciprocal edge

```text
(2,5) = -0.025
```

ranked `8,8,7` under the local residual-probe rule.

A simple possible explanation was that the correct edge was present in the residual but a one-step derivative/probe was too local. The post-hoc microscope therefore gave **every absent reciprocal edge** a full candidate-conditioned refit:

```text
wrong-topology stage-1 solution
+ one candidate absent edge
-> jointly re-optimize declared matrix + candidate + nuisance
-> rank by final measured complex-response loss
```

All eight candidates had exactly the same model size and optimization budget.

## Result

The hidden true edge was still not selected:

```text
start A   local rank 8   conditional-refit rank 7
start C   local rank 8   conditional-refit rank 5
start D   local rank 7   conditional-refit rank 3

true edge top-1 after conditional refit: 0/3
```

The true candidate also collapsed toward zero rather than recovering `-0.025`:

```text
start A   fitted true candidate  -0.000152
start C   fitted true candidate  -0.001962
start D   fitted true candidate  -0.001792
```

Its base seven-knob matrix remained badly displaced:

```text
start A   base matrix RMSE  0.013179
start C   base matrix RMSE  0.012414
start D   base matrix RMSE  0.012520
```

## Candidate-loss degeneracy

The best and second-best *wrong* candidate models were almost indistinguishable in final loss:

```text
start A   best/second loss ratio  0.9998497
start C   best/second loss ratio  0.9999359
start D   best/second loss ratio  0.9997552
```

That is a much stronger warning than the local ranking alone. The static measured response admits several nearly equivalent compensated models at the current parameterization/noise level.

## Interpretation

The v0.6 failure is therefore **not rescued by simply replacing the local derivative scan with one ordinary candidate-conditioned refit initialized from the fitted wrong model.**

The evidence is consistent with a deeper single-state identifiability/basin problem:

> once the declared physical matrix and nuisance have compensated for the omitted `(2,5)` interaction, adding the correct candidate at nearly zero strength does not provide enough information or optimization leverage to reconstruct the hidden physical state from that same static response.

This does not prove that the hidden edge is mathematically unidentifiable from noiseless S-parameters under every formulation. It establishes only that the present bounded direct-response optimizer, from these compensated starts and this single measured state, does not recover it.

## Why the next gate changes the experiment instead of the optimizer

A natural brute-force response would be to add random candidate multistarts, larger initialization magnitudes, more iterations, or another global optimizer. Those may improve search, but they do not address the nearly degenerate model evidence directly.

The more informative next question is to add **new physical information**.

The microwave-filter literature already uses deliberate resonator perturbations/detuning to expose parasitic coupling structure. TWC's next synthetic gate should therefore use multiple measured states of the same hidden reciprocal topology:

```text
shared unknown physical topology
+ known deliberate resonator perturbation state A
+ known deliberate resonator perturbation state B
+ known deliberate resonator perturbation state C
-> joint candidate model comparison across all states
```

The parasitic edge and base physical matrix are shared. The known perturbations change the response geometry so a false compensating model that works in one state must also explain the others.

A qualifying v0.7 benchmark must use fresh hidden cases/noise seeds and be preregistered before those outcomes are inspected.

## Boundary

This post-hoc result must not be counted in the evidence ladder as an independent benchmark. Its only valid conclusion is mechanistic:

> **The frozen v0.6 failure is deeper than one-step local probe blindness; ordinary same-state candidate refitting from the compensated solution also fails to identify the hidden edge.**
