# TW-1A C0e abstract state-noise sweep — result

Status: **diagnostic** on already-spent bodies 1700–1709.

The qualified v0.5 + C0d physical background was held fixed while only the old
emulator `state_noise_std` term was swept.

## Result

| state noise RMS / state FS | all-body clean | DeltaC>=0.10 | final wins | median DeltaC | min DeltaC |
|---:|:---:|---:|---:|---:|---:|
| 0 | yes | 10 | 10 | +0.5704 | +0.2612 |
| 1e-7 | yes | 10 | 10 | +0.5804 | +0.2531 |
| 3e-7 | yes | 10 | 10 | +0.5877 | +0.2485 |
| 1e-6 | yes | 10 | 10 | +0.5772 | +0.2536 |
| 3e-6 | **yes** | 10 | 10 | +0.5346 | +0.2278 |
| 1e-5 | no | 9 | 10 | +0.3969 | +0.0700 |
| 3e-5 | no | 4 | 9 | +0.0637 | -0.0109 |
| 1e-4 | no | 1 | 7 | +0.0092 | -0.0674 |
| 3e-4 | no | 0 | 6 | -0.0007 | -0.0455 |
| 1e-3 | no | 0 | 6 | +0.0084 | -0.0734 |
| 3e-3 | no | 0 | 6 | +0.0126 | -0.0996 |
| 1e-2 | no | 0 | 6 | +0.0113 | -0.0737 |

The diagnostic boundary lies between `3e-6` and `1e-5` state full scale per
independent node update.

## Why this is **not** yet a capacitor requirement

The legacy state-noise model adds an independent Gaussian voltage-like error to
every node state on every forward and reverse update.  That was useful as a
stress test, but it is not how the proposed switched-capacitor tile acquires
thermal noise.

A naive direct mapping

```text
noise_fraction = sqrt(kT/Cstate) / VFS_state
```

would produce implausibly large on-chip capacitances.  At 300 K, using the
largest all-body-clean `3e-6` point:

| state voltage FS | direct Cstate from kT/C |
|---:|---:|
| 0.2 V | 11.5 nF |
| 0.4 V | 2.88 nF |
| 0.6 V | 1.28 nF |

Using a one-third-inward `1e-6` target would demand approximately 103.5 nF,
25.9 nF and 11.5 nF respectively.

Those numbers should **not** be used as TW-1A capacitor sizes.  They demonstrate
that the independent full-node noise injection is too pessimistic / physically
misplaced for absolute sizing.

## Circuit-native replacement

The main state capacitor is intended to retain charge; it is not independently
reset and resampled from a noisy source every wave tick.  A sampled reciprocal
edge packet of selected capacitance `Cedge` instead contributes thermal charge
noise approximately

```text
sigma_sample,V = sqrt(kT/Cedge)
sigma_Q        = Cedge * sigma_sample,V = sqrt(kT*Cedge)
sigma_node,V   = sigma_Q / Cstate
               = sqrt(kT/Cstate) * sqrt(Cedge/Cstate).
```

Thus the state disturbance is attenuated by the transfer-capacitance ratio and
has the same **equal/opposite edge locality** as the signal packet.  It is also
present only for selected physical edge code, not as one arbitrary full-node
noise source.

The next C0e model will therefore:

1. set the legacy independent `state_noise_std` to zero;
2. derive each edge's selected physical capacitor from its measured C0d code;
3. draw edge-sampling thermal packet noise proportional to
   `sqrt(Cedge/Cstate)`;
4. inject that packet equal/opposite into the two endpoint state nodes;
5. sample A and B independently but preserve the reciprocal spatial structure;
6. sweep the base quantity `sqrt(kT/Cstate)/VFS_state`.

Only that circuit-native boundary should be used for a first kT/C state-cap
estimate.
