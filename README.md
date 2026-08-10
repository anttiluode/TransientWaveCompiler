# TransientWaveCompiler

**A compiler/tuning toolkit for measured sparse reciprocal wave systems, with a separate mixed-signal research line for transient-wave computation.**

TransientWaveCompiler (TWC) grew out of [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField). The project has separated into two experimentally distinct tracks:

1. **TWC compiler / reciprocal-system tuner** — diagnose and optimize sparse symmetric wave/filter operators on an ordinary computer.
2. **TW-1A mixed-signal research backend** — investigate whether a reciprocal physical wave body can regenerate transient history and expose local training credit without storing an `O(N*T)` trajectory tape.

The compiler/tuner is now the application mainline. The chip remains a research result, including an important negative result that is worth preserving rather than hiding.

> **Active development:** [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08)

---

## Current application: measured reciprocal-system diagnosis

The filter layer fits a constrained reciprocal coupling matrix directly to complex measured `S11` and `S21` using exact inverse-matrix derivatives:

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)

d A^-1 / dp = -A^-1 (dA/dp) A^-1
```

Optional nominal/design values turn the recovered matrix into fitted-minus-design correction rows. Diagonal knobs represent resonator detuning; off-diagonal symmetric knobs represent reciprocal coupling.

This is **not** a claim that coupling-matrix extraction or computer-aided matrix diagnosis was invented here. Those are established fields. The project keeps an explicit [prior-art and claim-boundary document](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md).

### Strongest positive benchmark

The v0.5 benchmark deliberately adds systematic measurement/model mismatch:

```text
published seven-knob cross-coupled filter
+ uniform resonator loss
+ unknown S11 phase offset and slope
+ unknown S21 phase offset and slope
+ amplitude/phase measurement noise
```

Against the same 15 frozen cells:

```text
NAIVE  lossless matrix-only hidden-matrix recovery    0/15
AWARE  matrix + loss + phase nuisance recovery       15/15
```

The defensible result is specific: **under this frozen corruption, omitted nuisance was absorbed into false physical matrix corrections; joint physical+nuisance estimation recovered the hidden matrix on all 15 cells.**

Read the [v0.5 result](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md).

---

## Real `.s2p` measurement path

The active branch accepts ordinary two-port Touchstone data:

```text
.s2p
 -> physical frequency axis
 -> explicit bandpass or linear Omega normalization
 -> declared + nominal topology
 -> joint physical+nuisance fit
 -> fitted-minus-design diagnosis
```

For ordinary narrow-band coupled-resonator work it supports

```text
Omega = (f0/BW) * (f/f0 - f0/f).
```

The tuner also preserves the physical frequency mapping so a diagonal resonator diagnosis can be converted back into a physically meaningful frequency displacement. It deliberately does not invent Hz or screw travel for a coupling coefficient without an actuator calibration.

A ready starting topology is `examples/published_filter_vna_topology.json` on the active branch.

Read the [`twc-filter` / Touchstone workflow](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_TUNING.md).

The next decisive application falsifier is **real measured hardware with deliberate physical perturbations**, not another clean synthetic response.

---

## A sharper topology boundary: static response can be non-identifying

The preregistered v0.6 experiment hid one weak reciprocal edge, fit the knowingly wrong declared topology, and ranked absent edges from the residual. Four of five hidden-edge locations worked across every optimizer start. One hidden edge, `(2,5)=-0.025`, ranked **8, 8, 7** and failed systematically:

```text
true hidden edge ranked #1       12/15
true hidden edge ranked top-3    12/15
augmented recovery               12/15
frozen primary discovery clause  FAIL
```

A later full candidate-conditioned refit did **not** rescue that case. The true edge still lost to alternative realizations and its fitted value collapsed toward zero.

The exact-Jacobian microscope then found why. At the actual failed compensated fit, define

```text
eta = ||(I - P_J) g_edge|| / ||g_edge||
```

using the realified complex-response Jacobian. For hidden `(2,5)`:

```text
eta with 7 physical + 5 nuisance columns     ~1e-15
eta with the 7 physical columns only         3.4e-15
```

So the missing edge's entire first-order response direction is already contained in the existing **physical coupling-matrix** tangent space to machine precision. This is not primarily a cable-delay/nuisance problem and not merely bad numerical conditioning.

Adding `S22` does not break this static ambiguity: the physical-only novelty remains about `3e-15`.

The useful interpretation is therefore broader than “the local derivative scan failed”:

> **A static S-parameter response can identify an equivalence class of coupling-matrix realizations rather than a unique physical graph.**

Coupling-matrix realization non-uniqueness/similarity transformations are established prior art. TWC's useful role here is to **measure the ambiguity at the fitted point** and refuse to manufacture confidence from a flat rank.

Known physical perturbations can anchor the internal coordinate system. On the frozen failed solution, adding known resonator-detuning states breaks the exact alias, although only weakly. This motivates a diagnosis workflow that reports identifiability and recommends a measurement/perturbation when the requested physical distinction is not supported by the current data.

Read:

- [v0.6 result](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md)
- [identifiability / aliasing microscope](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_IDENTIFIABILITY_ALIASING_2026-08-10.md)

---

## The product behavior this points to

Instead of always returning a ranked hidden-edge list:

```text
fit declared physical model + nuisance
 -> compute identifiability of requested physical diagnoses
 -> identifiable: report the correction / candidate evidence
 -> aliased: report an equivalence or indistinguishability set
 -> recommend the next measurement or known perturbation that best breaks it
```

For real data the natural metric should become noise-weighted rather than purely Euclidean, so “identifiable” means distinguishable at the actual measurement noise floor, not merely algebraically nonzero.

---

## The hardware result is also useful — including the failure

The TW-1A work produced concrete recurrence transforms, reciprocal rank-one edge lowering, switched-cap circuit simplifications, ngspice pass/fail gates, common/difference reverse storage, and a kick-drift representation.

But the attractive small-cap stochastic on-device adjoint did not survive controlled task × fabrication × dynamic-noise tests.

At one fixed parameter point, even averaging **1024** independently noisy physical gradients left a median cosine of only **0.280** to the clean gradient, with evidence of a bias component.

> **A stochastic physical adjoint is not automatically an adjoint of a stochastic forward history.**

The deterministic echo algebra can be correct while the reverse traversal still fails to adjoint the particular forward trajectory when the two traversals receive different stochastic perturbation histories. More capacitance and brute-force averaging did not rescue the attractive operating point.

That parks the chip honestly without discarding the circuit work.

Read:

- [Current hardware status](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/HARDWARE_STATUS_2026-08-09.md)
- [Fixed-theta gradient microscope](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_RESULT.md)

---

## Why the two tracks still belong together

They share the same structural object:

```text
parameterized sparse symmetric operator
        |
        +-- reciprocal local edge stamps
        +-- constrained topology
        +-- exact local derivatives
        +-- forward response
        `-- inverse / adjoint sensitivity
```

The physical backend asks whether that structure can be exploited directly in matter. The compiler/tuner asks what can already be done reliably on a computer with measured reciprocal systems.

The second question is currently producing the stronger application.

---

## Repository status

`main` is the stable public landing page. The active research/compiler branch is [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08), which contains the current tuner, Touchstone reader, identifiability tools, benchmarks, circuit research record, and executable tests.

A future code promotion to `main` should be a curated compiler release rather than a blind merge of the full research history.
