# TW-1A hardware-emulator envelope v0.1 — INVALIDATED

Date: 2026-08-09

This note supersedes the interpretation of `HARDWARE_ENVELOPE_V01.md` as a hardware result.

The raw v0.1 run is retained for provenance, but **its noisy/quantized conclusions are invalid** because code inspection after the frozen sweep exposed a semantic bug in the emulator's uniform quantizer.

## Bug

The original quantizer mapped a B-bit code linearly across `[-full_scale,+full_scale]` using

```text
levels = 2^B - 1
q = round((x + FS) * levels / (2 FS))
xq = q * (2 FS) / levels - FS
```

For an odd number of intervals, zero lies halfway between the two central codes.

Therefore

```text
Q_ij = 0
u[n] = 0
ADC input = 0
```

did **not** quantize to zero.

At 8 bits, for example, an exactly zero coefficient was mapped to approximately

```text
+FS/255
```

(up to the tie-rounding convention).

## Why this invalidates the noisy envelope

TW-1A's physical backend defines an irregular arbor by leaving many legal 8x8 grid edges **disabled**.

The buggy quantizer turned every disabled physical edge into a small nonzero reciprocal coupling. Thus weight resolution changed not only coefficient precision but the physical topology itself.

Likewise, zero samples in the intentionally silent second half of the preregistered drive schedule became nonzero forcing samples.

The strange v0.1 weight-bit result

```text
12/10/8/7 bits: fail
6 bits: large gain but control fail
5 bits: pass
4 bits: catastrophic
```

is therefore not interpretable as a hardware precision response. Coarser bit depth increased the magnitude of the unintended background couplings/forcing and changed the compiled task.

## Status of previous results

Retain:

- compiler algebra and source/compiled trajectory tests;
- clean unquantized physical-credit finite-difference audit;
- raw v0.1 logs as a debugging/provenance artifact.

Invalidate as hardware evidence:

- requested 8-bit noisy baseline result;
- converter-bit sweep;
- weight-bit sweep;
- leakage/mirror/drift/noise envelope conclusions.

Those experiments must be repeated only after the quantizer is corrected and on a **fresh preregistered task-seed block**.

## Required quantizer semantic

TW-1A v0.2 uses a signed zero-preserving mid-tread quantizer:

```text
K = 2^(B-1) - 1
step = FS / K
xq = clip(round(x/step), -K, +K) * step
```

so

```text
Q(0) = 0
DAC(0) = 0
ADC(0) = 0
```

exactly.

The non-linear/mu-law path must inherit the same zero-preserving central code.

## Scientific consequence

This invalidation is not a rescue of the 8-bit hypothesis. We do not yet know whether the corrected baseline passes.

The correct next sequence is:

```text
1. fix and unit-test zero-preserving quantization;
2. correct the signed dynamic-range bit budget;
3. freeze fresh task seeds and thresholds;
4. run the corrected baseline and joint precision grid;
5. only after a viable precision point is earned, sweep leakage/mirror/drift to failure.
```

No v0.1 threshold may be carried forward as evidence.
