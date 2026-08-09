# TW-1A dynamic-range budget v0.2 — signed zero-preserving paths

Date: 2026-08-09

This note corrects the bit-count convention used in `DYNAMIC_RANGE_BUDGET.md`.

The v0.1 formula treated all `2^B` converter codes as positive dynamic-range intervals. The physical emulator exposed why that is inappropriate for TW-1A: sparse couplings and silent waveform samples require an **exact zero/off code**.

TW-1A v0.2 therefore freezes a symmetric signed mid-tread path

```text
K = 2^(B-1) - 1
codes = -K ... 0 ... +K
step = full_scale / K
```

with one two's-complement endpoint intentionally unused.

The maximum positive full-scale-to-LSB magnitude ratio is therefore `K`, not `2^B`.

---

## 1. Damping gauge

As before,

```text
G = r^(-T)
D = 20 log10(G)
```

where `G` is the largest full-horizon amplitude compensation required by the scalar damping gauge.

The compiler policy remains

```text
G_compiler_cap = 8
```

or

```text
D_compiler_cap = 18.0618 dB.
```

---

## 2. Signed broadband drive path

If the weakest useful broadband-drive sample must occupy at least `m_drive` positive magnitude codes,

```text
G <= K / m_drive
K = 2^(B_drive-1)-1.
```

Thus

```text
D_drive <= 20 log10(K/m_drive).
```

For `m_drive=4` and `G=8`, require

```text
K >= 32.
```

Therefore:

```text
6-bit signed: K=31   just insufficient
7-bit signed: K=63   sufficient
```

for the worst program at the current compiler cap.

An isolated impulse can still be independently gain-scaled and does not pay the full broadband span if only one nonzero source sample must be represented.

---

## 3. Signed quadratic error/readout path

The compiled trajectory-energy adjoint/error envelope spans approximately `G^2`.

With `m_error` magnitude codes reserved for the weakest useful sample,

```text
G^2 <= K / m_error
G <= sqrt(K/m_error).
```

Equivalently,

```text
D_error <= 10 log10(K/m_error).
```

For the frozen conservative margin

```text
m_error = 4
```

and compiler cap `G=8`, require

```text
K >= 4 * 64 = 256.
```

Therefore:

```text
8-bit signed   K=127   insufficient
9-bit signed   K=255   still one code short of the strict 4-code rule
10-bit signed  K=511   sufficient
```

So a **10-bit signed zero-preserving error-envelope path** is the conservative v0.2 architecture requirement if TW-1A wants to support every program accepted by the existing `G<=8` compiler cap without rescaling/relaxing the four-code margin.

This replaces the v0.1 statement that 8 bits was sufficient for the full `G=8` envelope.

---

## 4. Detector SNR

The detector argument is unchanged by the digital code convention.

With required weakest-contribution margin `m_snr`, conservatively

```text
SNR_det_amplitude >= m_snr G^2.
```

At

```text
G=8
m_snr=4
```

this remains

```text
SNR_det_amplitude >= 256
SNR_det >= 48.16 dB
```

when SNR dB is `20 log10(amplitude ratio)`.

This remains a worst-time representation target, not an empirical closed-loop failure threshold.

---

## 5. Frozen irregular-arbor task is less demanding than the architecture cap

For the v0 benchmark family

```text
dt = .08
gamma = .40
T = 56
```

we have

```text
a = 1-dt*gamma = .968
r = sqrt(a) = .9838699101
G_task = r^-56 = 2.4859363
D_task = 7.9098 dB
G_task^2 = 6.17988.
```

With the same four-code margin, the quadratic error path needs

```text
K >= 4 * 6.17988 = 24.72.
```

A 6-bit signed path has `K=31`, so **the frozen 56-step task is representable by 6 bits under the envelope-only rule** even though the full architecture-wide `G=8` promise requires 10 bits.

This distinction is important:

```text
compiler-wide worst-case representation requirement != task-specific empirical learning requirement.
```

The v0.2 precision experiment must measure the latter without weakening the former.

---

## 6. Combined corrected representation envelope

For a broadband trajectory-energy program with signed mid-tread paths,

```text
K_drive = 2^(B_drive-1)-1
K_error = 2^(B_error-1)-1

D_max = min(
    20 log10(G_compiler_cap),
    20 log10(K_drive/m_drive),
    10 log10(K_error/m_error),
    0.5 * (SNR_detector_dB - 20 log10(m_snr))
).
```

The compiler should eventually calculate this from each program's actual `G`, converter backend and declared margins rather than relying on a global prose rule.

---

## 7. Consequence for TW-1A v0.2

Freeze these architectural statements before the corrected emulator experiment:

1. every signed programmable/drive/sense path must represent exact zero;
2. the current `G<=8` compiler cap implies a conservative **10-bit error-envelope path** for universal v0 support at four-code margin;
3. lower-resolution paths may still support shorter/lower-damping programs, and the compiler may prove that task-specifically;
4. empirical learning sweeps are not allowed to override a failed representation check.
