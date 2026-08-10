# TransientWaveCompiler

**A reciprocal-system compiler and diagnosis toolkit that grew out of an attempt to turn the Geometric Neuron into physical hardware.**

TransientWaveCompiler (TWC) began from the question behind [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField): can the geometry and reciprocity of a physical wave system do useful computation and expose local learning signals?

That question split into two experimentally different projects:

1. **TWC compiler / reciprocal-system diagnosis** — represent sparse symmetric wave systems, compute exact sensitivities, fit measured response, separate supported measurement nuisance from physical parameters, and say when a proposed physical diagnosis is not identifiable.
2. **TW-1A mixed-signal research backend** — test whether a reciprocal physical wave body can regenerate transient history and provide local training credit without storing an `O(N*T)` trajectory tape.

The first line is now the practical mainline. The second is parked with a useful negative result rather than hidden.

---

## What can this be used for?

### 1. Diagnose a reciprocal filter from complex S-parameters

Given a declared/nominal coupling topology and complex `S11` / `S21`, TWC can fit physical coupling and resonator-detuning parameters directly.

```text
Touchstone .s2p
      ↓
explicit frequency normalization
      ↓
declared + nominal reciprocal topology
      ↓
physical matrix + supported nuisance fit
      ↓
fitted-minus-design corrections
```

This can be used with **measured VNA data or simulated/EM-generated S-parameters**. A physical VNA is therefore required for hardware validation, but not for using the compiler on simulated designs.

### 2. Keep measurement-chain errors from masquerading as physical faults

The fitter can carry resonator loss and independent S11/S21 phase offset/slope nuisance alongside the physical coupling matrix.

In the frozen v0.5 synthetic benchmark:

```text
matrix-only fit                       hidden-matrix recovery   0/15
matrix + supported nuisance fit       hidden-matrix recovery  15/15
```

The useful engineering lesson is not that this is the first nuisance-aware extraction method. It is that **this implementation keeps the distinction explicit in the fitted object and diagnosis output.**

### 3. Audit a topology before taking a measurement

A static two-port response does not always uniquely label the internal physical coupling graph. Classical coupling-matrix similarity transformations can move coupling strength between response-equivalent internal realizations. citeturn206419search1turn206419search2turn206419search0

TWC now turns that classical freedom into a negative-capability test:

```text
declared topology + nominal matrix
      ↓
internal so(N) rotation generators
      ↓
declared zeros fix the realization gauge
      ↓
release one proposed parasitic edge
      ↓
does a gauge direction reappear?
```

If yes, the software reports that the candidate is **statically gauge-aliased** rather than manufacturing a confident topology rank.

For the published four-resonator folded example, the topology-only calculation—using no S-parameter data—predicts exactly two aliased absent edges:

```text
(0,3)  frees R1 <-> R3 rotation
(2,5)  frees R2 <-> R4 rotation
```

Those are exactly the two machine-zero aliases found independently by the response-Jacobian microscope.

See [`docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md`](docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md).

### 4. Design a measurement that can break an exact ambiguity

For a gauge-aliased candidate, the same calculation can identify physical resonator coordinates whose known perturbation fixes the ambiguity.

For the folded example:

```text
candidate (0,3)  -> detune R1 or R3
candidate (2,5)  -> detune R2 or R4
```

That does **not** guarantee practical detection in noise. It establishes the more basic fact that the proposed additional state actually anchors the internal coordinate being mixed.

The next practical design score would compare the remaining orthogonal candidate signal with real sweep covariance / noise, rather than treating gauge-breaking itself as sufficient.

### 5. Report equivalence instead of false certainty

When several physical descriptions are response-equivalent, the correct output is not necessarily:

```text
#1 candidate A
#2 candidate B
```

A more useful engineering report is:

```text
STATIC RESPONSE CANNOT UNIQUELY LABEL THIS PHYSICAL EDGE
reason: response-equivalent internal realization freedom
suggested coordinate anchor: perturb resonator Rk and sweep again
```

This is useful even when the answer is negative: it tells the engineer when **more optimization cannot create information that the measurement does not contain.**

### 6. Compare repeated sweeps or controlled before/after states

The repository includes analysis tools for repeated fit results and baseline-versus-perturbed comparisons. With real or simulated repeated measurements they can separate:

