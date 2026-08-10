# Repeated-sweep analysis

Date: 2026-08-10

`twc-filter` now has a small ensemble-analysis layer for the first real VNA experiment.

The fitter should still be run **independently on each raw sweep**. The ensemble commands operate on the resulting fit JSON files; they do not average the VNA traces before fitting.

## Baseline repeatability

After fitting repeated untouched measurements:

```bash
twc-filter summarize-results baseline_01_fit.json baseline_02_fit.json baseline_03_fit.json \
  baseline_04_fit.json baseline_05_fit.json baseline_06_fit.json baseline_07_fit.json baseline_08_fit.json \
  -o baseline_summary.json
```

On shells that expand globs, the shorter form is:

```bash
twc-filter summarize-results baseline_*_fit.json -o baseline_summary.json
```

For every physical matrix parameter it reports:

```text
mean
sample standard deviation
min / max / range
median
all fitted values
```

Nuisance variables are summarized separately, as is final fit loss.

The point is to establish the measurement-to-measurement repeatability scale of the inferred **physical** matrix before interpreting any deliberate perturbation.

## Baseline versus deliberate perturbation

After independently fitting both sets:

```bash
twc-filter compare-results \
  --baseline baseline_*_fit.json \
  --perturbed perturbed_*_fit.json \
  -o perturbation_comparison.json
```

For each physical parameter the comparison reports:

```text
baseline mean / std
perturbed mean / std
mean shift
absolute mean shift
|shift| / baseline std
absolute-shift rank within parameter kind
```

Parameter kinds are separated into:

```text
resonator_detuning
reciprocal_coupling
```

so a deliberately changed resonator is ranked against the other resonator diagonals rather than against unrelated coupling magnitudes.

The `|shift| / baseline std` value is an **effect-to-repeatability ratio**, not a formal p-value or universal significance test.

Nuisance mean shifts are reported separately. This makes it possible to look for the intended structure:

```text
known device change
    -> localized physical-parameter shift

measurement-chain variation
    -> nuisance shift
    -> comparatively stable physical matrix
```

## Return-state check

If the hardware perturbation is reversible, fit the return sweeps and summarize them too:

```bash
twc-filter summarize-results return_*_fit.json -o return_summary.json
```

For the first physical experiment, inspect whether the baseline and return physical-parameter distributions overlap substantially. A future command can formalize three-state baseline/perturbed/return comparisons after the first real noise and drift scale is known.

## Boundary

These commands summarize fitted parameters; they do not make a claim that those parameters are identifiable or physically correct.

That is exactly what the real experiment is meant to test. A very repeatable wrong diagnosis remains a failure if it does not track the known hardware perturbation.

See `docs/REAL_VNA_FILTER_EXPERIMENT.md` for the full physical protocol.
