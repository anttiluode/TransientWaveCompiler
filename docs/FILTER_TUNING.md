# `twc-filter` — measured reciprocal filter diagnosis

`twc-filter` fits a constrained **explicit source–resonator–load reciprocal coupling matrix** to complex `S11` and `S21` data.

Given a declared topology, optional nominal/design values, and a measured response, the tool estimates physical detuning/coupling parameters while jointly fitting the supported loss/reference-plane nuisance.

This is a product-like surface built on established coupling-matrix physics; it is not a claim to have invented coupling-matrix extraction or computer-aided filter diagnosis. See `docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md`.

## Model and exact derivatives

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S)
```

The optimizer differentiates the inverse matrix exactly:

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

An off-diagonal parameter stamps two symmetric reciprocal entries. A diagonal parameter stamps one resonator self-detuning entry.

## Install

```bash
pip install -e .
twc-filter --help
```

---

# Real `.s2p` workflow

## 1. Inspect the VNA trace

```bash
twc-filter inspect-s2p measured.s2p
```

The dependency-free reader currently supports the practical first-VNA two-port subset:

- Touchstone 1.x `.s2p` network data;
- ordinary Touchstone 2.0 two-port network data;
- S parameters in `RI`, `MA`, or `DB` representation;
- standard `21_12` ordering and Touchstone 2.0 `12_21` ordering;
- full two-port matrices;
- reciprocal lower/upper two-port matrices;
- one common real reference resistance.

Unequal per-port reference impedances and arbitrary N-port conversion are not yet implemented.

## 2. Prepare the physical frequency coordinate

A Touchstone file gives physical frequency. The coupling-matrix model uses normalized `Omega`. TWC records the mapping explicitly rather than silently guessing it.

### Preferred narrow-band bandpass normalization

For ordinary coupled-resonator bandpass work:

```text
Omega = s * (f0/BW) * (f/f0 - f0/f)
```

where `s` is the explicit `+1` or `-1` sign convention.

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --bandwidth-hz 100000000 \
  -o measurement.json
```

Use the opposite coupling-matrix sign convention with:

```bash
--omega-sign -1
```

### Explicit linear alternative

When the intended model coordinate is linear over the band:

```text
Omega = (f - center_hz) / scale_hz
```

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --scale-hz 50000000 \
  -o measurement.json
```

`scale_hz` may be negative to reverse the sign convention.

The prepared JSON retains the original `frequency_hz`, records the chosen normalization metadata, and inserts the measured complex `S11` / `S21` arrays.

## 3. Fit

```bash
twc-filter fit measurement.json -o tuned.json
```

Validate first without optimizing if desired:

```bash
twc-filter fit measurement.json --validate-only
```

---

# Topology/design JSON

A ready starting point is:

```text
examples/published_filter_vna_topology.json
```

It contains:

- the published four-resonator cross-coupled structure used in the benchmark ladder;
- four diagonal resonator-detuning knobs;
- nominal/design matrix values;
- bounded common loss and S11/S21 phase nuisance;
- conservative optimizer settings.

Node convention:

```text
0             source
1 .. nodes-2  resonators
nodes-1       load
```

A parameter has the form:

```json
{
  "name": "m12",
  "i": 1,
  "j": 2,
  "initial": -0.60,
  "nominal": -0.86,
  "min": -1.50,
  "max": -0.20
}
```

`i == j` is a diagonal resonator detuning. `i != j` is a reciprocal coupling. The same reciprocal matrix entry cannot be declared twice.

## `initial` versus `nominal`

```text
initial   optimizer starting point
nominal   intended/design value used only for diagnosis
```

`nominal` never changes the fit objective. It lets the result report the recovered physical value relative to the intended design.

For every parameter with a nominal value, the result contains:

```text
kind
nominal
fitted
deviation_normalized
deviation_percent        when nominal != 0
```

For the explicit **linear** Omega mapping, the current implementation also reports

```text
frequency_equivalent_deviation_hz
    = (fitted - nominal) * scale_hz.
