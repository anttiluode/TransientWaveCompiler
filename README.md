# TransientWaveCompiler

**A compiler/tuning toolkit for sparse reciprocal wave systems, with a separate mixed-signal research line for transient-wave computation.**

TransientWaveCompiler (TWC) grew out of [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField). The project has now separated into two experimentally distinct tracks:

1. **TWC compiler / reciprocal-system tuner** — diagnose and optimize sparse symmetric wave and filter operators on an ordinary computer.
2. **TW-1A mixed-signal research backend** — investigate whether a reciprocal physical wave body can regenerate transient history and expose local training credit without storing an `O(N*T)` trajectory tape.

The compiler/tuner is now the application mainline. The chip remains a research result, including an important negative result that is worth preserving rather than hiding.

> **Active development:** [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08)

---

## Current headline: filter tuning becomes diagnosis instead of search

The current filter layer fits a constrained reciprocal coupling matrix directly to complex measured `S11` and `S21` using exact inverse-matrix derivatives:

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)

d A^-1 / dp = -A^-1 (dA/dp) A^-1
```

A diagonal matrix knob is a resonator-frequency correction. An off-diagonal symmetric knob is a reciprocal coupling correction. The goal is not merely to make the trace look right, but to recover **which physical resonators and couplings are wrong**.

The strongest current benchmark deliberately adds systematic measurement/model mismatch:

```text
published seven-knob cross-coupled filter
+ uniform resonator loss
+ unknown S11 phase offset and slope
+ unknown S21 phase offset and slope
+ amplitude/phase measurement noise
```

Fitting only the physical matrix gives:

```text
NAIVE hidden-matrix recovery   0/15
```

Jointly fitting the physical matrix and measurement nuisance gives:

```text
AWARE systematic recovery     15/15
```

That is the useful product-side result: **measurement-chain physics must be separated from physical coupling corrections, or calibration/reference-plane error can be converted into false tuning instructions.**

The active branch now exposes that nuisance-aware model through `twc-filter` and includes a two-port `.s2p` Touchstone path:

```text
inspect-s2p -> explicit frequency normalization -> declared topology -> joint physical+nuisance fit
```

Read:

- [Systematic nuisance benchmark v0.5](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md)
- [`twc-filter` / Touchstone workflow](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/FILTER_TUNING.md)

The next external falsifier is now **real measured hardware**, not another synthetic trace. In parallel, the next structural question is **unknown parasitic topology discovery**: can the residual identify a reciprocal edge that the declared model forgot?

---

## The hardware result is also useful — including the failure

The TW-1A work produced concrete recurrence transforms, reciprocal rank-one edge lowering, switched-cap circuit simplifications, ngspice pass/fail gates, common/difference reverse storage, and a kick-drift representation.

But the attractive small-cap stochastic on-device adjoint did not survive controlled task × fabrication × dynamic-noise tests.

At one fixed parameter point, even averaging **1024** independently noisy physical gradients left a median cosine of only **0.280** to the clean gradient, with evidence of a bias component.

The important boundary is:

> **A stochastic physical adjoint is not automatically an adjoint of a stochastic forward history.**

The deterministic echo algebra can be correct while the reverse traversal still fails to adjoint the particular forward trajectory when the two traversals receive different stochastic perturbation histories. More capacitance and brute-force averaging did not rescue the attractive operating point.

That result parks the chip honestly without discarding the circuit work.

Read the evidence map:

- [Current hardware status](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/HARDWARE_STATUS_2026-08-09.md)
- [Fixed-theta gradient microscope](https://github.com/anttiluode/TransientWaveCompiler/blob/agent/tw1a-common-diff-v08/docs/BENCHMARK_V09_FIXED_THETA_GRADIENT_SNR_RESULT.md)

---

## Why these two tracks still belong together

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

`main` is now the stable public landing page. The active research/compiler branch is [`agent/tw1a-common-diff-v08`](https://github.com/anttiluode/TransientWaveCompiler/tree/agent/tw1a-common-diff-v08), which contains the current tuner, Touchstone reader, benchmarks, circuit research record, and executable tests.

A future promotion to `main` should be a curated compiler release rather than a blind merge of the full research history.
