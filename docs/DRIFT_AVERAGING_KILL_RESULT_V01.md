# TW-1A differential-drift averaging kill test — result v0.1

Preregistration: `docs/DRIFT_AVERAGING_KILL_PREREG_V01.md`

Workflow: `drift-averaging-kill-v01`

Data status: development-only replay on already-spent seeds 970–979.

## Fixed challenge

Rank-one TW-1A, Q/DAC/ADC 8/8/8, v0.7 50% damage terms, but differential PLUS/MINUS operator drift restored to the originally proposed **0.002 RMS = 0.2%**.

At each optimizer step N independent complete AB/BA physical contrast gradients were measured and averaged before one update.

## Result

**KILL: no N <=16 qualifies.**

| repeats N | physical traversals / contrast update | median DeltaC | median placement gap | DeltaC >=0.10 | exact > shuffled | qualified |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 8 | +0.1206 | +0.0601 | 5/10 | 9/10 | FAIL |
| 2 | 16 | +0.0859 | +0.0562 | 5/10 | 6/10 | FAIL |
| 4 | 32 | +0.0559 | +0.0606 | 5/10 | 6/10 | FAIL |
| 8 | 64 | +0.1101 | +0.0552 | 5/10 | 7/10 | FAIL |
| 16 | 128 | +0.0582 | +0.0346 | 5/10 | 5/10 | FAIL |

The response is not even monotonically improved by modest averaging. That is compatible with a quantized nonlinear learner in which averaging changes both false-credit variance and the dither/code-crossing behavior.

## Engineering conclusion

Ordinary small-N repetition is rejected as the primary way to tolerate 0.2% independent pass drift.

The analytical cost warning remains decisive: if independent drift simply averages as `sigma/sqrt(N)`, reducing 0.2% to the measured 20-ppm combined-context boundary requires about 10,000 measurements per update; reaching the demonstrated 10-ppm v0.8 corner requires about 40,000.

The next architecture should therefore suppress differential drift **before subtraction** by making PLUS and MINUS observe a common operator realization (fast chopping/interleaving, simultaneous differential branches, or an equivalent calibrated estimator).
