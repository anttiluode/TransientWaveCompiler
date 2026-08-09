# TW-1A v0.7 controlled non-edge background split

Status: **diagnostic only; seeds 2000--2009 are spent**.

The controlled edge-residual split showed that removing unit-cap mismatch, edge
map calibration residual, A/B hold mismatch, every pair, or all three together
does **not** rescue the weak 2000--2009 tail when the rest of the formal
physical draw is held fixed.

This experiment therefore isolates the retained non-edge background without
redrawing silicon.

## Common starting point

Every condition starts from the same v0.7 formal physical draw for each seed,
with edge thermal set to zero to make the split deterministic.  The tile is
constructed before any surgical idealization.  No condition changes the edge
capacitor bank, edge calibration realization, or A/B edge-hold realization.

## Frozen conditions

```text
baseline_no_thermal
perfect_state_retention
perfect_self_path
perfect_terminal_clone
perfect_switch_kick
perfect_error_sign
ideal_lcc
perfect_credit_accumulator
perfect_credit_readout
```

Definitions:

`perfect_state_retention`
: sets every held state retention factor to one.

`perfect_self_path`
: removes raw/calibrated self gain error by setting true and measured self gain
  to one; 12-bit self quantization remains.

`perfect_terminal_clone`
: sets effective current/previous terminal copy gains to one. Clone noise is
  already zero in the formal point.

`perfect_switch_kick`
: sets the residual edge injection packets seen by both lanes to zero after the
  existing fabricated/autozero draw has been made.

`perfect_error_sign`
: sets the runtime +/- error-DAC gain asymmetry to zero; 10-bit error
  quantization remains.

`ideal_lcc`
: sets local credit detector curvature to zero.

`perfect_credit_accumulator`
: sets local credit accumulator leakage to zero.

`perfect_credit_readout`
: removes both the 25% local credit noise and the 0.015% local credit DC offset.

No conditions or magnitudes are added after observing results.

## Readout and decision

Report the same 10-body summary and the 2006/2007/2008 tail. If one single block
restores 10/10 improvement >= +0.10, that block becomes the next physical design
target. If none does, freeze a second-stage pair split among only the strongest
single-block improvements before running it.
