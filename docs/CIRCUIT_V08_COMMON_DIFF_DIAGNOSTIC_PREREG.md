# TW-1A v0.8 common/difference reverse diagnostic

Status: **diagnostic only; seeds 2000--2009 are already spent**.

The failed v0.7 formal gate and controlled same-draw diagnostics found a minimal
10/10 rescue when terminal-clone residual and +/- error-DAC sign asymmetry are
both removed.  v0.8 replaces the two stored reverse trajectories with exact
common/difference coordinates so those two analog requirements disappear by
construction rather than by tighter tolerance.

## v0.8 structural substitution

Instead of physical reverse lanes

```text
PLUS  = F + A
MINUS = F - A
```

store

```text
C = (PLUS + MINUS)/2 = F
D = (PLUS - MINUS)/2 = A.
```

At the terminal boundary:

- C is the mirrored forward terminal state already present in the forward lane;
- D.CUR and D.PREV are exact zero boundary states;
- the terminal error waveform is injected once into D with one polarity;
- no analog C->D terminal clone is performed;
- no matched +/- error injection pair exists.

During reverse:

```text
C[n+1] = Q C[n] - C[n-1] + retrace_source[n]
D[n+1] = Q D[n] - D[n-1] + error[n]
```

At each local edge credit sensor only, reconstruct

```text
delta_plus  = delta_C + delta_D
delta_minus = delta_C - delta_D
credit += (square(delta_plus)-square(delta_minus))/4.
```

Thus the existing multiplication-free square/LCC primitive is retained.

## Same-silicon rule

The v0.8 config intentionally retains the inherited terminal-clone and
error-sign-asymmetry fields in the random fabrication draw, but the v0.8
interpreter never consumes them. This preserves the ordering of all unrelated
random draws and avoids the config-level RNG confound discovered during the
v0.7 failure diagnosis.

All other v0.7 formal background remains unchanged: active edge codebooks,
3% unit-cap mismatch, A/B-now-C/D hold mismatch, switch-kick residuals, state
leakage, self calibration, converters, LCC curvature, credit noise/offset and
credit accumulator leakage.

## Frozen spent bodies

```text
2000--2009
```

## Frozen conditions

Exactly two:

```text
common_diff_b0      edge kT/C base b = 0
common_diff_b1e-5   edge kT/C base b = 1e-5
```

No additional thermal points or other idealizations are added after observing
these results.

## Reported predicate

For each condition report:

```text
count improvement >= +0.10
count final exact > shuffled
median/min improvement
median/min placement gap
per-seed 2006/2007/2008 values
```

A 10/10 result at b=1e-5 is sufficient to proceed to a new v0.8 physical
contract and quantitative residual studies. It is not a fresh qualification.
Fresh seeds are not reserved in this document.