- stable physical parameter shifts;
- fitted nuisance variation;
- the size/sign of a deliberate perturbation;
- repeatability relative to baseline scatter.

### 7. Use the code as an executable coupling-matrix / inverse-sensitivity laboratory

The branch contains exact inverse-matrix derivatives, Touchstone parsing, nuisance-aware fitting, topology/gauge analysis, multi-state objectives, frozen positive tests, and deliberately retained failed preregistrations.

That makes it useful for teaching, reproducing, or extending reciprocal coupled-resonator inference without pretending every research branch succeeded.

### 8. Generalize the compiler idea beyond microwave filters

The mathematical core is not inherently “a filter trick”:

```text
parameterized sparse symmetric operator
+ reciprocal local stamps
+ external response
+ exact inverse/adjoint sensitivity
+ constrained topology
```

That structure also occurs in other linear reciprocal resonator/scattering systems. Photonic, acoustic, mechanical, RF, or other domains would require their own correct forward/measurement models; TWC does **not** currently claim end-to-end support for them. But the compiler abstraction is deliberately broader than one microwave example.

---

## What became of the Geometric Neuron / chip idea?

It did not simply “turn into a filter.”

The original physical-computation idea forced the project to build and test a reusable object:

```text
geometry/topology
      ↓
sparse reciprocal operator
      ↓
forward response / transient
      ↓
exact local parameter sensitivities
      ↓
compiler lowering or physical implementation
```

The hardware question and the software compiler question then diverged under experiment.

The hardware line found real algebraic/circuit simplifications, but the attractive small-cap stochastic physical-adjoint claim failed controlled tests. The software side survived because exact reciprocal sensitivities and constrained sparse operators remain useful even when the material substrate does not supply a trustworthy stochastic adjoint.

The filter domain became a deliberately classical external testbed: if the compiler abstraction cannot behave sensibly on a well-understood reciprocal system with established mathematics and measurable S-parameters, it has no business making stronger claims elsewhere.

So the current outcome is:

> **The Geometric Neuron hardware hypothesis produced a documented physical boundary and, alongside it, a usable reciprocal-system compiler/diagnosis toolkit.**

---

## Core filter model

For the explicit source–resonator–load model,

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)
```

and each declared physical parameter has the exact derivative

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

A diagonal matrix knob can represent resonator detuning. An off-diagonal symmetric knob represents reciprocal coupling. Optional `nominal` values turn a fit into fitted-minus-design correction rows.

---

## Real / simulated Touchstone path

```bash
pip install -e .

twc-filter inspect-s2p measured.s2p
```

For ordinary narrow-band coupled-resonator work:

```text
Omega = (f0/BW) * (f/f0 - f0/f)
```

and:

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --bandwidth-hz 100000000 \
  -o measurement.json

twc-filter fit measurement.json -o tuned.json
```

A linear frequency mapping is also available when that is the model coordinate actually intended.

A starting topology is [`examples/published_filter_vna_topology.json`](examples/published_filter_vna_topology.json).

See [`docs/FILTER_TUNING.md`](docs/FILTER_TUNING.md).

---

## Evidence ladder

```text
v0.1  published 3-resonator couplings                   5/5 exact
v0.2  resonator offsets + couplings                     5/5 exact
v0.3  published 6x6 cross-coupled topology              5/5 exact
v0.4  zero-mean repeated complex noise                 15/15 robust
v0.5  systematic loss + phase nuisance                 15/15 aware
                                                       0/15 naive matrix recovery
v0.6  hidden parasitic edge local discovery            12/15 top-1/recovery
                                                       PRIMARY DISCOVERY FAIL
v0.7  four known physical states                        9/15 top-1
                                                        9/15 top-3
                                                        9/15 recovery
                                                       PRIMARY DISCOVERY/RECOVERY FAIL
```

### What the topology failures taught us

v0.6 first showed that an exact local derivative does not imply correct topology inference after a wrong model has compensated.

A post-hoc full candidate-conditioned refit did not rescue the difficult static case.

The deeper mechanism was then exposed: the hardest candidate lay on a **classical response-equivalent coupling-matrix realization orbit**. Internal similarity/rotation freedom is established filter theory, not a TWC invention. citeturn206419search2turn206419search0

TWC’s topology-only gauge audit then predicted exactly the two response-space machine-zero aliases `(0,3)` and `(2,5)`.

