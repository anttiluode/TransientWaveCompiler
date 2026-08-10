# TransientWaveCompiler

**Diagnose sparse reciprocal wave systems from measured response — with a separate mixed-signal research line for transient-wave computation.**

TransientWaveCompiler (TWC) grew out of [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField). The repository now contains two related but experimentally distinct projects:

1. **TWC compiler / reciprocal-system tuner** — infer and optimize sparse symmetric wave/filter operators on an ordinary computer.
2. **TW-1A mixed-signal research backend** — investigate whether a reciprocal physical wave body can regenerate transient history and expose local training credit without storing an `O(N*T)` trajectory tape.

The compiler/tuner is now the application mainline. The chip is parked as a research object with both positive circuit results and a useful negative stochastic-adjoint result.

---

## Current application: physical diagnosis from complex S-parameters

Given a declared reciprocal filter topology and complex measured `S11` / `S21`, `twc-filter` estimates the physical coupling matrix rather than merely searching for a trace match.

For the explicit source–resonator–load model,

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)
```

and every physical knob has an exact inverse-matrix derivative

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

A diagonal knob can represent resonator detuning. An off-diagonal symmetric knob represents a reciprocal coupling. Optional `nominal` values turn the fitted matrix into fitted-minus-design correction rows.

This is **not** a claim that coupling-matrix extraction or diagnosis was invented here. Those are established fields; see [`docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md`](docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md).

---

## The strongest current positive result: nuisance must not masquerade as physics

The v0.5 benchmark deliberately mixed a hidden seven-knob published cross-coupled matrix with:

```text
uniform resonator loss
S11 phase offset + slope
S21 phase offset + slope
0.5% RMS amplitude noise
0.5 degree RMS phase noise
8 sweeps averaged
```

Against the same 15 frozen measurement/start cells:

```text
NAIVE  lossless matrix-only hidden-matrix recovery    0/15
AWARE  matrix + loss + phase nuisance recovery       15/15
```

The supported lesson is narrow and concrete:

> **Under this frozen corruption, omitting supported measurement/model nuisance caused the physical matrix to absorb the mismatch; joint physical+nuisance estimation recovered the hidden matrix on all 15 cells.**

This does not imply that all previous extraction methods require separate de-embedding. Some published vector-fitting approaches explicitly avoid that requirement.

See [`docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md`](docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md).

---

## Real measurement path

The active branch accepts ordinary two-port Touchstone data.

```bash
pip install -e .

twc-filter inspect-s2p measured.s2p
```

For ordinary narrow-band coupled-resonator work, the preferred preparation path is the classical bandpass normalization

```text
Omega = (f0/BW) * (f/f0 - f0/f)
```

with an explicit sign convention:

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --bandwidth-hz 100000000 \
  -o measurement.json

twc-filter fit measurement.json -o tuned.json
```

A linear mapping remains available when that is the coordinate actually intended by the model:

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --scale-hz 50000000 \
  -o measurement.json
```

The importer preserves the physical frequency axis and records the chosen normalization instead of silently guessing it.

The two-port reader supports the practical first-VNA subset of Touchstone 1.x/2.0, `RI` / `MA` / `DB`, both two-port data orders, and a common real reference impedance.

A ready starting topology is [`examples/published_filter_vna_topology.json`](examples/published_filter_vna_topology.json). It includes the published cross-coupled structure, four diagonal resonator-detuning knobs, nominal design values, and bounded nuisance parameters.

See [`docs/FILTER_TUNING.md`](docs/FILTER_TUNING.md).

---

## Joint physical + nuisance fit

A topology JSON may expose bounded nuisance variables alongside matrix knobs:

```json
"nuisance": {
  "resonator_loss": {"initial": 0.010, "min": 0.000, "max": 0.080},
  "phi11":          {"initial": 0.000, "min": -0.50, "max": 0.50},
  "tau11":          {"initial": 0.000, "min": -0.10, "max": 0.10},
  "phi21":          {"initial": 0.000, "min": -0.50, "max": 0.50},
  "tau21":          {"initial": 0.000, "min": -0.10, "max": 0.10}
}
```

Missing nuisance fields remain fixed at zero, so older lossless specifications are backward compatible.

The output separates:

```text
matrix                 inferred physical coupling matrix
diagnosis              optional fitted-minus-nominal corrections
physical_s11 / s21     inferred filter before phase nuisance
fitted_s11 / s21       complete predicted measured trace
nuisance               inferred loss and reference-plane variables
```

---

## Filter evidence ladder

```text
v0.1  published 3-resonator couplings                  5/5 exact
v0.2  resonator offsets + couplings                    5/5 exact
v0.3  published 6x6 cross-coupled topology             5/5 exact
v0.4  zero-mean repeated complex measurement noise    15/15 robust
v0.5  systematic loss + reference-plane nuisance      15/15 aware
                                                      0/15 naive matrix recovery
