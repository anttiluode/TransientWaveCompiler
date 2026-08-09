# TW-1A residual interaction diagnosis v0.2

These are diagnostics on the already-spent v0.1 corner bodies 1200-1209. Every case first removes the dominant independent lane-select charge-injection term, then removes one additional error group.

Artifact: `circuit-native-corner-diagnose-v02`, workflow run 31302537469.

## Result

With charge injection removed but every other v0.1 corner error retained:

```text
8/10 DeltaC >= +0.10
8/10 placed final > shuffled
median DeltaC  +0.346
median gap     +0.236
```

Adding one further removal:

| charge injection removed + ... | n DeltaC>=.10 | final wins | median DeltaC | median gap |
|---|---:|---:|---:|---:|
| nothing else | 8/10 | 8/10 | +0.346 | +0.236 |
| old leakage/noise/readout background | 8/10 | 9/10 | +0.216 | +0.189 |
| common edge gain mismatch | 7/10 | 7/10 | +0.200 | +0.161 |
| **self-MDAC gain mismatch** | **10/10** | **10/10** | **+0.366** | **+0.359** |
| `-PREV` ratio error | 6/10 | 7/10 | +0.268 | +0.262 |
| terminal clone error | 9/10 | 9/10 | +0.406 | +0.353 |
| A/B settling-memory-sign group | 7/10 | 8/10 | +0.144 | +0.132 |
| credit path errors | 8/10 | 8/10 | +0.349 | +0.256 |
| storage/leakage/`-PREV` group | 8/10 | 8/10 | +0.300 | +0.259 |
| self + `-PREV` errors | 7/10 | 8/10 | +0.387 | +0.387 |

The particularly important line is the self-MDAC result: **removing only charge injection and self gain mismatch satisfies all of the original v0.1 simultaneous-corner numerical predicates on the spent diagnostic bodies**, including a minimum body improvement of about `+0.117`.

This is not a new qualified corner because the bodies are spent. It is nevertheless a strong architectural diagnosis.

## Interpretation

The first simultaneous corner did not fail because every analog error accumulated generically. It failed mainly because of two implementation choices:

1. an independent lane-select edge kick was injected every tick;
2. the large residual node self coefficient was treated as an uncalibrated analog gain with 0.3% spatial CV.

The second is especially actionable. The architecture already provides a digital 12-bit self coefficient. There is no reason to accept raw analog gain error as the effective programmed coefficient.

## TW-1A v0.3 response

### Charge-balanced edge sampling

Replace independent A/B switch injection with a correlated decomposition:

```text
q_A = q_common + q_diff
q_B = q_common - q_diff
```

and use the same `q_common` component in the forward edge sampling path. Bottom-plate switching, dummy/complementary transmission gates and precharge/autozero are intended to make `q_diff` much smaller than total switch injection.

The relevant hardware specification becomes **residual differential injection**, not absolute switching charge.

### Foreground self-path calibration

For node `i`, measure the effective self-MDAC gain/code map with neighbor edges disabled or held in a known state. Store a calibration mapping `code_i(d)` and let the backend compile desired residual self coefficient `d_i` through that map.

At minimum the emulator can represent this as:

```text
raw physical gain       g_i
measured gain           ghat_i
programmed code target  d_i / ghat_i
actual coefficient      quantize(d_i/ghat_i) * g_i
```

Thus large raw process mismatch is converted into a much smaller **calibration residual plus code quantization**.

This is preferable to specifying an unrealistically precise uncalibrated +/-3.0 analog multiplier.

## Next evidence gate

A v0.3 emulator should implement both changes explicitly. A revised simultaneous corner must then be preregistered on untouched bodies, not selected from these 1200-1209 diagnostics.