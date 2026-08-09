# TW-1A corrected hardware envelope v0.2 — precision qualification FAIL

Date: 2026-08-09

Preregistration: `docs/HARDWARE_ENVELOPE_PREREG_V02.md`

Workflow: `hardware-envelope-v02`, run 31295901159

Artifact: `tw1a-hardware-envelope-v02`

## Result

Stage A found **no stable precision corner**. Therefore Stage B correctly did not execute and no leakage/mirror/drift tolerance is claimed.

The corrected zero-preserving quantizer tests passed before this run. Unlike v0.1, disabled edges and silent DAC samples remain exactly zero.

## High-precision corner

At the highest tested point

```text
weight bits      12
DAC/ADC bits     12
mirror error     5%
+/- drift        .2%
credit noise     5%
```

the aggregate result was

```text
median exact reduction       +.5400
median shuffled reduction     .0000
>=10% exact reduction         3/5
exact beats shuffled          3/5
```

so it failed the frozen 4/5 criteria despite strong learning on three tasks.

Individual rows:

```text
seed 820  L0=0                 exact R= 0.000   shuffled R= 0.000
seed 821  L0=1.455e-5          exact R=+.570   shuffled R=+.307
seed 822  L0=3.536e-4          exact R=+.697   shuffled R=-.331
seed 823  L0=1.069e-5          exact R=+.540   shuffled R=-.289
seed 824  L0=3.140e-7          exact R=-.525   shuffled R=+.508
```

The exact-placement signal is therefore useful where the objective is observable, but two task instances are at or below the fixed sense-converter floor.

## Evidence for a sense-range problem

The v0.2 signed 12-bit ADC uses

```text
K = 2^(12-1)-1 = 2047
full scale = +/-2
LSB = 2/2047 = 9.77e-4.
```

Seed 820's complete quantized trajectory objective is exactly zero at the high-precision corner. Seed 824's trajectory objective is only `3.14e-7`, so it is represented by very sparse near-LSB activity.

By contrast, seeds 821-823 have larger observable outputs and all three learn strongly with exact physical credit.

This identifies a missing hardware/compiler degree of freedom:

> **A fixed global ADC full scale is not an adequate sense-port contract for irregular transient bodies whose transfer amplitude varies strongly with geometry.**

The forward and returned-error DAC paths already choose a schedule-specific full scale in the v0 emulator. The sense path should likewise expose a programmable analog gain / range rather than demand ever more ADC bits to cover unused headroom.

## Coarse Q points remain non-qualifying

At 6-bit weights, many grid points drive the objective almost to zero on all five tasks, but the shuffled-credit control often does the same. Examples:

```text
w6/c12 median exact R=.9993  shuffled=.9897  gap=.0097
w6/c10 median exact R=.9984  shuffled=.9973  gap=.0011
w6/c9  median exact R=1.000  shuffled=1.000   gap=0
```

The frozen control correctly rejects these as evidence for meaningful credit placement.

Thus the v0.1 `5-bit sweet spot` was not rescued by the corrected quantizer, and v0.2 does not support a coarse-weight build claim.

## Next development diagnostic

Use only already-inspected Stage-A seeds 820-824 and compare:

```text
fixed 12-bit ADC range
ideal/unquantized sense
compiler/PGA auto-ranged 12-bit sense
```

Measure raw output peak/RMS, nonzero ADC codes, objective distortion and closed-loop learning.

If programmable sense gain fixes the two invisible tasks, add it as an explicit TW-1A port primitive and preregister v0.3 on untouched seeds.

If ideal sensing does not fix them, the task/optimizer family itself needs revision before any hardware tolerance envelope is meaningful.

## v0.2 wall sentence

> **Zero-preserving quantization removes the v0.1 topology bug, but precision alone does not yield a robust TW-1A operating region. Three of five fresh arbors learn strongly at 12/12 bits while two are effectively below a fixed +/-2 sense range. The next missing architectural primitive is therefore programmable sense-port gain/auto-ranging, not simply more bits.**
