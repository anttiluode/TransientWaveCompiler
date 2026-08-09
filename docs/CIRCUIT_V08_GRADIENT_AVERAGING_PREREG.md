# TW-1A v0.8 complete-gradient averaging trade — preregistration

Date: 2026-08-09

Status: **diagnostic on spent fresh-qualified bodies 2300..2309. No fresh seeds authorized.**

The combined thermal sweep showed that

```text
b_edge = b_self = 2e-5
```

fails the frozen 30-update learning predicate, but all 10 bodies still finish with exact credit above the same-credit shuffled control. This suggests that useful gradient ordering survives while one-echo stochastic SNR is insufficient.

This experiment tests a pure area/time trade without changing the analog topology.

## Frozen physical corner

Use the exact v0.8 fresh-qualified hardware model except:

```text
edge thermal base = 2e-5
self thermal base = 2e-5
```

Everything else stays frozen, including:

- common/difference reverse coordinates;
- structural `-PREV`;
- 0.265 nominal edge range;
- 3% RMS unit-cap mismatch;
- 1% RMS site-common ratio mismatch;
- 0.5% kick-cancellation measurement error;
- 2 ppm common / 1 ppm differential kick floors;
- converter, leakage, LCC and credit-path settings;
- 30 parameter updates;
- step size 0.20;
- same fixed task-specific sense PGA;
- same shuffled-credit control.

## Averaging definition

For each parameter update, execute `M` independent complete physical target/distractor echoes on the **same held fabricated tile and same current parameters**.

For repeat `r`, compute the same physical contrast-gradient estimate as the existing learner:

```text
g_r = contrast_gradient(E_target_r, E_distractor_r,
                        credit_target_r, credit_distractor_r)
```

Then apply one update using

```text
g_bar = (1/M) * sum_r g_r.
```

The shuffled control receives the same averaged credit vector with the same fixed edge permutation as before.

This is deliberately **gradient averaging**, not averaging deterministic validation scores and not silently increasing the number of learning updates.

## Frozen repeat counts

```text
M = 1, 2, 4, 8
```

`M=1` must reproduce the previously failed combined-thermal `2e-5` behavior closely enough to serve as an implementation check.

## Frozen predicate

After the same 30 parameter updates:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

## Interpretation

- If `M=2` is clean, the `b=2e-5` thermal scale becomes an especially attractive candidate: 4x smaller kT/C capacitance for 2x echo traversal count per update. Ideal capacitor-switching energy associated with those thermal capacitors scales roughly as `M/4`, before OTA/clock/reference overhead.
- If only `M=4` is clean, capacitor area still falls 4x but ideal capacitor-switching work is roughly break-even; latency and active-circuit energy increase.
- If `M=8` is required or all fail, averaging is unlikely to rescue the first-chip economics by itself.

The experiment does not claim that dynamic energy is exactly proportional to capacitance. OTA, clock, ADC/DAC, credit and reference energy must be counted separately.
