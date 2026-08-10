# TransientWaveCompiler

**Diagnose sparse reciprocal wave systems from measured response — with a separate mixed-signal research line for transient-wave computation.**

TransientWaveCompiler (TWC) grew out of [GeometricNeuronPlusField](https://github.com/anttiluode/GeometricNeuronPlusField). The repository now contains two related but experimentally distinct projects:

1. **TWC compiler / reciprocal-system tuner** — infer and optimize sparse symmetric wave/filter operators on an ordinary computer.
2. **TW-1A mixed-signal research backend** — investigate whether a reciprocal physical wave body can regenerate transient history and expose local training credit without storing an `O(N*T)` trajectory tape.

The compiler/tuner is now the application mainline. The chip is parked as a research object with both positive circuit results and a useful negative stochastic-adjoint result.

---

## Current application: turn filter tuning into diagnosis

Given a filter topology and complex measured `S11` / `S21`, `twc-filter` estimates the physical coupling matrix rather than merely searching for a trace match.

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

So a diagonal knob can mean “this resonator is off frequency” and an off-diagonal symmetric knob can mean “this reciprocal coupling is wrong.”

### The result that matters most

The v0.5 benchmark deliberately mixed the hidden seven-knob published cross-coupled matrix with:

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

The important lesson is not another small RMSE number:

> **Measurement-chain physics must be modeled separately, or reference-plane/calibration error can be converted into false physical coupling corrections.**

See [`docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md`](docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md).

---

## Real measurement path

The active branch now accepts ordinary two-port Touchstone data.

```bash
pip install -e .

twc-filter inspect-s2p measured.s2p

twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --scale-hz 50000000 \
  -o measurement.json

twc-filter fit measurement.json -o tuned.json
```

The importer preserves physical frequency in hertz and records the explicit normalization

```text
Omega = (frequency_hz - center_hz) / scale_hz.
```

It does **not** silently guess the coupling-matrix frequency normalization.

The two-port parser supports the practical first-VNA subset of Touchstone 1.x/2.0, `RI` / `MA` / `DB`, and both two-port data orders.

See [`docs/FILTER_TUNING.md`](docs/FILTER_TUNING.md).

---

## Joint physical + nuisance fit

A topology JSON may optionally expose bounded nuisance variables alongside matrix knobs:

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

The result separates:

```text
matrix                 inferred physical coupling matrix
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
```

The new product surface is covered by both the repository-wide test suite and a dedicated `filter-cli-ci` gate, including the nuisance gradients and Touchstone preparation path.

---

## Next structural question: is the topology itself wrong?

The current fitter assumes that the declared reciprocal graph is correct. That is the next assumption worth attacking.

Suppose the intended matrix omits one weak physical coupling:

```text
known topology + unknown parasitic reciprocal edge
```

A constrained fit cannot explain that edge away perfectly. The residual should contain a direction in response space corresponding to the missing symmetric matrix stamp.

The next experiment asks whether TWC can:

1. fit the declared topology and nuisance;
2. score absent reciprocal edges directly from the structured complex residual and exact sensitivity;
3. rank the true missing edge first;
4. add it and jointly recover both the intended matrix and parasitic strength.

That would move the tool from **parameter diagnosis** toward **topology diagnosis**.

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
  touchstone.py                     dependency-free two-port measurement reader

  circuit_emulator_v09_*.py        controlled hardware stochastic emulation
  kick_drift.py                     kick-drift representation

experiments/
  published_*filter*.py             external-domain filter evidence ladder
  v09_*.py / v10_*.py               stochastic-adjoint and forward-estimator tests

spice/                               circuit rejection/pass ladder
docs/                                preregistrations, results, hardware status, tuner guide
tests/                               compiler, circuit, filter, nuisance and Touchstone tests
```

Failed preregistered gates are intentionally retained. In this repository they are part of the design record: many of the useful simplifications came from identifying which assumption should be deleted rather than merely tightening tolerances.

---

## Prior-art boundary

TWC does **not** claim invention of adjoint optimization, coupling-matrix synthesis/extraction, in-situ physical backpropagation, Hamiltonian echo learning, integrating-factor damping transforms, physical wave computing, or trainable scattering media.

The narrower compiler/engineering contribution being explored is:

> **Represent reciprocal systems as constrained sparse symmetric operators, preserve exact sensitivity structure, jointly separate physical parameters from supported measurement nuisance, and make residual model mismatch explicit enough to diagnose when the declared physics itself is wrong.**
