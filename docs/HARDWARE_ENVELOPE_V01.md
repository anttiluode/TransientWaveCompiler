# TW-1A hardware-emulator envelope v0.1 — result

Date: 2026-08-09

Preregistration: `docs/HARDWARE_ENVELOPE_PREREG_V01.md`

Dynamic-range derivation: `docs/DYNAMIC_RANGE_BUDGET.md`

Baseline result: `docs/HARDWARE_BASELINE_V01_FAIL.md`

Workflow: `hardware-envelope-v01`, run 31295526187

## Result in one sentence

> **The first preregistered hardware-envelope experiment did not earn a simple TW-1A build specification: the requested 8-bit operating point failed, and that failure masked every one-axis tolerance sweep except for a strongly non-monotone weight-quantization effect in which only the 5-bit point passed the frozen learning criterion.**

This is a useful failure. It says the next problem is not yet “how much leakage can the chip tolerate?” It is “what precision/readout operating point makes this compiled transient task observable and trainable in the first place?”

---

## 1. What was already established before this sweep

The clean emulator credit was checked against central finite differences on the compiled irregular-arbor task before the noisy baseline was interpreted.

That audit passed.

Therefore the v0.1 failure is not explained by an obvious sign or time-index error in

```text
(E_plus - E_minus)/4
```

or in the compiled edge-credit scale.

The requested 8-bit baseline then failed formally:

```text
seed 810   exact reduction +0.00000
seed 811                   +0.41484
seed 812                   +0.00000
seed 813                   +0.30309
seed 814                   +0.00000
```

Only 2/5 tasks cleared 10% reduction and the median reduction was zero.

---

# 2. Frozen v0.1 sweep results

All one-axis sweeps retained every other baseline setting exactly as preregistered.

## Converter bits — DAC and ADC tied

Weight resolution remained fixed at the failing 8-bit baseline value.

```text
bits   usable   median exact R   median shuffled R   >=10% exact   exact<shuffle loss
12     NO       +0.0912          +0.1346              2/5            2/5
10     NO       +0.0000          +0.0000              2/5            2/5
8      NO       +0.0000          +0.0000              2/5            1/5
7      NO       +0.0000          +0.0000              0/5            1/5
6      NO       +0.0000          +0.0000              0/5            1/5
5      NO       +0.0000          +0.0000              0/5            0/5
4      NO       +0.0000          +0.0000              0/5            0/5
3      NO       +0.0000          +0.0000              0/5            0/5
```

No converter-bit requirement is earned. Even 12-bit converters do not rescue the task while the weight path remains at the failing 8-bit operating point.

This rules out the simplest interpretation of the baseline failure:

```text
"the ADC was merely too coarse"
```

at least when coefficient resolution and all other baseline imperfections remain unchanged.

---

## Programmable edge-weight bits

DAC/ADC stayed at the failing 8-bit baseline value.

```text
bits   usable   median exact R   median shuffled R   gap       >=10% exact   exact better
12     NO       +0.0000          +0.0000             +0.0000   2/5            1/5
10     NO       +0.0000          +0.0000             +0.0000   1/5            1/5
8      NO       +0.0000          +0.0000             +0.0000   2/5            1/5
7      NO       +0.0000          +0.0000             +0.0000   1/5            1/5
6      NO       +0.8919          +0.7938             +0.0980   5/5            3/5
5      YES      +0.8764          +0.7130             +0.1633   5/5            4/5
4      NO       -1.1312          -2.2120             +1.0808   1/5            3/5
3      NO       +0.0000          +0.0000             +0.0000   0/5            1/5
```

The helper's mechanical summary says `minimum_passing=5`, but that is **not a valid hardware-resolution requirement** because the response is violently non-monotone.

If ordinary precision were the limiting resource, 12/10/8 bits should not all fail while 5 bits passes.

The scientifically defensible statement is instead:

> **Coarse coefficient quantization changes the effective wave computation enough to create a trainable operating regime around 5–6 bits for this frozen task family.**

Possible mechanisms include spectral relocation, larger effective parameter jumps, escape from quantized objective plateaus, altered transfer amplitude, or some combination. Those are development questions to distinguish before any bit specification is frozen.

