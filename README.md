# TransientWaveCompiler

**A compiler/tuning toolkit for sparse reciprocal wave systems, with a separate mixed-signal research line for transient-wave computation.**

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

Optional nominal/design values turn the recovered matrix into fitted-minus-design correction rows. A diagonal knob can represent resonator detuning; an off-diagonal symmetric knob represents reciprocal coupling.

This is **not** a claim that coupling-matrix extraction or computer-aided matrix diagnosis was invented here. Those are established fields. The project now keeps an explicit [prior-art and claim-boundary document](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md).

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

The active branch now has a two-port Touchstone path:

```text
.s2p
 -> physical frequency axis
 -> explicit bandpass or linear Omega normalization
 -> declared + nominal topology
 -> joint physical+nuisance fit
 -> fitted-minus-design diagnosis
```

For ordinary narrow-band coupled-resonator work it supports the classical mapping

```text
Omega = (f0/BW) * (f/f0 - f0/f).
```

A ready starting topology with resonator-detuning knobs and nuisance bounds is included at `examples/published_filter_vna_topology.json` on the active branch.

Read the [`twc-filter` / Touchstone workflow](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_TUNING.md).

The next decisive application falsifier is now **real measured hardware with deliberate physical perturbations**, not another clean synthetic response.

---

## Parasitic topology discovery: promising, but the first general gate failed

The preregistered v0.6 experiment hid one weak reciprocal edge, fit the knowingly wrong declared topology, and ranked every absent edge by an exact local residual-sensitivity probe.

Result:

```text
true hidden edge ranked #1       12/15
true hidden edge ranked top-3    12/15
augmented recovery               12/15
frozen primary discovery clause  FAIL
```

Four of five hidden-edge locations were #1 and recovered across every optimizer start. One hidden edge, `(2,5)=-0.025`, ranked **8, 8, 7** and failed systematically.

So automatic topology discovery is **not** promoted as a product feature. The negative result says something useful: once a flexible wrong topology has compensated by moving its allowed matrix/nuisance variables, the exact local derivative at that fitted point need not identify the omitted physical interaction.

Read the [v0.6 result](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md).

The next research estimator is candidate-conditioned refitting/model comparison rather than a one-shot local derivative scan.

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

`main` is the stable public landing page. The active research/compiler branch is [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08), which contains the current tuner, Touchstone reader, benchmarks, circuit research record, and executable tests.

A future code promotion to `main` should be a curated compiler release rather than a blind merge of the full research history.
