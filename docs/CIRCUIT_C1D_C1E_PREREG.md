# TW-1A C1d/C1e active-integrator finite-gain and bandwidth gates

These circuit gates are frozen before observing any new C1d/C1e ngspice result.
They extend the restored C1c ideal virtual-summing deck; they do not run learning.

## Why these gates exist

C1b rejected passive destination charge sharing because the increment depended
on the state already stored. C1c showed that an ideal virtual-summing charge
integrator restores state-independent packet addition.

The remaining first-order amplifier questions are:

1. how much open-loop DC gain is actually needed for a packet ratio;
2. how much unity-gain bandwidth is needed for the fixed 20 ns transfer aperture
   at the worst scheduled capacitive feedback factor.

The sweep explicitly includes the **self-path loading case**, because a direct
`|self|=3` packet gives the worst first-order feedback factor

```text
beta = Cf/(Cf+Cin) = 1/(1+3) = 0.25.
```

The edge path at the working 0.265 edge full scale has `beta=1/(1+0.265)`.

## C1d — finite DC gain

Use the same ideal-output virtual-sum topology as C1c but finite VCVS open-loop
gain. For each input-capacitance ratio, choose the sampled voltage so the ideal
output packet magnitude is 25.6 mV. Compare both an empty and +0.2 V precharged
state.

Frozen points:

```text
Cin/Cf = 0.265, 3.0
A0     = 1e3, 3e3, 1e4, 3e4, 1e5
```

Report packet magnitude error, empty/precharged packet mismatch, and virtual
summing-node excursion. The circuit-facing static pass marker is **<=0.1% packet
magnitude error and <=0.1% state-dependent packet mismatch**. This is a design
marker, not a learning qualification.

## C1e — finite bandwidth

Use a one-pole finite-gain amplifier made from an internal VCCS/R/C open-loop
node followed by an ideal unity output buffer. This keeps the specified A0 and
GBW independent of the external feedback-cap load while allowing the closed
loop to settle naturally.

Frozen values:

```text
A0              = 1e5
transfer aperture = 20 ns
Cin/Cf           = 0.265, 3.0
GBW              = 30, 100, 300, 1000 MHz
```

Again choose the sample voltage so the ideal final packet is 25.6 mV and test
both zero and +0.2 V precharged outputs.

Report packet settling error and state-dependent packet mismatch at the end of
the 20 ns aperture. The circuit-facing timing marker is **<=0.1% packet error
and <=0.1% state-dependent mismatch**.

No A0, GBW, capacitance ratio, aperture or acceptance point is added after the
results are observed.

## Scope

These are process-independent first-order amplifier gates. They do not include
slew rate, output swing compression, input common-mode range, transistor noise,
PVT, switch parasitics or OTA area/power. Those remain later C1 gates.
