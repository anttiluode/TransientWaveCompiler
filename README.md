# TransientWaveCompiler

**A reciprocal-system compiler and diagnosis toolkit that grew out of an attempt to turn the Geometric Neuron into physical hardware.**

TransientWaveCompiler (TWC) grew out of [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField). The work split into two experimentally distinct tracks:

1. **TWC compiler / reciprocal-system diagnosis** — sparse symmetric operators, exact sensitivities, measured/simulated response fitting, nuisance separation, and identifiability reporting.
2. **TW-1A mixed-signal research backend** — a physical reciprocal transient-wave computer / learning experiment.

The compiler is now the practical mainline. The chip line is parked with a documented negative stochastic-adjoint result rather than hidden.

> **Active development:** [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08)

---

## What is this useful for?

### Filter / resonator diagnosis

TWC can take a declared/nominal reciprocal coupling topology and complex `S11` / `S21`, then fit physical coupling and resonator-detuning parameters using exact inverse-matrix sensitivities.

```text
Touchstone .s2p or simulated S-parameters
      ↓
frequency normalization
      ↓
declared + nominal topology
      ↓
physical matrix + supported nuisance fit
      ↓
fitted-minus-design diagnosis
```

The active branch supports ordinary two-port Touchstone data, classical bandpass normalization, linear normalization, and physical-frequency diagnosis for diagonal resonator terms.

### Separate nuisance from physics

The fitter can carry resonator loss and independent S11/S21 phase offset/slope variables alongside the physical matrix.

On the frozen v0.5 corruption benchmark:

```text
matrix-only hidden-matrix recovery            0/15
matrix + supported nuisance recovery         15/15
```

The useful point is practical: supported measurement/model mismatch is represented explicitly instead of being silently absorbed into false physical corrections.

### Audit whether a topology is identifiable before measuring it

A static two-port response does not always uniquely identify a literal internal physical graph. Classical coupling-matrix similarity transformations can generate response-equivalent internal realizations.

TWC now contains a topology-only **negative-capability audit**. It forms the internal rotation generators, applies the declared zero pattern as constraints, releases one proposed absent edge, and asks whether a response-equivalent gauge direction reappears.

For the published four-resonator folded topology, using **no S-parameter data at all**, the audit predicts exactly two statically aliased absent edges:

```text
(0,3)  -> R1 <-> R3 internal rotation
(2,5)  -> R2 <-> R4 internal rotation
```

Those are exactly the two machine-zero physical aliases found independently by the response-Jacobian microscope.

It also says which known resonator detuning anchors each exact ambiguity:

```text
(0,3)  -> perturb R1 or R3
(2,5)  -> perturb R2 or R4
```

Read the [topology gauge capability map](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md).

### Report equivalence instead of false certainty

When a static measurement cannot distinguish two physical realizations, the desired behavior is not a confident but arbitrary ranking. It is closer to:

```text
STATIC RESPONSE CANNOT UNIQUELY LABEL THIS PHYSICAL EDGE
reason: response-equivalent realization freedom
suggested next state: perturb resonator Rk and measure again
```

That is useful even when the answer is negative: **more optimization cannot create information that the measurement does not contain.**

### Compare repeated or deliberately perturbed states

The active branch includes tools for summarizing repeated fits and comparing baseline-versus-perturbed results. With real or simulated repeated measurements, these can separate stable physical movement from measurement-chain nuisance and baseline scatter.

### Simulation / EM-model debugging

A VNA is not required to use the compiler itself. Simulated or EM-generated `.s2p` data can be fed through the same diagnosis path to compare a realized/simulated response with a nominal coupling model.

A VNA becomes necessary for the **external hardware validation** question: does the diagnosis remain correct when a real resonator is deliberately changed and swept again?

---

## What became of the Geometric Neuron / chip idea?

It did not simply turn into a microwave-filter project.

The original physical-computation work forced a reusable abstraction into existence:

```text
geometry / topology
      ↓
sparse reciprocal operator
      ↓
forward response or transient
      ↓
exact local parameter sensitivity
      ↓
software compiler or physical lowering
```

The two sides then separated under experiment.

