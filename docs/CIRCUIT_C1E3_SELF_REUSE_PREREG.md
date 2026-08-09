# TW-1A C1e3 reusable two-slice self-bank reset study

C1e2 found the smallest useful self-path timing change: split the worst
`|self|=3` contribution into **two sequential packets**. With two separately
precharged `Cin/Cf=1.5` sample capacitors, A0=1e5 and 300 MHz GBW passed the
0.1% packet marker.

C1e3 is frozen before observing any result from a **single physical self sample
capacitor reused twice**.

## Reuse sequence

Use one self sample capacitor

```text
Cs/Cf = 1.5
```

and one continuous active-integrator amplifier trajectory.

For a total ideal 25.6 mV self contribution, each slice contributes 12.8 mV and
the sample capacitor is charged to

```text
Vsample = 25.6 mV / 3 = 8.533333... mV.
```

Clock sequence:

```text
initial sample already charged to Vsample
TRANSFER1   20 ns through Ron=1 ohm
RESET       reconnect Cs to ideal Vsample through Ron=1 ohm
TRANSFER2   20 ns through Ron=1 ohm
```

Transfer and reset switches are non-overlapping. The same capacitor is used for
both packets. The amplifier compensation node, feedback capacitor and output
state remain continuous throughout.

This is still a process-independent switch/one-pole-amplifier deck; the ideal
Vsample source represents the self-code sampling reference and does not yet
model its driver output impedance.

## Frozen circuit values

```text
A0                  1e5
GBW                 300 MHz
Cf                  1 nF normalization
Cs/Cf               1.5
transfer Ron         1 ohm
reset Ron            1 ohm
transfer aperture    20 ns each
initial output cases 0 V, +0.2 V
```

## Frozen reset apertures

```text
5 ns
10 ns
20 ns
```

No reset duration, switch resistance, GBW or slice count is added after results
are observed.

## Acceptance marker

After the second transfer, compared with the total ideal 25.6 mV packet:

```text
packet magnitude error                 <= 0.1%
0 V vs +0.2 V state-dependent mismatch <= 0.1%
```

Also report sample-cap voltage immediately before the second transfer and total
self-path elapsed time.

## Decision

Choose the shortest frozen reset aperture that passes. If none passes, the
single-bank reuse assumption is rejected at Ron=1 ohm / 300 MHz and the first
chip must either use two ping-pong half-range self banks, lower reset resistance,
or allocate a longer reset interval; such a change requires a new frozen gate.
