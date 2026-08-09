# TW-1A v0.9 seed 2400 same-draw pair split — preregistration

Date: 2026-08-09

Status: **diagnostic only on spent seed 2400.**

The same-draw single-block split used a common all-thermal-zero baseline:

```text
baseline                         +0.047842
no inherited edge kick          +0.093745
no drift residual               +0.081666
ideal edge codebook             +0.062030
exact kick-self gain            +0.058980
no leakage                      +0.055303
ideal credit path               +0.054785
ideal converters                +0.052692
exact edge lane holds           +0.047842
all support clean               +0.791364
```

No single physical/support block reaches +0.10, while the same silicon becomes strongly learnable when the support stack is cleaned jointly. The next diagnostic therefore tests all six unordered pairs among the four largest single-block improvements.

## Anti-redraw rule

Use exactly the same construction and post-construction surgery machinery as `experiments/v09_seed2400_static_split.py`:

- exact formal v0.9 seed/config constructed first;
- exact same static disorder copied into target/distractor/shuffled tiles;
- same frozen PGA = 32;
- edge/self/drift thermal bases set to zero only after construction;
- no fabrication sigma changes before construction.

## Frozen pair conditions

```text
edge_kick + drift_residual
edge_kick + edge_codebook
edge_kick + kick_self_gain
drift_residual + edge_codebook
drift_residual + kick_self_gain
edge_codebook + kick_self_gain
```

Each surgery has exactly the meaning defined in `docs/CIRCUIT_V09_SEED2400_STATIC_SPLIT_PREREG.md`.

## Decision frozen before results

- If one or more pairs produce improvement >= +0.10, the smallest/highest-margin pair becomes the next interaction target. Do not infer that either member individually needs to be zero in hardware; follow with a quantitative residual sweep around the formal values.
- If no pair reaches +0.10, do not cherry-pick a triple. First split the remaining support stack into larger physically meaningful groups (state/operator vs acquisition/credit) to find where the higher-order interaction resides.

This is a one-body diagnosis only and does not authorize fresh qualification.
