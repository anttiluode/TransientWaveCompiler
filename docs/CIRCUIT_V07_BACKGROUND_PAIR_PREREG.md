# TW-1A v0.7 controlled background pair split

Status: **diagnostic only; seeds 2000--2009 are spent**.

The controlled single-block split found no single removal that restored 10/10.
The strongest seed-specific effects came from four blocks:

- terminal clone residual;
- residual edge switch-kick packet;
- +/- error-DAC sign asymmetry;
- local credit readout noise/offset.

This second-stage split is frozen before any pair result is observed.

## Controlled physical draw

As in the prior controlled split, every condition starts from the exact same
v0.7 formal physical draw for each seed with edge thermal set to zero. Physical
silicon is constructed first; named blocks are then surgically idealized. No
unrelated random draw changes between conditions.

## Frozen pair conditions

All six unordered pairs among the four strongest single-block candidates:

```text
clone + switch_kick
clone + error_sign
clone + credit_readout
switch_kick + error_sign
switch_kick + credit_readout
error_sign + credit_readout
```

No pair or triple is added after results are observed.

## Readout / decision

Report the same 10-body learning summary and seeds 2006/2007/2008. The smallest
pair that restores all ten bodies to improvement >= +0.10 while keeping 10/10
above shuffled credit identifies the minimal interaction that the next physical
contract must remove or tighten. If multiple pairs qualify, prefer structural
changes over merely tighter analog precision, and then freeze quantitative
residual sweeps before opening any fresh qualification gate.
