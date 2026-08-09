# TW-1A hardware requirements envelope — rank-one edge-cell result v0.5

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V05.md`

Workflow: `hardware-envelope-order-v05`

## Executive result

The v0.5 edge-cell hardware semantic fixed the precision pathology seen in v0.1–v0.4 and produced clean, monotone benchmark-specific bit floors plus measurable physical-imperfection boundaries.

However, the preregistered **combined conservative corner failed narrowly**, so no claim is made that all independent recommended tolerances can be simultaneously realized without further backoff.

## Stage A — precision floors

Fresh seeds 910–915.

| path | 4 bits | 5 bits | 6 bits | 7 bits | 8 bits | 9 bits | 10 bits | 12 bits | stable minimum |
|---|---|---|---|---|---|---|---|---|---:|
| rank-one edge-cell Q | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **5** |
| drive/error DAC | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **4** |
| sense ADC + static PGA | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **5** |

Thus, within this benchmark and exact quantizer/PGA contract:

- edge-cell Q precision has a demonstrated stable floor of **5 bits**;
- DAC precision has a demonstrated floor of **4 bits or lower** (4 is the lowest tested);
- ADC precision has a demonstrated stable floor of **5 bits**.

These are task-specific floors. They do not replace the separate architecture-wide boundary-gain dynamic-range requirement.

### Clean 8-bit joint point

Fresh seeds 916–921:

**8-bit Q / 8-bit DAC / 8-bit ADC: PASS.**

- median `DeltaC`: **+0.9601**;
- median placed-vs-shuffled improvement gap: **+0.9503**;
- 6/6 reached `DeltaC >= 0.10`;
- exact final contrast beat shuffled final in 6/6.

### Originally requested nominal mixed-signal point

On the same fresh block:

- Q/DAC/ADC = 8/8/8;
- mirror error = 5%;
- differential +/- pass drift = 0.2%;
- local credit noise = 5%;
- other damage axes zero.

**Result: PASS on this 6-seed block.**

- median `DeltaC`: **+0.2776**;
- median placement gap: **+0.3428**;
- 6/6 reached `DeltaC >= 0.10`;
- exact final beat shuffled final in 5/6.

This is encouraging but does not override the separate one-axis drift boundary below.

## Stage B — independent damage boundaries at 8/8/8

Fresh seeds 922–927.

### Leakage rate per tick

- pass prefix: `0, 0.0001, 0.0002, 0.0005, 0.001, 0.002`;
- first failure: **0.005**;
- measured boundary: **0.002/tick**;
- preregistered inward recommendation: **0.001/tick**.

### Time-mirror error

- pass through **0.50**;
- first failure: **0.75**;
- inward recommendation: **0.30**.

The learning mechanism is therefore surprisingly insensitive to mirror-gain error in this model.

### Differential REVERSE_PLUS / REVERSE_MINUS parameter drift

- pass prefix: `0, 0.0005, 0.001`;
- first failure: **0.002**;
- measured boundary: **0.001 = 0.1% RMS**;
- inward recommendation: **0.0005 = 0.05% RMS**.

This is one of the tight hardware requirements.

### Analog state noise

- zero-noise point passed;
- the first tested nonzero point, `1e-5` of state full scale RMS per node per tick, failed the registered predicate.

Therefore v0.5 resolves only:

`state_noise_std < 1e-5 of full scale`

and requires a finer near-zero sweep before a nonzero requirement can be stated.

With the frozen +/-20 state full scale, `1e-5` corresponds to RMS noise amplitude `2e-4` state units injected per node per tick.

### Local credit readout noise

Every tested point through **1.00 = 100% RMS of credit RMS** qualified.

- measured lower bound on tolerance: **>=100%** under this noise model;
- inward recommendation because the grid ended: **50%**.

This suggests zero-mean detector noise is far less dangerous than systematic bias or differential pass mismatch.

### Local credit DC offset

- zero offset passed;
- first tested nonzero point, **0.005 = 0.5%**, failed the registered predicate.

Thus the nonzero offset boundary is unresolved below 0.5% and needs a finer sweep.

### Leakage spatial CV

At recommended mean leakage `0.001/tick`, every tested CV through **1.50** qualified.

- measured lower bound on tolerance: **>=150% CV**;
- inward recommendation: **100% CV**.

The model is much more sensitive to mean dissipative loss than to frozen spatial variation around a small mean loss.

## Stage C — combined conservative corner

Fresh seeds 930–939.

Combined preregistered recommendations:

- Q/DAC/ADC = 8/8/8;
- leakage = 0.001/tick;
- leakage CV = 1.0;
- mirror error = 0.30;
- differential pass drift = 0.0005;
- state noise = 0;
- credit noise = 0.50;
- credit offset = 0.

**Result: FAIL narrowly.**

- median exact `DeltaC`: **+0.2122**;
- median placed-vs-shuffled improvement gap: **+0.2775**;
- exact final contrast beat shuffled final in **9/10**;
- only **7/10** seeds reached `DeltaC >= 0.10` (required 8/10).

Therefore the independent boundaries are measured, but v0.5 does **not** earn a simultaneous combined hardware envelope.

## Most important engineering lesson

The dominant correction was not more precision. It was representing the physical trainable object correctly.

When one compiled edge was incorrectly quantized as four independent Q entries, learning appeared erratic and nonmonotone in bit depth. Once one edge cell was quantized once and stamped as an exact rank-one contribution, the precision response became clean and monotone and 8-bit learning became strong.

The hardware contract should therefore say **one reciprocal edge cell / one programmable coefficient / one local credit accumulator**, not "four independently quantized matrix entries."
