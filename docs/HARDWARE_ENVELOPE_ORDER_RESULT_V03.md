# TW-1A hardware requirements envelope — temporal-order result v0.3

Preregistration: `docs/HARDWARE_ENVELOPE_ORDER_PREREG_V03.md`

## Stage A independent precision results

The zero-preserving static-PGA emulator produced stable independent precision minima:

| path | stable minimum | preregistered one-step-margin design |
|---|---:|---:|
| Q / coupling coefficients | **8 bits** | **9 bits** |
| drive + returned-error DAC | **4 bits** | **5 bits** |
| sense ADC with static PGA | **5 bits** | **6 bits** |

The DAC result was especially flat: every tested DAC depth from 4 through 12 bits qualified when Q and ADC were ideal.

The ADC needed the PGA but then qualified at every tested depth from 5 through 12 bits. Q precision was the demanding path: 8, 9, 10 and 12 bits qualified; 7 and below did not satisfy the frozen predicate.

## Joint precision confirmation

The preregistered joint point `(Q,DAC,ADC) = (9,5,6)` was tested on fresh seeds 856–861.

**Result: FAIL.**

It passed several strong directional checks:

- all 6 exact learners improved (`DeltaC > 0`);
- placed-credit final contrast beat shuffled-credit final contrast in **6/6**;
- median exact contrast improvement: **+0.3635**;
- median placed-vs-shuffled improvement gap: **+0.3875**.

But only **4/6** seeds achieved the registered `DeltaC >= 0.10` requirement (needed 5/6).

The two misses were:

- seed 859: `DeltaC = +0.01993`, exact final `C=+0.01993`, shuffled final `C=0`;
- seed 860: `DeltaC = +0.00610`, but it began already at `C=+0.48940`; exact final `C=+0.49550` while shuffled final fell to `C=-0.03577`.

Therefore the independent minima are **not** promoted to a hardware specification. Per preregistration, all leakage/mirror/drift/noise sweeps were stopped and no combined buildability envelope was claimed.

## Next allowed step

Use only the already-seen 856–861 block to diagnose the precision interaction around `(9,5,6)`. Then freeze a new joint-precision qualification on untouched seeds before any physical-tolerance sweep resumes.