The TW-1A hardware work found real deterministic echo algebra and circuit simplifications, but the attractive small-cap stochastic physical-adjoint claim failed controlled tests. The software side survived because sparse reciprocal operators and exact sensitivities remain useful whether or not a physical substrate can supply the desired stochastic adjoint.

The microwave-filter domain became a deliberately classical external testbed for the compiler idea.

> **The current outcome is a documented boundary on the hardware hypothesis plus a usable reciprocal-system compiler/diagnosis toolkit.**

---

## Current filter evidence

The core explicit-port model uses

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)

d A^-1 / dp = -A^-1 (dA/dp) A^-1
```

The evidence ladder currently reads:

```text
v0.1  published 3-resonator couplings                   5/5 exact
v0.2  resonator offsets + couplings                     5/5 exact
v0.3  published 6x6 cross-coupled topology              5/5 exact
v0.4  zero-mean repeated complex noise                 15/15 robust
v0.5  systematic loss + phase nuisance                 15/15 aware
                                                       0/15 naive matrix recovery
v0.6  hidden parasitic local discovery                 12/15 top-1/recovery
                                                       PRIMARY DISCOVERY FAIL
v0.7  four known physical states                        9/15 top-1
                                                        9/15 top-3
                                                        9/15 recovery
                                                       PRIMARY DISCOVERY/RECOVERY FAIL
```

v0.7 is especially informative. The three non-gauge hidden-edge classes were perfect across all starts. Both topology-gauge classes failed across all starts, even though the known perturbation schedule breaks their exact similarity gauge in principle.

So the present boundary is:

> **Breaking an exact realization gauge is necessary for unique physical diagnosis, but it is not sufficient for robust finite-noise topology discovery after a flexible wrong-model fit has compensated.**

Read:

- [v0.6 result](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md)
- [v0.7 result](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md)
- [exact realization-rotation proof](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_REALIZATION_ROTATION_PROOF_2026-08-10.md)
- [prior-art / claim boundary](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md)

Classical coupling-matrix similarity transformations and topology conversion are prior art. TWC does not claim those rotations. The narrower software result is the explicit capability audit and refusal to over-identify a physical topology when the model/measurement cannot support it.

---

## Touchstone workflow

The active branch has a normal CLI path:

```text
.s2p
 -> physical frequency axis
 -> explicit bandpass or linear Omega normalization
 -> declared + nominal topology
 -> joint physical+nuisance fit
 -> fitted-minus-design diagnosis
```

For ordinary narrow-band coupled-resonator work:

```text
Omega = (f0/BW) * (f/f0 - f0/f)
```

A ready starting topology is `examples/published_filter_vna_topology.json` on the active branch.

Read the [`twc-filter` / Touchstone guide](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_TUNING.md).

---

## TW-1A hardware result

The hardware line produced concrete recurrence transforms, reciprocal edge lowering, switched-cap circuit simplifications, ngspice pass/fail gates, common/difference reverse storage, and a kick-drift representation.

But at the attractive small-cap stochastic operating point, controlled task × fabrication × dynamic-noise experiments did not preserve the physical adjoint.

At one fixed parameter point, even averaging **1024** independently noisy physical gradients left a median cosine of only **0.280** to the clean gradient, with evidence of a bias component.

> **A stochastic physical adjoint is not automatically an adjoint of a stochastic forward history.**

Read the [hardware status](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/HARDWARE_STATUS_2026-08-09.md).

---

## Current stopping line

The software-only topology-discovery hit-rate ladder stops at the failed v0.7 gate. There is no planned v0.8 synthetic rescue merely to make the percentage go up.

The next decisive external experiment would require a real reciprocal resonator/filter measured in repeated known physical states. Until that hardware/data exists, the current software results stand on their own:

- reciprocal sparse-operator/compiler structure;
- exact inverse-matrix sensitivities;
- nuisance-aware physical fitting;
- Touchstone ingestion and physical-frequency diagnosis;
- repeated-state comparison;
- response-space identifiability diagnostics;
- topology-only negative-capability / perturbation-anchor analysis;
- retained positive and negative preregistered evidence.

`main` is the stable public landing page. Active research/code remains on [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08).
