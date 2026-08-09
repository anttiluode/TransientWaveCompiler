# TW-1A C1e2 self-packet slicing timing study

C1e is a real circuit failure for the monolithic `|self|=3` active-integrator
packet. With `A0=1e5`, a 20 ns transfer aperture and 1 ohm transfer switch, the
edge load (`Cin/Cf=0.265`) passes the 0.1% timing marker at 100 MHz GBW, but the
monolithic self load (`Cin/Cf=3`) still has 0.352% packet-magnitude error at
1 GHz.

This study is frozen before observing any sliced-self result.

## Architectural idea

Represent a requested self coefficient `s` as a sequence of equal charge
packets through a smaller reusable self capacitor bank. At the worst magnitude
`|s|=3`, an `N`-slice implementation uses instantaneous

```text
Cin/Cf = 3/N
```

and applies `N` packets. For a fixed desired total state increment `Delta`, each
packet contributes `Delta/N`, so the required sampled voltage is

```text
Vsample = (Delta/N)/(3/N) = Delta/3,
```

independent of `N`.

The timing deck uses `N` separately initialized sample capacitors to keep the
SPICE clock simple while preserving one continuous amplifier/output trajectory.
Only one is connected at a time. This is a timing-equivalent upper-bound model
for a design that may later **reuse one physical sliced self bank** after a
resample/reset phase; C1e2 does not yet prove the reset/reuse circuit or its
energy.

## Frozen circuit values

```text
feedback/state capacitor Cf   1 nF (normalization only)
total ideal self packet       25.6 mV
A0                            1e5
transfer switch Ron           1 ohm
one transfer aperture         20 ns
inter-slice gap               5 ns
initial-state cases           0 V, +0.2 V
```

## Frozen sweep

```text
slices N   1, 2, 4, 8
GBW        30, 100, 300, 1000 MHz
```

For every pair `(N,GBW)`, use `N` sample capacitors each of size
`(3/N)*Cf`, each precharged to `25.6mV/3`, and connect them sequentially for
20 ns each. The amplifier internal compensation node remains continuous through
all slices.

No slice count, GBW, switch resistance, aperture or gap is added after seeing
the result.

## Acceptance marker

At the end of the final slice, relative to the total ideal 25.6 mV packet:

```text
packet magnitude error               <= 0.1%
0 V vs +0.2 V state-dependent mismatch <= 0.1%
```

Report total elapsed self-transfer time as well as the first passing GBW for
each slice count.

## Decision

Prefer the **smallest slice count** that passes at a practical frozen GBW point.
A passing sliced result changes the self-path timing architecture and must later
be checked for sample-reset/reuse, switch kick, thermal noise, self-code mapping
and full wave-tick scheduling. It does not alter the already fresh-qualified
v0.8 edge/learning contract.
