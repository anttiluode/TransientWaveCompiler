# TW-1A v0.9 kick-drift trained state-range audit — result

Date: 2026-08-09

Status: **PASS: same-range P bank is plausible on the trained benchmark bodies.**

Preregistration: `docs/CIRCUIT_V09_KICK_DRIFT_RANGE_PREREG.md`

The audit reran the fresh-qualified v0.8 learner on spent bodies 2300..2309,
programmed the resulting final edge parameters into the same physical model,
and observed the exactly equivalent coordinates

```text
Z = CUR
P = CUR - PREV
```

through deterministic target/distractor forward and returned C/D fields.

## Result

```text
maximum peak |Z| / old state FS    0.02504897
median  peak |Z| / old state FS    0.01855458
maximum peak |P| / old state FS    0.00323376
median  peak |P| / old state FS    0.00291499
```

Per-body peak P/Z ratios ranged roughly from 0.127 to 0.224.

The preregistered classification is therefore

```text
same_range_plausible
```

not merely `<=1.25x` headroom. The trained P field is much smaller than the
existing conservative state voltage range on these tasks.

## Interpretation

The exact `(Z,P)` representation uses the same two stored vectors per lane and,
on the qualified temporal-order workload family, does **not** hide a larger
P-bank voltage-range requirement. That removes a straightforward storage/range
objection to the kick-drift architecture.

This does not imply that P can immediately be given a tiny capacitor or tiny
voltage range: absolute noise, leakage, OTA input noise and source/error
injection still have to be budgeted. It only says the state trajectory itself
does not require extra P headroom.

The next diagnostic therefore implements the full kick-drift physical learner
and places thermal noise at the actual sampled operations:

```text
P <- P + K*Z + edge/source packets    # edge + residual-self sampling noise
Z <- Z + P                            # unity-drift sampling noise
```

with the terminal inverse-drift mirror paying the same unity-shear mechanism
once.
