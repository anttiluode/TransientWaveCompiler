# `twc-filter` — measured reciprocal filter diagnosis

`twc-filter` fits a constrained **explicit source–resonator–load reciprocal coupling matrix** to complex `S11` and `S21` data.

Given a declared topology, optional nominal/design values, and a measured response, the tool estimates physical detuning/coupling parameters while jointly fitting supported loss/reference-plane nuisance.

This is a product-like surface built on established coupling-matrix physics; it is not a claim to have invented coupling-matrix extraction, computer-aided filter diagnosis, or parasitic-coupling localization. See `docs/FILTER_PRIOR_ART_AND_CLAIM_BOUNDARY.md`.

## Model

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

# Real `.s2p` workflow

## Inspect

```bash
twc-filter inspect-s2p measured.s2p
```

The dependency-free two-port reader supports the practical first-VNA subset:

- Touchstone 1.x and ordinary 2.0 network data;
- S parameters in `RI`, `MA`, or `DB`;
- `21_12` and `12_21` two-port ordering;
- full matrices plus reciprocal lower/upper two-port matrices;
- one common real reference resistance.

## Prepare the normalized frequency coordinate

For ordinary narrow-band coupled-resonator work, use the classical bandpass coordinate:

```text
Omega = s * (f0/BW) * (f/f0 - f0/f)
```

where `s` is an explicit sign convention:

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --bandwidth-hz 100000000 \
  -o measurement.json
```

Use `--omega-sign -1` for the opposite convention.

A linear alternative remains available when that is genuinely the intended model coordinate:

```text
Omega = (f - center_hz) / scale_hz
```

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --scale-hz 50000000 \
  -o measurement.json
```

The prepared JSON retains the original `frequency_hz` and records the exact normalization metadata.

## Fit

```bash
twc-filter fit measurement.json -o tuned.json
```

Validate without optimization:

```bash
twc-filter fit measurement.json --validate-only
```

# Topology/design JSON

A ready starting point is:

```text
examples/published_filter_vna_topology.json
```

It includes the published four-resonator cross-coupled structure, four diagonal resonator-detuning knobs, nominal design values, and bounded nuisance variables.

Node convention:

```text
0             source
1 .. nodes-2  resonators
nodes-1       load
```

Example parameter:

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

`initial` is the optimizer start. `nominal` is the intended/design value used only for diagnosis.

## Physical-unit resonator diagnosis

For a diagonal resonator term `d`, the model is locally

```text
Omega + d = 0
```

so the uncoupled resonance occurs at

```text
Omega_res = -d.
```

TWC now inverts the recorded frequency normalization and reports, for diagonal knobs when a supported Touchstone mapping is present:

```text
nominal_resonance_hz
fitted_resonance_hz
resonance_deviation_hz = fitted_resonance_hz - nominal_resonance_hz
```

This is exact for both the recorded linear and classical bandpass maps. In particular, a positive fitted-minus-nominal diagonal detuning does **not** automatically mean a higher physical resonance; the sign follows from `Omega_res=-d` and the chosen Omega convention.

That lets a real diagnosis legitimately say, for example, “resonator 3 is about 2.1 MHz low/high” under the declared model.

Off-diagonal reciprocal couplings are **not** converted into made-up hertz or screw travel. They are reported as fitted normalized values and deviations/percent deviations from nominal unless an actuator/device-specific calibration is supplied separately.

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

Missing nuisance fields are fixed at zero. A nuisance can be fixed nonzero by setting `min == initial == max`.

The output separates:

- `matrix`: inferred reciprocal physical matrix;
- `diagnosis`: fitted-minus-nominal physical corrections and diagonal resonance Hz when available;
- `physical_s11` / `physical_s21`: inferred response before fitted phase nuisance;
- `fitted_s11` / `fitted_s21`: complete predicted measured response;
- `nuisance`: fitted loss/phase variables, bounds, and gradients;
- `measurement_source`: retained Touchstone/normalization provenance.

# Repeated-sweep analysis

Do not average the first physical experiment into one best-looking trace. Fit each sweep independently, then inspect parameter repeatability.

```bash
twc-filter summarize-results baseline_*_fit.json -o baseline_summary.json
```

Compare an untouched ensemble with a deliberate physical perturbation:

```bash
twc-filter compare-results \
  --baseline baseline_*_fit.json \
  --perturbed perturbed_*_fit.json \
  -o perturbation_comparison.json
```

The comparison reports each physical parameter's baseline/perturbed mean and standard deviation, mean shift, shift relative to baseline repeatability, and absolute-shift rank within its physical kind (`resonator_detuning` or `reciprocal_coupling`). Nuisance shifts are reported separately.

See:

- `docs/REAL_VNA_FILTER_EXPERIMENT.md`
- `docs/REPEATED_SWEEP_ANALYSIS.md`

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

The v0.5 result is method-specific: on the frozen systematic corruption, omitting supported nuisance corrupted the hidden physical matrix while the joint model recovered it 15/15. It should not be generalized into a claim that all earlier methods de-embed phase first.

The v0.6 local missing-edge estimator also has a clear boundary: four hidden-edge locations were top-1 and recovered across every start, while hidden `(2,5)=-0.025` ranked `8,8,7`. An exact derivative at a compensated wrong-model optimum was not a reliable identifier of the omitted interaction.

See the frozen result documents under `docs/BENCHMARK_PUBLISHED_FILTER_*`.

# Current boundary

The ordinary fitter still assumes:

- a real-symmetric reciprocal coupling matrix;
- explicit source/load nodes;
- a user-declared physical topology;
- one common resonator loss when loss fitting is enabled;
- linear phase nuisance versus normalized `Omega`;
- bounded continuous parameters;
- no actuator hysteresis/nonlinearity model;
- no robust outlier model;
- no arbitrary N-port de-embedding.

Automatic parasitic-topology discovery is **not** a qualified product feature. Locating parasitic couplings is also established prior art; TWC's current topology work evaluates particular residual/exact-sensitivity estimators under controlled failure gates.

# Next external falsifier

> **Measure a real two-port resonator filter on a VNA, fit repeated sweeps, deliberately perturb a known resonator or coupling, and test whether the inferred physical correction is reproducible, localized to the changed hardware, and in the known direction while nuisance is estimated separately.**

That is now more valuable than another clean synthetic recovery benchmark.
