# TW-1A v0.9 kick-drift state-range audit — preregistration

Date: 2026-08-09

Status: diagnostic on spent bodies 2300..2309.

Exact kick-drift coordinates replace each position-history pair by

```text
Z = CUR
P = CUR - PREV.
```

This uses the same number of stored vectors, but that does not guarantee the P
bank can use the same voltage/full-scale range as Z. In principle `|P|` can
reach twice the clipped Z full scale.

## Frozen audit

For each spent body 2300..2309:

1. rerun the existing fresh-qualified v0.8 self-thermal learner for the same 30 updates;
2. program the resulting final trainable edge vector back into the same static physical tile;
3. execute deterministic target and distractor forward+returned common/difference echoes;
4. at every stored state, report

```text
Z = current
P = current - previous
```

for forward C and returned C/D contexts;
5. normalize peak magnitudes to the existing v0.8 `state_full_scale`.

No kick-drift clipping is introduced in this audit; it observes the exactly equivalent v0.8 trajectories.

## Interpretation frozen before results

```text
peak |P| <= 1.00 state FS   same-range P bank is plausible
peak |P| <= 1.25 state FS   modest P headroom required
peak |P| <= 1.50 state FS   material voltage/capacitance headroom cost
peak |P| >  1.50 state FS   do not call (Z,P) a storage-neutral replacement
```

The audit also reports peak |P|/peak |Z| and separates forward from reverse. It does not authorize fresh seeds or a new chip version.
