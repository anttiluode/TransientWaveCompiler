# TW-1A v0.3 combined-corner diagnosis

Bodies 1300-1309 are spent diagnostic bodies after the formal v0.3 simultaneous-corner failure.

## 1. The benchmark was not the problem

The corresponding clean reference was audited on the same bodies:

```text
clean quantized 8/12/8/10/8
  10/10 DeltaC >= +0.10
  10/10 final wins
  median DeltaC +0.588
  median gap    +0.595
  minimum DeltaC +0.299

clean quantized with 10% raw edge + self gain,
self perfectly calibrated
  10/10
  median DeltaC +0.621
  minimum DeltaC +0.405

ideal precision
  10/10
  median DeltaC +0.604
  minimum DeltaC +0.473
```

Therefore the failed v0.3 corner reflects the simultaneous physical error model, not an absolute learning tail of these arbors.

## 2. Charge injection remains the largest interaction

Full v0.3 corner:

```text
5/10 DeltaC >= +0.10
7/10 final wins
median DeltaC +0.087
```

Leave-one-group-out:

```text
remove all edge charge injection
  9/10 DeltaC >= +0.10
  10/10 final wins
  median DeltaC +0.381
  median gap    +0.416
```

No other single deletion came close.

Removing only common injection improved to 6/10. Removing only differential injection did not improve the count. Thus the dominant remaining issue is not merely A/B mismatch; it is that even a coherently replayed edge-switch kick is an additive source applied at every active edge and every tick. It changes the physical trajectory enough to interact with the other circuit errors.

The design response is **near-zero-net-charge sampling**: bottom-plate sequencing, dummy/complementary switches, precharge/autozero, and differential common-mode rejection. The residual specification should apply to the post-cancellation packet, not raw MOS switch charge.

## 3. After charge removal, no single remaining block dominates

With all charge injection removed, the base diagnostic is 9/10 with strong medians. Removing any one additional group does not produce a stable 10/10 rescue; trajectories reshuffle nonlinearly.

This means the residual problem is now genuinely multi-error rather than another single obvious culprit.

## 4. Calibration-first architecture

The clean audit also exposes an architectural inconsistency in the emulator: the physical design has always included calibration observability, but v0.3 still let several calibratable fixed gains enter training as raw process errors.

TW-1A v0.4 should distinguish **raw mismatch** from **post-calibration residual** for:

- reciprocal edge MDAC gain / code-to-coefficient map;
- node self MDAC map;
- fixed unity `-PREV` capacitor ratio;
- terminal A->B clone gain;
- sense range/PGA (already handled).

The host/compiler should program physical coefficients through calibrated inverse maps. `PARAM_HOLD` then freezes the calibrated codes during one gradient evaluation.

This converts fabrication spread into a calibration-headroom/yield question and makes the emulator test the residual errors the real circuit must meet.

## 5. Next gate

Implement v0.4 with:

```text
raw physical mismatch
        ↓ foreground calibration / trim
measured transfer map
        ↓ inverse programming
small residual coefficient error
        ↓ PARAM_HOLD
forward + lockstep reverse
```

and a near-zero-net-charge edge sampler.

A new simultaneous corner must use untouched bodies.