```

For a diagonal resonator detuning that is a directly useful frequency-offset interpretation under the chosen linear model. For an off-diagonal coupling it is only a coupling-frequency equivalent, not a screw/gap calibration.

The classical nonlinear bandpass mapping is now supported for fitting; automatic conversion of an arbitrary fitted normalized delta back into a single exact Hz correction is intentionally not reported as though all parameter types were literal frequency shifts.

---

# Joint measurement/model nuisance

Optional nuisance fields are:

```text
resonator_loss   common normalized resonator loss lambda
phi11            S11 phase offset [radian]
tau11            S11 phase slope [radian / normalized Omega]
phi21            S21 phase offset [radian]
tau21            S21 phase slope [radian / normalized Omega]
```

Example:

```json
"nuisance": {
  "resonator_loss": {"initial": 0.010, "min": 0.000, "max": 0.080},
  "phi11":          {"initial": 0.000, "min": -0.50, "max": 0.50},
  "tau11":          {"initial": 0.000, "min": -0.10, "max": 0.10},
  "phi21":          {"initial": 0.000, "min": -0.50, "max": 0.50},
  "tau21":          {"initial": 0.000, "min": -0.10, "max": 0.10}
}
```

Missing nuisance fields are fixed at zero, preserving backward compatibility with the older lossless format. A nuisance value can also be fixed nonzero by setting `min == initial == max`.

The joint fit solves one bounded objective over

```text
[matrix knobs..., lambda, phi11, tau11, phi21, tau21]
```

using exact derivatives for every variable.

The output separates:

- `matrix`: inferred reciprocal physical matrix;
- `diagnosis`: fitted-minus-nominal physical corrections when nominal values were declared;
- `physical_s11` / `physical_s21`: inferred physical response before fitted phase nuisance;
- `fitted_s11` / `fitted_s21`: complete predicted measured response;
- `nuisance`: fitted loss/phase variables, bounds, and gradients.

A low trace residual alone is not enough: the v0.5 experiment showed that an incomplete model can fit by corrupting the physical matrix.

---

# Evidence ladder

```text
v0.1  published 3-resonator couplings                  5/5 exact
v0.2  resonator offsets + couplings                    5/5 exact
v0.3  published 6x6 cross-coupled topology             5/5 exact
v0.4  repeated complex measurement noise              15/15 robust
v0.5  loss + reference-plane systematic nuisance      15/15 aware
                                                      0/15 naive hidden-matrix recovery
v0.6  one hidden parasitic reciprocal edge             12/15 top-1
                                                      12/15 recovery
                                                      PRIMARY DISCOVERY FAIL
```

See:

- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_CROSS_COUPLED_FILTER_V03_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_NOISY_MEASUREMENT_V04_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_RESULT.md`

## v0.5 boundary

The frozen comparison established only this method-specific result:

```text
same 15 cells
matrix-only model             hidden matrix 0/15
matrix + supported nuisance   full recovery 15/15
```

It should not be generalized into “all prior methods de-embed phase first.” Published vector-fitting methods already exist that form extraction polynomials without first removing phase offset/de-embedding transmission lines.

## v0.6 boundary

The first missing-edge estimator fit the wrong topology, froze that compensated fit, then probed every absent reciprocal edge with an exact local derivative and ranked by actual probe residual.

Four hidden-edge locations were top-1 and recovered across all starts. One hidden edge, `(2,5)=-0.025`, ranked `8,8,7` and failed systematically. Therefore the preregistered discovery-primary clause failed.

The key lesson is:

> An exact derivative at a compensated wrong-model solution need not be a reliable identifier of the physical interaction omitted from that model.

The local scorer remains research code and is not exposed as an automatic topology-discovery CLI feature.

---

# Current boundaries

The ordinary fitter still assumes:

- a real-symmetric reciprocal coupling matrix;
- explicit source and load nodes;
- a user-declared physical topology;
- one common resonator-loss value when loss fitting is enabled;
- linear phase nuisance versus normalized `Omega`;
- bounded continuous parameters;
- no actuator hysteresis/nonlinearity model;
- no outlier/robust-noise model;
- no arbitrary N-port de-embedding.

## Next external falsifier

> **Measure a real two-port resonator filter on a VNA, fit repeated sweeps, deliberately perturb known resonators/couplings, and test whether the inferred physical corrections are reproducible and move in the known direction while nuisance absorbs measurement-chain variation.**

That is now more valuable than another clean synthetic recovery benchmark.

## Next topology research gate

The v0.6 failure points to candidate-conditioned refitting:

```text
for each absent reciprocal edge c:
    add c
    jointly refit matrix + c + nuisance
    compare final residual / model score
```

The failed v0.6 cell can be used as a post-hoc mechanism microscope. A qualifying next benchmark must use fresh hidden cases/noise seeds and be preregistered before outcomes are inspected.

## Deliberate boundary from TW-1A

`twc-filter` is a high-accuracy computer-side inverse-matrix optimizer. It is **not** the TW-1A on-device physical gradient learner.

The hardware branch and tuner share sparse reciprocal operator structure, but controlled thermal experiments did not qualify the small-cap stochastic physical adjoint. The filter tuner is the current application mainline.