v0.6  one hidden parasitic reciprocal edge            12/15 top-1 + recovery
                                                      PRIMARY DISCOVERY FAIL
```

The v0.6 failure is deliberate and retained. Four of five frozen hidden-edge locations were ranked #1 and recovered across every start. One hidden load-side edge, `(2,5)=-0.025`, ranked **8, 8, 7** and failed across all starts, so the preregistered top-3 clause failed.

See [`docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md`](docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md).

---

## Topology diagnosis: what v0.6 actually taught us

The first idea was simple:

```text
fit wrong declared topology
-> hold it fixed
-> compute exact derivative of every absent reciprocal edge
-> take one bounded probe per edge
-> rank by actual probe residual
```

That works extremely well when the wrong-topology fit stays near the intended physical matrix. It fails when the wrong model has already compensated for the missing interaction by moving its allowed physical and nuisance parameters.

The exact derivative is still correct at that compensated point. The point is simply no longer a reliable place from which to infer the omitted graph edge.

So **automatic parasitic topology discovery is not a qualified public feature yet.** The scorer remains research code in `transientwave/topology_discovery.py`.

The next estimator is candidate-conditioned model comparison:

```text
for each absent edge c:
    add c
    jointly refit matrix + c + nuisance
    compare final complex residual/model score
```

The failed `(2,5)` cell is useful as a post-hoc mechanism microscope. A qualifying next benchmark must use fresh hidden cases/seeds and be preregistered.

---

# TW-1A hardware research

## What survived

The hardware line produced real structural simplifications:

- analog `-PREV` multiplier/trim deleted through state-bank orientation;
- terminal analog clone deleted with common/difference reverse coordinates;
- matched positive/negative error DACs deleted;
- passive NEXT charge sharing rejected in ngspice and replaced by active virtual summing;
- monolithic large self transfer replaced by reusable half-range transfers;
- kick-drift `(Z,P)` coordinates passed deterministic algebra, echo boundary tests, state-range audit, and ngspice shear tests.

The process-independent circuit ladder is retained under `spice/`.

## The important negative result

At the attractive small-cap stochastic operating point, controlled task × fabrication × dynamic-noise experiments did not preserve the physical adjoint.

At one fixed parameter vector, even averaging **1024** independently noisy physical gradients gave median:

```text
cosine to clean gradient        0.280
projection onto clean gradient  0.191
relative vector error           1.048
relative trace standard error   0.521
```

The result is stronger than “the gradient is noisy.” There is evidence of a bias component.

> **A stochastic physical adjoint is not automatically an adjoint of a stochastic forward history.**

The deterministic second-order trajectory can be reconstructible from terminal state while the particular stochastic forward trajectory also depends on random packets that the reverse traversal does not possess. A new noisy reverse traversal is therefore not automatically the adjoint of that realized forward history.

Capacitance backoff and brute-force gradient averaging did not rescue the attractive point. This parks the small-cap general on-device training claim without invalidating the deterministic echo mathematics or the circuit work.

See [`docs/HARDWARE_STATUS_2026-08-09.md`](docs/HARDWARE_STATUS_2026-08-09.md).

---

## Repository map

```text
transientwave/
  compiler.py                       transient reciprocal compiler
  physical.py                       TW-1A lowering
  backend.py                        strict physical backend

  generalized_coupling_matrix.py   explicit-port filter response + exact derivatives
  measurement_aware_filter.py      loss + S11/S21 phase nuisance model
  filter_tuning.py                 bounded physical+nuisance optimizer
  filter_cli.py                    twc-filter command line
  touchstone.py                     two-port Touchstone + Omega normalization
  topology_discovery.py             experimental missing-edge scorer

experiments/
  published_*filter*.py             external-domain filter evidence ladder
  v09_*.py / v10_*.py               stochastic-adjoint and forward-estimator tests

examples/
  published_filter_vna_topology.json  starting point for a real VNA trace

spice/                               circuit rejection/pass ladder
docs/                                preregistrations, results, prior-art boundary, tuner guide
tests/                               compiler, circuit, filter, nuisance, Touchstone and topology tests
```

Failed preregistered gates are intentionally retained. In this repository they are part of the design record: many useful simplifications came from identifying which assumption should be deleted rather than merely tightening tolerances.

---

## Current claim boundary

TWC does **not** claim invention of adjoint optimization, coupling-matrix synthesis/extraction, computer-aided coupling-matrix diagnosis, lossy extraction, in-situ physical backpropagation, Hamiltonian echo learning, integrating-factor damping transforms, physical wave computing, or trainable scattering media.

The narrower compiler/engineering contribution being tested is:

> **Represent reciprocal systems as constrained sparse symmetric operators, preserve exact sensitivity structure, jointly separate supported measurement nuisance from physical parameters, expose fitted-minus-design diagnosis, and make residual model mismatch explicit enough to test when the declared physics itself is wrong.**

The next decisive application result is no longer synthetic: it is a real measured filter whose deliberate physical perturbations are diagnosed correctly and reproducibly.
