# TW-1A hardware envelope — near-zero refinement and combined backoff result v0.6

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V06.md`

Workflow: `hardware-envelope-order-v06`

## Stage A — refined near-zero boundaries

Fresh seeds 940–945, Q/DAC/ADC = 8/8/8.

### Analog state noise

Pass prefix:

`0, 1e-8, 3e-8`

First registered failure: **`1e-7` of internal state full scale RMS per node per tick**.

Therefore:

- measured boundary: **`3e-8 FS`**;
- preregistered one-step-inward recommendation: **`1e-8 FS`**.

With the frozen +/-20 internal state full scale, these correspond to:

- boundary RMS amplitude: **`6e-7` state units** per node per tick;
- recommended RMS amplitude: **`2e-7` state units** per node per tick.

This remains the tightest requirement in the current emulator.

### Local credit DC offset

Pass prefix:

`0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3`

First registered failure: **`0.002 = 0.2%`**.

Therefore:

- measured boundary: **`0.001 = 0.1%`**;
- one-step-inward recommendation: **`0.0003 = 0.03%`**.

This confirms the qualitative v0.5 result: systematic local bias is much more dangerous than zero-mean local credit noise.

## Stage B — combined backoff discovery

Fresh seeds 946–951.

The full `s=1` damage vector used the v0.5 recommendations plus the refined near-zero values:

- leakage rate: `0.001/tick`;
- leakage CV: `1.0`;
- mirror error: `0.30`;
- differential +/- pass drift: `0.0005`;
- credit noise: `0.50`;
- state noise: `1e-8 FS`;
- credit offset: `0.0003`.

Every preregistered discovery scale passed:

`0, 0.25, 0.50, 0.75, 1.00`.

Thus the discovery boundary was at least **`s=1.0`**. Per the frozen safety rule, the final confirmation used **`s=0.75`** rather than the full vector.

## Stage C — 75% simultaneous corner

Fresh seeds 952–961.

The tested simultaneous corner was:

- Q/DAC/ADC: **8/8/8**;
- leakage: **0.00075/tick**;
- leakage CV: **0.75**;
- mirror error: **0.225 = 22.5%**;
- differential +/- drift: **0.000375 = 0.0375% RMS**;
- zero-mean credit noise: **0.375 = 37.5%**;
- credit DC offset: **0.000225 = 0.0225%**;
- state noise: **`7.5e-9 FS`** = `1.5e-7` state-unit RMS with +/-20 full scale.

**Registered result: FAIL.**

The failure was a robustness-tail condition rather than broad collapse:

- median exact `DeltaC`: **+0.70375**;
- median placed-vs-shuffled improvement gap: **+0.50734**;
- 8/10 reached `DeltaC >= 0.10`;
- exact final contrast beat shuffled final in 8/10;
- all values finite;
- but the preregistration also required **every** exact learner to improve, and that failed.

The two weak-tail cases were:

- seed 952: `DeltaC = -0.00295`, placement gap `-0.05889`;
- seed 955: `DeltaC = +0.05789`, placement gap `-0.05828`.

The other eight seeds improved strongly.

Therefore v0.6 does **not** earn the 75% simultaneous corner. A more conservative backoff may be tested only under a new preregistration and fresh confirmation seeds.

## Current hardware picture after v0.5 + v0.6

The most robust conclusions now are:

- represent one physical trainable bond as one reciprocal rank-one edge cell;
- clean 8-bit Q/DAC/ADC learning is strong;
- benchmark-specific precision floors are Q >=5 bits, DAC >=4 tested bits, ADC >=5 bits with static PGA;
- architecture-wide returned-error dynamic range for the compiler's full `G=8` promise remains a separate, stricter converter-budget issue;
- common time-mirror gain error is highly tolerated compared with differential +/- pass drift;
- zero-mean credit noise is highly tolerated compared with systematic credit offset;
- mean state leakage matters much more than frozen leakage CV around a small mean;
- analog per-tick state noise is the tightest modeled requirement;
- independently safe maxima cannot be assumed to compose without backoff.
