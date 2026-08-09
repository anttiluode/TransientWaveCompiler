# TW-1A dynamic-range budget v0.1

Date: 2026-08-09

This note freezes the first closed-form dynamic-range budget **before** the noisy hardware emulator is used to choose any hardware boundary.

The budget is conservative. It deliberately separates:

1. **representation** — can the compiler-generated source/error schedules be represented at all?;
2. **learning tolerance** — can the closed loop still learn when the represented signals are noisy and imperfect?

Those are not the same question.

---

## 1. Scalar damping gauge

For the compiled scalar-damped recurrence,

```text
x[n] = r^n z[n]
0 < r <= 1
```

and a source acting on transition `n -> n+1` is compiled with

```text
u_comp[n] = r^(-(n+1)) u_src[n].
```

Define the full-horizon amplitude compensation factor

```text
G = r^(-T)
```

and the compiled-out source-domain amplitude decay

```text
d = r^T = 1/G.
```

In dB,

```text
D = 20 log10(G) = -20 log10(d).
```

The current compiler default is

```text
max_boundary_gain = 8
```

therefore TW-1A v0 currently refuses a full-horizon broadband schedule requiring more than

```text
G = 8
D = 20 log10(8) = 18.0618 dB amplitude decay
power/energy ratio = G^2 = 64 = 36.1236 dB.
```

This is a compiler policy cap, not a claim that larger values are physically impossible.

---

## 2. Broadband drive schedule

Suppose a broadband schedule has useful nonzero source samples throughout the horizon. Ignoring the source waveform's own crest factor, the damping gauge alone introduces an amplitude span no larger than approximately

```text
S_drive = G.
```

More exactly, if the first and last useful drive samples occur at transition indices `n0` and `n1`,

```text
S_drive = r^(-(n1-n0)).
```

Let a B-bit signed DAC be normalized so the largest compiled sample uses full scale. Let `m` be the required number of quantizer steps for the weakest useful sample. Conservatively,

```text
S_drive <= 2^B / m
```

so

```text
G <= 2^B / m
D <= 6.0206 B - 20 log10(m)  dB.
```

This is the envelope-only condition. A real waveform needs additional codes for its own amplitude information, crest factor, calibration error and headroom.

---

## 3. Impulse drive schedule

A single impulse is different.

If the only nonzero source sample occurs at transition `n0`, its compiled amplitude is simply

```text
u_comp[n0] = r^(-(n0+1)) u_src[n0].
```

There is no *intra-schedule* exponential dynamic-range span because there is only one nonzero source sample.

If per-program analog gain may be chosen, that one impulse can be scaled to DAC full scale and the full horizon `T` does not by itself consume DAC bits. The relevant condition is clipping:

```text
r^(-(n0+1)) |u_src[n0]| <= DAC_full_scale.
```

For an impulse at the beginning of a long experiment, the drive-DAC cost of the damping gauge can therefore remain small even when `G = r^-T` is large.

This does **not** remove the readout/error dynamic-range cost below if the objective is integrated over the whole trajectory.

A terminal-only objective would likewise have only one error injection event and can be rescaled independently; the current executable v0.1 compiler instead supports trajectory quadratic-energy objectives.

---

## 4. Quadratic readout / error schedule

For

```text
J = sum_k w[k] |x_out[k]|^2
```

with `x[k] = r^k z[k]`, the compiled objective is

```text
J = sum_k w[k] r^(2k) |z_out[k]|^2.
```

The returned error/adjoint source therefore carries the same quadratic envelope:

```text
q[k] proportional to r^(2k) z_out[k].
```

Across the full horizon the damping-gauge part of the error schedule spans approximately

```text
S_error = G^2.
```

This is stricter than the forward broadband drive schedule.

With a B-bit error DAC / multiplier and `m` code steps reserved for the weakest useful error sample,

```text
G^2 <= 2^B / m
G <= sqrt(2^B / m)
```

or, in dB,

```text
D <= 3.0103 B - 10 log10(m)  dB.
```

This is the first important closed-form TW-1A bit budget.

### v0.1 design margin

Freeze

```text
m = 4 codes
```

for the weakest gauge-only error-envelope sample.

Then:

```text
B=6:  G <= 4        D <= 12.04 dB
B=7:  G <= 5.657    D <= 15.05 dB
B=8:  G <= 8        D <= 18.06 dB
B=10: G <= 16       D <= 24.08 dB
```

Thus the existing compiler policy `G <= 8` and an 8-bit error-envelope path meet exactly at the conservative 4-code margin.

This is a useful rationale for retaining the current `8x` compiler cap through the first emulator/hardware phase.

---

## 5. Detector SNR bound

The local credit detector obtains a cross term from a differential square-law measurement:

```text
C_e = (E_plus - E_minus)/4.
```

The damping gauge does not require the detector to reconstruct every time sample digitally, but a conservative worst-time budget asks that the weakest quadratic-envelope contribution remain resolvable.

Let `SNR_det` be an amplitude SNR of the differential credit path and `m_snr` the required sigma/margin factor. Requiring the weakest `G^-2` contribution to exceed the detector floor gives

```text
SNR_det >= m_snr G^2.
```

Therefore

```text
G <= sqrt(SNR_det / m_snr)
```

or

```text
D <= 10 log10(SNR_det / m_snr) dB
```

when `SNR_det` is expressed as an amplitude ratio. Equivalently, if detector SNR is quoted in dB as `20 log10(amplitude ratio)`,

```text
D <= 0.5 * (SNR_det_dB - 20 log10(m_snr)).
```

Freeze the same conservative margin

```text
m_snr = 4.
```

For the current `G=8` cap,

```text
required SNR amplitude ratio >= 4 * 64 = 256
required detector SNR >= 20 log10(256) = 48.16 dB.
```

This is a **worst-time representation target**, not a claim that closed-loop learning fails below 48 dB. Integrated credit can remain useful with substantially poorer instantaneous SNR; that is an emulator sweep question.

Differential `E_plus-E_minus` common-mode rejection and pass-to-pass drift impose additional requirements not captured by this scalar SNR formula.

---

## 6. Combined closed-form representation envelope

For a broadband trajectory-energy program, a conservative amplitude-decay limit is

```text
D_max = min(
    20 log10(G_compiler_cap),
    6.0206 B_drive - 20 log10(m_drive),
    3.0103 B_error - 10 log10(m_error),
    0.5 * (SNR_detector_dB - 20 log10(m_snr))
).
```

For the TW-1A v0 defaults

```text
G_compiler_cap = 8
m_drive = m_error = m_snr = 4
B_drive = B_error = 8
SNR_detector_target = 48.16 dB
```

the compiler cap and the quadratic error-path bit budget both give

```text
D_max = 18.06 dB
G_max = 8
minimum represented full-horizon amplitude ratio d_min = 1/8 = 0.125.
```

The forward broadband DAC alone would permit more; the quadratic error schedule is the bit-limiting path at equal converter resolution.

---

## 7. What the emulator must test rather than assume

The formulas above do not tell us the learning-failure boundary for:

- weight quantization;
- DAC/ADC quantization of structured waveforms;
- analog state leakage;
- spatial variation in leakage;
- time-mirror error;
- differential `+/-` pass drift;
- local credit offset/noise;
- analog state noise;
- saturation;
- interactions among those errors.

Those boundaries are empirical properties of the task, optimizer and physical architecture. They are therefore frozen separately in `HARDWARE_ENVELOPE_PREREG_V01.md` and must be swept to failure rather than selected after inspection.