v0.7 deliberately changed the information by adding known resonator-detuning states. Its schedule breaks both exact gauges in principle, but the frozen benchmark still failed both gauge-class cases across all starts while recovering all three non-gauge cases across all starts.

The current boundary is therefore:

> **Breaking an exact realization gauge is necessary for unique physical diagnosis, but not sufficient for robust finite-noise topology discovery after a flexible wrong-model fit has compensated.**

No v0.8 synthetic hit-rate rescue is planned.

Read:

- [`docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md`](docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md)
- [`docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md`](docs/BENCHMARK_PUBLISHED_FILTER_MULTISTATE_TOPOLOGY_V07_RESULT.md)
- [`docs/FILTER_REALIZATION_ROTATION_PROOF_2026-08-10.md`](docs/FILTER_REALIZATION_ROTATION_PROOF_2026-08-10.md)
- [`docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md`](docs/FILTER_TOPOLOGY_GAUGE_CAPABILITY_MAP_2026-08-10.md)

---

# TW-1A hardware research

## What survived

The hardware line produced concrete recurrence/circuit simplifications, including state-bank orientation, common/difference reverse coordinates, active virtual summing, reusable half-range transfers, and kick-drift `(Z,P)` coordinates. The process-independent circuit ladder remains under `spice/`.

## The important negative result

At the attractive small-cap stochastic operating point, controlled task × fabrication × dynamic-noise experiments did not preserve the physical adjoint.

At one fixed parameter vector, even averaging **1024** independently noisy physical gradients gave median:

```text
cosine to clean gradient        0.280
projection onto clean gradient  0.191
relative vector error           1.048
relative trace standard error   0.521
```

> **A stochastic physical adjoint is not automatically an adjoint of a stochastic forward history.**

The deterministic echo algebra can survive while a reverse traversal still lacks the particular random history that generated the realized forward trajectory. Capacitance backoff and brute-force averaging did not rescue the attractive point.

See [`docs/HARDWARE_STATUS_2026-08-09.md`](docs/HARDWARE_STATUS_2026-08-09.md).

---

## Repository map

```text
transientwave/
  compiler.py                       transient reciprocal compiler
  physical.py                       TW-1A lowering
  backend.py                        strict physical backend

  generalized_coupling_matrix.py   explicit-port response + exact derivatives
  measurement_aware_filter.py      loss + S11/S21 phase nuisance
  filter_tuning.py                 bounded physical+nuisance optimizer
  filter_analysis.py               repeated-fit / perturbation comparison
  filter_cli.py                    twc-filter command line
  touchstone.py                     two-port Touchstone ingest
  identifiability.py                response-Jacobian novelty diagnostics
  topology_gauge.py                 topology-only similarity/gauge audit
  topology_discovery.py             experimental missing-edge scorer
  multistate_filter.py              shared-physics multi-state objective

experiments/
  published_*filter*.py             frozen filter evidence / microscopes
  v09_*.py / v10_*.py               stochastic-adjoint tests

examples/
  published_filter_vna_topology.json

spice/                               circuit rejection/pass ladder
docs/                                results, prior-art boundary, tuner guides
tests/                               compiler/filter/circuit regression tests
```

---

## Claim boundary

Classical coupling-matrix synthesis, extraction, similarity transformations, computer-aided tuning, lossy extraction, and parasitic-coupling localization all have substantial prior art. Atia–Williams and Cameron are part of the classical lineage behind the realization freedom exposed here. citeturn206419search1turn206419search2turn206419search0

See [`docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md`](docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md).

The narrower TWC contribution under test is:

> **Represent reciprocal systems as constrained sparse symmetric operators; preserve exact sensitivity structure; separate supported nuisance from physical parameters; expose fitted-minus-design diagnosis; and explicitly report when the chosen measurement/model cannot uniquely support a physical claim.**

---

## Current stopping line

The software-only topology-discovery ladder stops at the failed v0.7 gate.

The next external falsifier would be a real reciprocal resonator/filter measured in repeated known physical states. Until such hardware/data exists, there is no value in manufacturing another synthetic success percentage.

That does **not** make the repository idle. The compiler, Touchstone path, nuisance-aware fit, repeated-state analysis, exact sensitivities, and topology negative-capability audit are usable software results now.
