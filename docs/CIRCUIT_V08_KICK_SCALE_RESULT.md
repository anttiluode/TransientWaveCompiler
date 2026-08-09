# TW-1A v0.8 switch-kick residual scale result

The frozen same-silicon residual sweep in
`CIRCUIT_V08_KICK_SCALE_PREREG.md` was run on the spent fresh-gate bodies
2100--2109 with the formal edge thermal point `b=1e-5` retained.

## Boundary

```text
scale   >=+0.10   wins   median DeltaC   min DeltaC   seed2107
1.00      9/10   10/10      +0.611408    +0.035623   +0.035623
0.75      9/10   10/10      +0.623651    +0.082481   +0.082481
0.50     10/10   10/10      +0.750632    +0.172751   +0.172751
0.25     10/10   10/10      +0.798389    +0.143423   +0.143423
0.10     10/10   10/10      +0.805718    +0.234781   +0.234781
0.00     10/10   10/10      +0.813974    +0.292370   +0.292370
```

The largest nonzero passing scale is therefore **0.50**. The 0.75 point fails
only the per-body +0.10 criterion, but under the frozen rule it is not accepted.

## Measured residual scale

At the failed formal point the ten tiles had mean residual RMS fractions

```text
common       5.968e-6 state FS
 differential 2.202e-6 state FS
```

with worst sampled tile RMS

```text
common       6.848e-6 state FS
 differential 2.648e-6 state FS.
```

At the first passing 0.50 boundary:

```text
mean common       2.984e-6
mean differential 1.101e-6
max common        3.424e-6
max differential  1.324e-6
```

At the chosen inward 0.25 design point:

```text
mean common       1.492e-6
mean differential 0.551e-6
max common        1.712e-6
max differential  0.662e-6
```

## Circuit-facing target

Do **not** design to the 0.50 cliff. The working v0.8 target is the tested 0.25
point, approximately

```text
common residual RMS       <= 1.6e-6 state FS
 differential residual RMS <= 0.6e-6 state FS
```

This is about a fourfold reduction in total post-cancellation residual from the
failed formal implementation. A follow-up same-silicon mechanism split will
separate the contribution from foreground cancellation measurement error from
the independent residual floor before a fresh qualification range is reserved.
