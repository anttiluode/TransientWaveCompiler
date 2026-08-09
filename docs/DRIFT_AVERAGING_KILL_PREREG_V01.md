# TW-1A differential-drift averaging kill test — preregistration v0.1

Date frozen: 2026-08-09

## Motivation

The v0.8 emulator demonstrated a strong simultaneous mixed-signal corner when differential REVERSE_PLUS / REVERSE_MINUS operator drift was limited to 10 ppm RMS. The originally proposed hardware model used 0.2% RMS = 2000 ppm independent pass drift.

If independent zero-mean drift averaged ideally, reaching the measured combined-context 20-ppm boundary would require roughly

`N = (0.002 / 0.00002)^2 = 10,000`

independent measurements, and reaching the demonstrated 10-ppm corner would require roughly 40,000. Ordinary averaging therefore looks unattractive analytically.

This experiment is a **kill test**, not a search for a pass. It asks whether the nonlinear closed-loop learner gains unexpectedly large robustness from modest repeated measurements.

## Data status

Use only the already-spent v0.7 seeds:

`970,971,972,973,974,975,976,977,978,979`.

Therefore this experiment cannot establish a new hardware result. It may only decide whether small-N averaging deserves fresh confirmation.

## Fixed hardware/task model

Use the rank-one v0.5 TW-1A emulator and temporal-order benchmark unchanged.

Keep the v0.7 50% simultaneous damage terms except set differential drift to the originally proposed 0.2%:

- Q/DAC/ADC = 8/8/8;
- leakage = 0.0005/tick;
- leakage CV = 0.50;
- mirror error = 0.15;
- differential PLUS/MINUS drift = **0.002 RMS**;
- zero-mean credit readout noise = 0.25;
- credit offset = 0.00015;
- state noise = 5e-9 FS;
- static PGA enabled.

Optimizer remains:

- 40 updates;
- step size 0.20;
- RMS-normalized update;
- same shuffled-credit control definition.

## Repeated estimator

At each optimizer iteration, hold theta fixed and perform N independent complete AB/BA physical credit measurements.

For repetition r:

1. execute ordinary target AB four-pass energy/credit measurement;
2. execute ordinary distractor BA four-pass energy/credit measurement;
3. form that repetition's exact normalized-contrast gradient using its measured energies and physical credits.

Average the N combined contrast-gradient vectors arithmetically, then apply one host update.

The shuffled arm receives the same averaged gradient values with its fixed edge permutation.

Every repetition receives fresh emulator pass-drift/noise draws. No common-mode drift is introduced.

## Frozen repeat counts

`N = [1, 2, 4, 8, 16]`.

No larger N may be added after inspecting these results under this preregistration.

## Evaluation predicate

Use the existing ten-seed final hardware predicate:

1. every exact learner has DeltaC > 0;
2. at least 8/10 have DeltaC >= 0.10;
3. median DeltaC >= 0.15;
4. exact final contrast beats shuffled final contrast in at least 8/10;
5. median placed-vs-shuffled improvement gap >= 0.10;
6. all values finite.

## Decision rule

Small-N averaging **survives** only if at least one N <=16 satisfies the entire predicate on these spent seeds.

If no N<=16 qualifies, kill ordinary small-N averaging as the primary solution to 0.2% pass drift. The next architecture must instead suppress drift before subtraction, e.g. by common-realization chopping/simultaneous differential measurement or explicit calibration.

If an N<=16 unexpectedly qualifies, freeze the smallest qualifying N and test it on fresh seeds before making any claim.
