# TW-1A v0.8 site-ratio/headroom learning diagnostic

Status: **diagnostic only; seeds 2000--2009 are spent**.

v0.8 common/difference coordinates passed 10/10 on the failed v0.7 task bodies
at `b=1e-5`, but that diagnostic inherited the 0.255 nominal edge range and did
not include a site-common Cunit/Cstate ratio error. A separate 20,000-tile yield
study showed that at 1% RMS site ratio error, nominal 0.255 edge range gives poor
112-edge tile yield, 0.260 is marginal (~99%), and 0.265 was all-pass in that
Monte Carlo.

This diagnostic freezes one more realistic v0.8 point before fresh seeds are
spent.

## Frozen physical point

```text
reverse coordinates                 common/difference v0.8
edge nominal positive full scale    0.265
Cunit/Cstate                         0.265 / 127
unit-cap mismatch                    3% RMS independent units
site-common Cunit/Cstate mismatch    1% RMS independent edge sites
edge thermal base b                  1e-5
```

All other v0.8 background remains unchanged from the spent-body common/diff
thermal diagnostic: A/B-now-C/D hold mismatch, switch-kick residuals, state
leakage, self calibration, converter precision, LCC curvature, credit
noise/offset and credit accumulator leakage. Terminal clone and +/- error-sign
matching remain structurally absent.

The site-common ratio draw uses a dedicated deterministic RNG stream so adding
this fabrication axis does not redraw any pre-existing disorder.

## Fabrication gate

For each of seeds 2000--2009, before learning:

- all 112 codebooks must remain strictly monotonic;
- all site ratio scales must be positive;
- all 112 code-127 physical ranges must be >=0.25.

The measured site-specific codebook is used directly. No sorting, repair or
extrapolation is permitted.

## Learning readout

Report the same diagnostic predicate:

```text
10/10 improvement >= +0.10
10/10 final exact > shuffled
median improvement >= +0.30
median placement gap >= +0.25
```

If all fabrication gates and the learning predicate pass, the next fresh v0.8
qualification seeds are reserved as **2100--2109**. No further parameter tuning
on those fresh seeds is allowed before the preregistered formal result is read.
