# TW-1A failed-corner diagnosis v0.1

These diagnostics use the already-spent v0.1 simultaneous-corner bodies 1200-1209. They are **diagnostic only** and cannot qualify a revised operating corner.

Artifact: `circuit-native-corner-diagnose-v01`, workflow run 31302373117.

## Result

The full corner reproduced the preregistered failure:

```text
3/10 DeltaC >= +0.10
5/10 placed final > shuffled
median DeltaC  +0.0073
median gap     +0.0033
```

Removing one error group at a time gave:

| diagnostic | n DeltaC>=.10 | final wins | median DeltaC | median gap |
|---|---:|---:|---:|---:|
| full failed corner | 3/10 | 5/10 | +0.007 | +0.003 |
| remove older leakage/noise/readout background | 4/10 | 7/10 | +0.084 | +0.012 |
| remove common edge gain mismatch | 1/10 | 6/10 | +0.040 | +0.030 |
| remove self gain mismatch | 3/10 | 8/10 | +0.046 | +0.008 |
| remove `-PREV` ratio error | 4/10 | 7/10 | +0.039 | +0.017 |
| remove terminal clone error | 1/10 | 5/10 | +0.019 | +0.002 |
| remove A/B settling-memory-sign group | 2/10 | 9/10 | +0.026 | +0.040 |
| **remove lane-select edge charge injection** | **8/10** | **8/10** | **+0.346** | **+0.236** |
| remove credit-path errors | 2/10 | 6/10 | +0.009 | +0.009 |
| remove storage/leakage/`-PREV` group | 4/10 | 9/10 | +0.056 | +0.051 |
| **older background only; all new circuit errors removed** | **10/10** | **10/10** | **+0.698** | **+0.672** |

## Main diagnosis

The v0.1 simultaneous collapse is dominated by the modelled **lane-select-dependent edge charge injection**.

Removing only that term moves the system from effectively dead learning to strong median learning. No other single deletion produces a comparable rescue.

The older emulator background is not the explanation: with the old leakage, leakage CV, state noise, credit readout noise and credit offset present, but the new circuit-specific errors removed, all 10/10 bodies learn strongly.

Therefore the next circuit revision should attack charge injection structurally rather than tightening every analog tolerance.

## Why the present injection model is hostile

The v0.1 emulator gives lane A and lane B independent fixed edge-switch injection packets on every active physical edge, every wave tick. Each packet is stamped equal/opposite into the two edge endpoints.

That is exactly the kind of error the lockstep architecture was intended to avoid: a systematic **differential forcing term** that is absent from the mathematical reciprocal operator and is repeatedly accumulated through the reverse trajectory.

At the one-axis level `3e-5` of state full scale looked conservative. In the simultaneous corner, interactions with coefficient mismatch, state-history error, terminal copy and readout corruption make that repeated forcing far more destructive.

## Circuit response

TW-1A v0.3 should not simply specify a smaller independent kick number. The edge sampler should be **charge-balanced** so most switch injection is one common physical event and only a residual differential component separates lanes A and B.

Candidate first implementation:

```text
shared bottom-plate edge sampler
        |
        +-- lane A sample/transfer
        |
        +-- complementary dummy / return phase
        |
        +-- lane B sample/transfer

q_A = q_common + q_diff
q_B = q_common - q_diff
```

with differential state storage, bottom-plate sampling, complementary/dummy transmission gates and an explicit autozero/precharge phase.

The next emulator must therefore split:

- **common edge charge injection**, shared by A/B and forward/reverse where appropriate;
- **residual differential edge charge injection**, the quantity the physical balancing circuit must suppress.

The old independent-A/B injection model remains as a killed v0.2 implementation choice.

## Residual interaction

Removing injection alone still leaves two failing tails (8/10 rather than 10/10). Thus charge balancing is necessary but not yet sufficient for a demonstrated simultaneous corner.

A second diagnostic on the same spent bodies may remove one additional group on top of charge injection to identify the next interaction. Any new combined corner must use untouched bodies.