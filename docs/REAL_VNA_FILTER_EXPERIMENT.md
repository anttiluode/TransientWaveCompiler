# First real VNA filter experiment

Date drafted: 2026-08-10

Status: protocol for the next external falsifier. No real-data outcome has been inspected yet.

## Goal

The first physical experiment should not ask only:

> can TWC fit a real S-parameter trace?

Many methods can fit a trace.

The useful question is:

> **are the inferred physical parameters reproducible across repeated measurements, and do they change in the correct localized direction after a deliberate known physical perturbation while measurement nuisance remains separately estimated?**

That is the first real test of TWC as a diagnostic tool rather than another response fitter.

## Hardware requirements

The protocol is intentionally VNA-agnostic. It needs:

- a two-port VNA capable of exporting complex `.s2p` data;
- a reciprocal resonator filter with a topology that can be declared approximately;
- at least one physical element that can be changed deliberately and reversibly or replaced with a known value;
- ordinary cables/adapters and a competent two-port calibration at the cable ends when the VNA supports it.

A calibration should still be performed even though TWC can fit supported phase nuisance. The nuisance model is not a substitute for doing the measurement properly; it is there to prevent remaining systematic mismatch from being falsely converted into coupling corrections.

## Preferred first device

The easiest falsifier is not necessarily a sealed production ceramic filter.

A small coupled-resonator device is preferable if one resonator can be changed in a physically interpretable way, for example:

- an accessible helical/cavity filter with individual tuning elements;
- a coupled LC resonator board where one capacitor can be changed by a known amount;
- another two-port reciprocal resonator network with a known coupling graph.

The first device does not need to be commercially important. It needs to make the physical ground truth of one perturbation clear.

## Measurement set A — baseline repeatability

Without touching the device:

1. perform the two-port calibration;
2. place the sweep comfortably beyond both passband edges;
3. keep the same frequency grid for every repeat;
4. save at least **8 independent `.s2p` sweeps**;
5. do not average them together before saving.

Example names:

```text
baseline_01.s2p
baseline_02.s2p
...
baseline_08.s2p
```

Record separately:

```text
filter/device description
nominal center frequency
nominal or measured bandwidth used for Omega normalization
VNA model
calibration type
frequency start/stop
number of points
IF bandwidth / averaging setting if known
date/time
temperature if conveniently available
```

## Measurement set B — deliberate physical perturbation

Change **one** known physical element and leave everything else untouched as far as practical.

Prefer a perturbation whose direction is physically known independently of TWC. Examples:

```text
increase one resonator capacitance -> resonance should move lower
replace one resonator capacitor with a known nearby value
move one documented tuning element by a measured small amount
```

Save the perturbation itself in plain language and numbers. Do not infer its effect from TWC before recording it.

Then save another 8 independent sweeps:

```text
perturbed_01.s2p
...
perturbed_08.s2p
```

If the change is reversible, restore the original physical state and take a short return set:

```text
return_01.s2p
...
return_04.s2p
```

A successful return is valuable because it separates a real device-state change from drift in cables, connectors, or temperature.

## Topology specification

Start from:

```text
examples/published_filter_vna_topology.json
```

only if the device genuinely resembles that explicit source–four-resonator–load graph. Otherwise make a topology file matching the actual intended device.

Every intended physical parameter may contain:

```text
initial   optimizer starting value
nominal   intended/design value, if known
min/max   physically plausible fitting bounds
```

Do not add speculative cross-couplings merely to improve the fit. A structured residual from a deliberately incomplete but honest declared topology is more informative than an unconstrained matrix that can explain anything.

## Touchstone preparation

For ordinary narrow-band bandpass filters use the classical mapping:

```bash
twc-filter prepare-s2p topology.json baseline_01.s2p \
  --center-hz F0 \
  --bandwidth-hz BW \
  -o baseline_01.json
```

If the chosen coupling-matrix convention is reversed, use:

```text
--omega-sign -1
```

The prepared JSON retains physical `frequency_hz` and records the normalization metadata.

## Fit each sweep independently first

Do **not** begin by averaging all eight sweeps into one best-looking trace.

Fit each baseline and perturbation sweep separately:

```bash
twc-filter fit baseline_01.json -o baseline_01_fit.json
...
twc-filter fit perturbed_01.json -o perturbed_01_fit.json
```

Independent fits answer the first essential question: how much of the inferred physical matrix is repeatable measurement-to-measurement?

A later utility can batch these files and report parameter distributions automatically; the individual JSON files are already sufficient for the first experiment.

## Primary observations

### A. Baseline physical repeatability

For each physical matrix knob, calculate across the baseline sweeps:

```text
mean fitted value
standard deviation
range
```

Do the same separately for nuisance variables.

The hoped-for structure is:

```text
physical matrix          comparatively stable
phase/loss nuisance      allowed to vary with measurement-chain state
```

No universal numeric pass threshold is frozen yet because no real device/noise scale has been observed. The first data set should establish the practical scale before a second real-hardware benchmark is preregistered quantitatively.

### B. Correct perturbation localization

Compare the baseline distribution with the perturbed distribution.

The physically changed knob should show a clear shift in the expected direction.

For a deliberately changed resonator, record at least:

```text
Delta fitted diagonal parameter
rank of |Delta| among all resonator diagonals
sign agreement with known physical perturbation
```

For a deliberately changed coupling, use the corresponding off-diagonal group.

The strongest simple result would be:

```text
changed physical parameter has the largest same-class shift
AND
shift sign agrees with the known perturbation
AND
baseline and return states overlap substantially
```

### C. Nuisance separation

Check whether the physical diagnosis survives when phase/loss nuisance changes across sweeps.

A useful failure mode to look for deliberately is:

```text
small cable/reference-plane change
-> nuisance moves
-> physical matrix should remain substantially more stable
```

This is the physical analogue of the synthetic v0.5 question.

### D. Predictive next-step test

After the first perturbation fit, use the inferred diagnosis to predict which direction would move the device back toward its nominal matrix.

Then perform one small corrective physical adjustment and measure again.

This is stronger than retrospective parameter extraction because it tests whether the inferred physical error is actionable.

## Failure outcomes worth preserving

The first real experiment remains useful if it fails.

Important distinct failure modes are:

1. **trace fit poor** — current coupling-matrix/nuisance model does not describe the device;
2. **trace fit good, physical matrix unstable across repeats** — parameters are not identifiable at the measurement noise/systematic level;
3. **physical matrix repeatable but perturbation localizes incorrectly** — model/topology or physical interpretation is wrong;
4. **perturbation localizes but nuisance strongly trades with physical knobs** — joint model remains insufficiently identifiable;
5. **baseline/return do not agree** — device hysteresis/drift or measurement setup dominates;
6. **one topology fits many physically incompatible parameter sets** — need uncertainty/profile-likelihood reporting before diagnosis can be trusted.

None should be converted into a success by loosening bounds after looking at the answer without recording that change.

## Data to keep in the repository

For a publishable/reproducible result, retain:

```text
raw .s2p files
exact topology JSON
prepared measurement JSON or reproducible preparation command
fit result JSON
measurement notes
physical perturbation notes/photos if useful
software commit SHA
```

The raw `.s2p` files matter most. Future model changes can then be evaluated on exactly the same physical measurements.

## What success would mean

One good physical device would not establish universal filter tuning.

It would establish the first missing bridge in the current evidence chain:

```text
synthetic hidden physics
        -> controlled nuisance
        -> exact recovery
        -> real measured reciprocal hardware
        -> reproducible physical diagnosis
        -> correct response to a known physical change
```

That is enough to decide whether `twc-filter` deserves to become a more general engineering tool.
