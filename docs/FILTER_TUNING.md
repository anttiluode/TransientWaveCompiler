# `twc-filter` — measured reciprocal filter diagnosis

`twc-filter` fits a constrained **explicit source–resonator–load reciprocal coupling matrix** to complex `S11` and `S21` data.

The useful distinction is **diagnosis rather than search**. Given a topology the filter is supposed to have, the fitter estimates which resonator self-detunings and reciprocal couplings are wrong while separating them from supported measurement-chain nuisance.

This is the first product-like surface extracted from the TransientWaveCompiler research branch. It uses the same sparse symmetric parameter idea as the transient compiler, but the filter equations are the standard generalized coupling-matrix equations:

```text
A(Omega) = M + Omega U - j q
S11      = 1 + 2j [A^-1]_(S,S)
S21      = -2j [A^-1]_(L,S).
```

The optimizer differentiates the inverse matrix exactly:

```text
d A^-1 / dp = -A^-1 (dA/dp) A^-1.
```

A reciprocal coupling knob stamps two symmetric entries. A diagonal resonator tuning knob stamps one entry.

## Install

From the active branch:

```bash
pip install -e .
twc-filter --help
```

## Fast path: a measured `.s2p` file

The current real-data workflow deliberately keeps **measurement parsing**, **frequency normalization**, and **physical topology** separate.

First inspect the trace:

```bash
twc-filter inspect-s2p measured.s2p
```

Then prepare it with the topology the device is supposed to have:

```bash
twc-filter prepare-s2p topology.json measured.s2p \
  --center-hz 2450000000 \
  --scale-hz 50000000 \
  -o measurement.json
```

This records the physical frequency axis and applies the explicit mapping

```text
Omega = (frequency_hz - center_hz) / scale_hz.
```

`scale_hz` may be negative if the chosen coupling-matrix convention requires the opposite Omega sign.

Then fit:

```bash
twc-filter fit measurement.json -o tuned.json
```

### Touchstone support

The dependency-free reader currently supports the practical two-port subset needed for the first VNA experiments:

- Touchstone 1.x `.s2p` network data;
- ordinary Touchstone 2.0 two-port network data;
- S parameters in `RI`, `MA`, or `DB` representation;
- standard `21_12` ordering and Touchstone 2.0 `12_21` ordering;
- full two-port matrices;
- reciprocal lower/upper two-port matrices;
- a common real reference resistance.

Unequal per-port reference impedances and arbitrary N-port conversion are intentionally not yet implemented.

### Why `center_hz` and `scale_hz` are explicit

A Touchstone file tells us the measured frequency axis; it does **not** tell us which normalized coupling-matrix coordinate the intended filter model uses. TWC therefore refuses to silently invent `Omega(f)`.

The current linear map is a transparent first real-data bridge, not a claim that one linear normalization is the universal bandpass transform for every filter family. More domain-specific normalization can be added without changing the S-parameter parser.

---

## Topology JSON

A topology file can contain just the model, nodes, trainable matrix parameters, optimizer settings, and optional nuisance bounds. `prepare-s2p` inserts the measured arrays.

Example:

```json
{
  "name": "my-filter",
  "model": "explicit-port",
  "nodes": 6,
  "parameters": [
    {"name": "mS1", "i": 0, "j": 1, "initial": 0.80, "nominal": 1.02, "min": 0.40, "max": 1.50},
    {"name": "d1",  "i": 1, "j": 1, "initial": 0.00, "nominal": 0.00, "min": -0.50, "max": 0.50},
    {"name": "m12", "i": 1, "j": 2, "initial": -0.60, "nominal": -0.86, "min": -1.50, "max": -0.20},
    {"name": "m23", "i": 2, "j": 3, "initial": 0.95, "nominal": 0.77, "min": 0.20, "max": 1.30},
    {"name": "m34", "i": 3, "j": 4, "initial": -1.05, "nominal": -0.86, "min": -1.50, "max": -0.20},
    {"name": "m4L", "i": 4, "j": 5, "initial": 1.15, "nominal": 1.02, "min": 0.40, "max": 1.50},
    {"name": "m14", "i": 1, "j": 4, "initial": -0.05, "nominal": -0.19, "min": -0.70, "max": 0.40},
    {"name": "mSL", "i": 0, "j": 5, "initial": 0.020, "nominal": 0.0005, "min": -0.05, "max": 0.05}
  ],
  "optimizer": {
    "iterations": 1200,
    "learning_rate": 0.015
  }
}
```

Node convention:

```text
0             source
1 .. nodes-2  resonators
nodes-1       load
```

`i == j` represents a diagonal resonator self-detuning parameter. `i != j` represents one reciprocal coupling. The same reciprocal matrix entry cannot be declared twice.

### `initial` versus `nominal`

These fields have different jobs:

```text
initial   starting point supplied to the optimizer
nominal   intended/design value used only for diagnosis
```

`nominal` is optional and does not affect the fit. When it is present, the result contains a `diagnosis` row with:

```text
fitted value
fitted - nominal
percent deviation when nominal != 0
frequency-equivalent deviation when a linear Touchstone Omega scale is known
```

For a linear mapping, the reported frequency-equivalent deviation is simply

```text
(fitted - nominal) * scale_hz.
```

For a diagonal resonator detuning this is the directly useful frequency-offset interpretation under the chosen normalized model. For an off-diagonal coupling it is a **coupling-frequency equivalent**, not a claim about screw travel, gap distance, or any other actuator calibration.

This distinction lets a topology file represent the intended design while `initial` remains free to be a deliberately poor optimizer start.

---

## Joint measurement/model nuisance

The v0.5 benchmark established that systematic measurement physics cannot safely be treated as if it were a coupling error. The product fitter therefore now supports optional joint estimation of:

```text
resonator_loss   common normalized resonator loss lambda
phi11            S11 phase offset [radian]
tau11            S11 phase slope [radian / normalized Omega]
phi21            S21 phase offset [radian]
tau21            S21 phase slope [radian / normalized Omega]
```

Example:

```json
{
  "nuisance": {
    "resonator_loss": {"initial": 0.010, "min": 0.000, "max": 0.080},
    "phi11":          {"initial": 0.000, "min": -0.50, "max": 0.50},
    "tau11":          {"initial": 0.000, "min": -0.10, "max": 0.10},
    "phi21":          {"initial": 0.000, "min": -0.50, "max": 0.50},
    "tau21":          {"initial": 0.000, "min": -0.10, "max": 0.10}
  }
}
```

Missing nuisance fields are fixed at zero, so existing lossless JSON remains backward compatible. A field can also be fixed to a known nonzero value by setting `min == initial == max`.

The optimizer then solves one bounded problem over

```text
[matrix knobs..., lambda, phi11, tau11, phi21, tau21]
```

using exact derivatives for every variable.

The result JSON distinguishes:

- `fitted_s11` / `fitted_s21`: predicted trace including fitted measurement phase nuisance;
- `physical_s11` / `physical_s21`: inferred physical filter response before the phase nuisance;
- `matrix`: inferred reciprocal physical coupling matrix;
- `diagnosis`: optional fitted-minus-nominal correction rows;
- `nuisance`: inferred loss/reference-plane variables and their bounds/gradients.

This is important because a low residual by itself is not enough. The goal is to avoid converting cable/reference-plane error into false physical screw corrections.

---

## Direct JSON measurement input

Touchstone is optional. A complete fit specification may still provide normalized `omega`, `s11`, and `s21` arrays directly:

```json
{
  "omega": [-3.0, -2.99, -2.98],
  "s11": {
    "real": [0.1, 0.2, 0.3],
    "imag": [0.0, 0.01, 0.02]
  },
  "s21": {
    "real": [0.01, 0.02, 0.03],
    "imag": [-0.1, -0.09, -0.08]
  }
}
```

The short arrays above illustrate the schema only. Real `omega`, `S11`, and `S21` arrays must have equal length and should contain the complete measurement grid used for fitting.

## Validate without fitting

```bash
twc-filter fit measurement.json --validate-only
```

Example output:

```text
valid explicit-port filter spec: nodes=6, knobs=8, samples=1201, iterations=1200, measurement_model=joint-nuisance, free_nuisance=5, nominal_knobs=8
```

## Fit output

```bash
twc-filter fit measurement.json -o tuned.json
```

The console prints the initial/final loss, recovered matrix knobs, any free nuisance variables, and fitted-minus-nominal diagnosis when design values are present. `tuned.json` also contains:

- parameter order and bounds;
- initial/final/nominal values;
- initial/final exact gradients;
- fitted symmetric matrix;
- diagnosis rows and frequency-equivalent corrections when available;
- nuisance estimates;
- measured, fitted, and inferred-physical complex `S11`/`S21` arrays;
- physical frequency metadata when the input came through Touchstone;
- optimizer settings;
- a compact loss trace.

Use `--compact` if the full response JSON should be written without indentation.

---

## Evidence ladder

The filter surface was not exposed from a single clean synthetic fit. The current sequence is:

```text
v0.1  published 3-resonator couplings                  5/5 exact
v0.2  resonator offsets + couplings                    5/5 exact
v0.3  published 6x6 cross-coupled topology             5/5 exact
v0.4  zero-mean repeated complex measurement noise    15/15 robust
v0.5  loss + reference-plane systematic nuisance      15/15 aware
                                                      0/15 naive hidden-matrix recovery
v0.6  one hidden parasitic reciprocal edge             preregistered/running
```

The v0.5 comparison is the reason nuisance variables are now part of the product surface. A lossless/no-phase model could fit toward the trace only by corrupting physical matrix estimates; the joint model recovered the hidden matrix on all frozen cells.

See:

- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V01_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_COUPLED_FILTER_V02_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_CROSS_COUPLED_FILTER_V03_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_NOISY_MEASUREMENT_V04_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_SYSTEMATIC_NUISANCE_V05_RESULT.md`
- `docs/BENCHMARK_PUBLISHED_FILTER_PARASITIC_TOPOLOGY_V06_PREREG.md`

---

## Current boundary and next falsifier

The fitter still assumes:

- a real-symmetric reciprocal coupling matrix;
- explicit source and load nodes;
- a user-declared physical topology for ordinary `fit`;
- one common resonator loss value when loss fitting is enabled;
- linear phase nuisance versus normalized `Omega`;
- bounded continuous matrix knobs;
- no actuator hysteresis/nonlinearity;
- no outlier model;
- no automatic de-embedding beyond the fitted phase nuisance.

The next external falsifier is therefore simple and physical:

> **measure a real two-port resonator filter on a VNA, declare the topology and nominal design, and see whether TWC gives stable, physically interpretable diagnoses across repeated sweeps and deliberate tuning changes.**

In parallel, v0.6 attacks the structural assumption with **parasitic topology discovery**: hide one weak reciprocal edge that is absent from the declared topology, ask whether the constrained residual identifies the correct missing edge, then jointly recover its strength and the intended matrix.

## Deliberate boundary from TW-1A

This tool is **not** the TW-1A on-device physical gradient learner. The hardware branch and filter tuner share sparse reciprocal operator machinery, but `twc-filter` runs a high-accuracy computer-side inverse-matrix optimizer.

That distinction is intentional. Controlled thermal experiments did not qualify the small-cap on-device stochastic adjoint. The filter tuner is the current application mainline.