The 4-bit point then overshoots catastrophically, so “coarser is better” is also false.

---

## Common leakage rate

Every frozen level failed, including zero added leakage.

```text
rate/tick
0
1e-4
2e-4
5e-4
1e-3
2e-3
5e-3
1e-2
2e-2
5e-2

all: FAIL
```

No leakage tolerance can be inferred because the undamaged baseline for this axis already fails.

---

## Spatial leakage CV at mean rate .002/tick

Every frozen CV failed, including CV=0.

```text
0, .10, .20, .30, .50, .75, 1.0, 1.5

all: FAIL
```

No leakage-disorder tolerance is earned.

---

## Time-mirror error

Every point failed, including an exact mirror:

```text
0, .02, .05, .10, .20, .30, .50, .75, 1.0

all: FAIL
```

Therefore v0.1 does **not** say that the mirror must be more accurate than 5%. The precision operating point is already unusable even at zero mirror error.

---

## Differential +/- pass drift

Every point failed, including zero differential drift:

```text
0, .0005, .001, .002, .005, .01, .02, .05

all: FAIL
```

No pass-stability requirement is earned from v0.1.

---

## Credit readout noise

Every point failed, including zero credit noise:

```text
0, .02, .05, .10, .20, .50, 1.0

all: FAIL
```

Again, the baseline precision regime masks the tolerance axis.

---

# 3. What v0.1 did earn

## Analytical representation envelope

The closed-form compiler-side result remains valid independently of the noisy learning failure.

For the current v0 compiler policy

```text
G_max = 8
```

TW-1A represents at most

```text
18.06 dB full-horizon compiled-out amplitude decay
36.12 dB corresponding quadratic-envelope span.
```

With the preregistered four-code margin, an 8-bit quadratic error-envelope path is exactly sufficient for that `G=8` representation target, and the conservative worst-time detector target is 48.16 dB differential SNR.

These are representation requirements, not yet sufficient learning requirements.

## Clean physical-credit semantics

The emulator's ideal four-pass local credit agrees with finite-difference differentiation of the compiled task.

Thus a viable noisy operating point is worth searching for; the failure is not presently evidence that the echo-gradient architecture itself is wrong.

## Baseline design lesson

A hardware tolerance envelope cannot be swept around an operating point that already fails its task.

The next experiment must therefore be hierarchical:

```text
1. establish a viable joint precision/readout operating point;
2. freeze that point;
3. only then sweep leakage, mirror error, drift and credit noise to failure.
```

---

# 4. Immediate development diagnostic

Before preregistering v0.2, use only the already-seen v0.1 seeds 810–814 and determine what the 5-bit coefficient point is doing.

For each weight resolution measure before training:

```text
Q quantization error
compiled Q eigenvalue range / modal movement
raw output RMS and peak before ADC
ADC output code occupancy
quantized objective value
small parameter-step -> physical Q change rate
small parameter-step -> objective-code change rate
```

Also run a joint `(weight_bits, converter_bits)` development grid. The v0.1 one-axis design never tested high converter precision and high coefficient precision at the same time.

The purpose is mechanism discovery only. No hardware threshold may be claimed from these already-inspected task seeds.

---

# 5. Required v0.2 logic

After the diagnostic, freeze a new seed block and a joint precision/readout operating point **before** tolerance sweeps.

Only if that fresh operating point passes the same learning/control criteria may v0.2 report statements of the form

```text
weight resolution >= X bits
converter resolution >= Y bits
leakage <= Z/tick
mirror error <= M
+/- drift <= P
```

If no monotone operating envelope appears, report that honestly rather than forcing a digital-style bit specification onto a resonant analog wave machine.

## v0.1 wall sentence

> **TW-1A v0.1 does not yet have an empirical build envelope. Its exact echo credit is correct, but the first 8-bit mixed-signal operating point is not reliably trainable; coefficient quantization changes the wave computation non-monotonically, with a narrow 5–6-bit regime outperforming more precise settings. Precision, scaling and modal placement must therefore be treated as part of compilation rather than as independent implementation noise before leakage/mirror/drift limits can be meaningfully specified.**
