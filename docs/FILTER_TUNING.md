# `twc-filter` — measured reciprocal filter tuning

`twc-filter` fits a constrained **explicit source–resonator–load reciprocal coupling matrix** to measured complex `S11` and `S21` samples.

It is the first product-like surface extracted from the TransientWaveCompiler research branch. It uses the same sparse symmetric parameter idea as the transient compiler, but the filter equations are the standard generalized coupling-matrix equations:

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

From the repository:

```bash
pip install -e .
```

Then:

```bash
twc-filter --help
```

## Input JSON

The current CLI intentionally uses an explicit JSON interchange format rather than guessing topology from a Touchstone file. A specification contains:

```json
{
  "name": "my-filter",
  "model": "explicit-port",
  "nodes": 6,
  "parameters": [
    {"name": "mS1", "i": 0, "j": 1, "initial": 0.80, "min": 0.40, "max": 1.50},
    {"name": "m12", "i": 1, "j": 2, "initial": -0.60, "min": -1.50, "max": -0.20},
    {"name": "m23", "i": 2, "j": 3, "initial": 0.95, "min": 0.20, "max": 1.30},
    {"name": "m34", "i": 3, "j": 4, "initial": -1.05, "min": -1.50, "max": -0.20},
    {"name": "m4L", "i": 4, "j": 5, "initial": 1.15, "min": 0.40, "max": 1.50},
    {"name": "m14", "i": 1, "j": 4, "initial": -0.05, "min": -0.70, "max": 0.40},
    {"name": "mSL", "i": 0, "j": 5, "initial": 0.020, "min": -0.05, "max": 0.05}
  ],
  "omega": [-3.0, -2.99, -2.98],
  "s11": {
    "real": [0.1, 0.2, 0.3],
    "imag": [0.0, 0.01, 0.02]
  },
  "s21": {
    "real": [0.01, 0.02, 0.03],
    "imag": [-0.1, -0.09, -0.08]
  },
  "optimizer": {
    "iterations": 1200,
    "learning_rate": 0.015,
    "beta1": 0.9,
    "beta2": 0.999,
    "epsilon": 1e-8
  }
}
```

The short arrays above illustrate the schema only. Real `omega`, `S11`, and `S21` arrays must have equal length and should contain the complete measurement grid.

Node convention:

```text
0             source
1 .. nodes-2  resonators
nodes-1       load
```

`i == j` is allowed and represents a diagonal resonator self-detuning parameter. `i != j` represents one reciprocal coupling. The same reciprocal matrix entry cannot be declared twice.

## Validate without fitting

```bash
twc-filter fit measurement.json --validate-only
```

Example output:

```text
valid explicit-port filter spec: nodes=6, knobs=7, samples=1201, iterations=1200
```

## Fit

```bash
twc-filter fit measurement.json -o tuned.json
```

The console prints the initial/final loss and recovered knob values. `tuned.json` also contains:

- parameter order and bounds;
- initial/final values;
- initial/final exact gradients;
- fitted symmetric matrix;
- measured and fitted complex `S11`/`S21` arrays;
- optimizer settings;
- a compact loss trace.

Use `--compact` if the full response JSON should be written without indentation.

## What the current fitter assumes

Current `twc-filter fit` assumes:

- reciprocal real-symmetric coupling matrix;
- explicit source and load nodes;
- calibrated complex `S11` and `S21` on normalized frequency `Omega`;
- lossless resonators in the base model;
- fixed topology supplied by the user;
- bounded continuous matrix knobs.

The research branch has already begun testing extensions for resonator loss and reference-plane nuisance, but they are not exposed in the CLI until the preregistered systematic-mismatch benchmark passes.

## Evidence behind this interface

Before `twc-filter` was exposed, the same derivative engine was required to pass:

1. analytic-gradient finite-difference audits;
2. 5/5 exact recovery of a published three-resonator coupling matrix;
3. 5/5 exact recovery with three resonator self-detunings added;
4. 5/5 exact recovery of a published 6x6 source–four-resonator–load cross-coupled topology containing a very small direct source-load path;
5. 15/15 recovery of that seven-knob matrix from eight-sweep synthetic complex measurements with frozen zero-mean amplitude/phase noise.

See the corresponding `BENCHMARK_PUBLISHED_*_RESULT.md` files in `docs/`.

## Deliberate boundary

This tool is **not** the TW-1A on-device physical gradient learner. The hardware branch and filter tuner share sparse reciprocal operator machinery, but `twc-filter` runs a high-accuracy computer-side inverse-matrix optimizer. That distinction is intentional: controlled thermal experiments did not qualify the small-cap on-device stochastic adjoint, while ordinary computer-side resonator tuning has now produced strong external-domain results.
