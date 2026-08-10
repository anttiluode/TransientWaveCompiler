# Filter identifiability / realization-aliasing microscope

Date: 2026-08-10

Status: **post-hoc mechanism result / not a qualifying benchmark**

Source failure: v0.6 case `4303`, hidden reciprocal edge `(2,5)=-0.025`, start A from frozen workflow `31357543837`.

## Why this microscope was run

The v0.6 local missing-edge scorer failed systematically on one hidden edge. A later candidate-conditioned full-refit microscope also failed to rescue that case: even when the true edge was supplied as a candidate, re-optimization drove its fitted value toward zero and competing wrong models obtained nearly the same loss.

That raised a sharper question than optimizer quality:

> Is the missing edge's response direction already contained in the tangent space of the fitted wrong model?

For a real-parameter model with complex response, form the **realified** response Jacobian

```text
J = d [Re S, Im S] / d theta
```

and candidate derivative `g`. Define local novelty

```text
eta = ||(I - P_J) g|| / ||g||,
```

where `P_J` projects onto the numerical column space of `J`.

`eta ~= 0` means the candidate is locally aliased by the parameters already present. `eta ~= 1` means its first-order response direction is almost wholly new.

This is a local first-order identifiability diagnostic, not a proof of global uniqueness.

## Direct result on the actual failed v0.6 optimum

For hidden `(2,5)` using measured-model channels `S11 + S21`, with the seven fitted matrix parameters and all five fitted nuisance parameters in `J`:

```text
candidate ||g||                         26.8074
||(I-P_J)g||                            ~3.1e-14
eta                                     ~1.2e-15
projected energy fraction               ~1.000000000000
numerical J rank                        12 / 12
J condition number                      ~160.6
```

So the v0.6 failure is not merely that the local probe happened to point poorly:

> **At the compensated wrong-model solution, the entire first-order `(2,5)` response is already in the fitted model tangent space to machine precision.**

That directly explains why the later full candidate-conditioned refit could prefer to leave the true edge near zero.

## The alias is already physical — nuisance is not the cause

The stronger microscope removed nuisance columns from `J`.

For `(2,5)` with **only the seven existing physical coupling-matrix columns**:

```text
eta                                     3.41e-15
physical J rank                         7 / 7
physical J condition number             6.84
```

Adding loss or phase nuisance does not create the degeneracy; it is already present in the physical coupling-matrix realization.

The least-squares combination of existing physical derivative columns that reproduces the `(2,5)` derivative has relative residual `8.21e-16` and coefficients approximately

```text
mS1   +0.000000
m12   +0.165394
m23   +0.861100
m34   +0.733718
m4L   -0.000000
m14   -0.847154
mSL   +0.000000
```

This is consistent with a **coupling-matrix realization / internal-basis gauge direction**: a physical coupling derivative can be redistributed into a coordinated change of existing matrix entries while preserving the port response to first order.

Coupling-matrix realization non-uniqueness and similarity transformations are established prior art. The claim here is not that TWC discovered that phenomenon. The useful result is that the exact response Jacobian exposes the ambiguity quantitatively at the actual failed fit.

## S22 does not rescue this static ambiguity

Adding `S22` to the response does not make the hidden edge locally identifiable.

For `S11 + S21 + S22`, using physical columns only:

```text
eta                                     2.83e-15
physical J condition number             4.10
```

The same physical-column combination reproduces the candidate derivative with relative residual `1.33e-15`.

A conservative test that also gives S22 its own phase-offset and phase-slope nuisance remains machine-zero novelty.

Therefore, for this specific static realization ambiguity:

> **more portside response information from S22 is not enough; the missing information is the physical coordinate system of the internal resonators.**

## Not every absent edge is aliased

At the same compensated v0.6 point, the physical-only novelty scan found two essentially exact aliases among the absent reciprocal edges:

```text
(0,3)    eta ~ 1.5e-15
(2,5)    eta ~ 3.4e-15
```

The other absent edges had physical-only novelty approximately `1.0`.

So a single static response can make some candidate interactions locally distinguishable and others members of a realization-equivalent tangent class.

This is why a raw ranked list is the wrong product abstraction when candidate scores are flat or novelty is below the measurement information floor.

## Controlled perturbations can anchor the physical coordinates

The same frozen failed solution was evaluated under hypothetical known resonator-detuning states.

The already-preregistered v0.7 state set

```text
BASE
R1 +0.080
R2 -0.070
R4 +0.060
```

raises `(2,5)` novelty from machine zero to

```text
eta(S11,S21)                 0.04366
eta(S11,S21,S22)             0.04832
```

Thus the exact static alias is broken, although only weakly.

A scan of BASE plus one `+/-0.08` resonator detuning showed:

```text
R4 detuning      eta ~ 0.05354
R2 detuning      eta ~ 0.05326
R1 detuning      eta ~ machine zero
R3 detuning      eta ~ machine zero
```

Node `5` in this six-node explicit-port model is the **load**, not a fifth resonator, so there is no `R5` detuning state. The hidden `(2,5)` interaction is resonator-2 to load; v0.7 already includes an R2 perturbation. Interestingly, R4 is slightly stronger by this local normalized metric at the frozen compensated point.

This supports the more general experiment-design rule:

> Do not choose perturbations merely because they are geometrically adjacent to the suspected edge. Choose known physical perturbations that add a response direction outside the compensated model tangent space.

## Important refinement: normalized novelty is not the whole design objective

The ratio `eta` measures fractional novelty, but real detection also depends on absolute residualized sensitivity and measurement noise.

For example, a larger multi-state experiment can have a slightly lower normalized `eta` while producing a larger absolute `||(I-P_J)g||` because it contains more observations.

For real VNA experiment design the natural next form is therefore noise-whitened:

```text
Jw = W^(1/2) J
gw = W^(1/2) g
eta_w = ||(I-P_Jw) gw|| / ||gw||
```

and the absolute residualized sensitivity / Fisher information should be reported beside `eta_w`.

Bounds and nonlinear compensation also remain outside this local tangent calculation.

## Product consequence

The useful workflow is no longer

```text
one S-parameter trace
-> rank all hidden edges
-> declare winner
```

It is

```text
fit declared physical model + nuisance
-> compute identifiability of requested diagnoses
-> if identifiable: report correction / candidate evidence
-> if aliased: report an equivalence/indistinguishability set
-> recommend the next measurement or known perturbation that best breaks it
```

In short:

> **A static filter response may identify an equivalence class of coupling-matrix realizations rather than a unique physical graph. A controlled perturbation of a known physical resonator can act as a coordinate anchor.**

That is a more honest and more useful diagnostic-tool behavior than manufacturing confidence from a flat rank.

## Code / evidence

- `transientwave/identifiability.py`
- `experiments/filter_identifiability_alias_microscope.py`
- `experiments/filter_identifiability_gauge_microscope.py`
- workflow `filter-identifiability-alias-microscope`, run `31359833463`
- filter identifiability CI passed in run `31359641322`
