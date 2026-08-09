# TW-1A v0.5 C0c capacitor-codebook learning gate — QUALIFIED

The preregistered gate on untouched bodies 1600–1609 **passes** the frozen
qualification predicate when the ideal uniformly spaced signed edge ladder is
replaced by the actual C0c capacitor charge-sharing codebook.

## Frozen predicate

```text
10/10 exact improvement >= +0.10
10/10 final exact contrast > final shuffled contrast
median exact improvement >= +0.30
median placement gap      >= +0.25
```

## Result

```text
qualified                 true
improvement >= +0.10      10/10
final exact wins           10/10
median improvement        +0.444847
median placement gap      +0.428426
minimum improvement       +0.262596
minimum placement gap     +0.251068
```

Per-body exact improvements:

```text
1600  +0.372894
1601  +0.456821
1602  +0.287895
1603  +0.262596
1604  +0.619867
1605  +0.305553
1606  +0.804120
1607  +0.432872
1608  +0.685612
1609  +0.771814
```

All ten final exact learners beat their same-credit shuffled controls.

## What was changed

Nothing in the already-qualified v0.5 mixed-signal background was relaxed.
Only the physical edge coefficient level set changed.

The previous emulator used an ideal uniform signed 8-bit edge ladder.  The C0c
bridge instead uses the physical seven-bit magnitude capacitor-array law

```text
f(m) = m*r / (1 + 2*m*r),

m = 0..127
r = Cunit/Csum = 0.001
```

normalized so physical magnitude code 127 still equals the routed edge full
scale `|a_e| = 0.25`.

The controller chooses the nearest physical measured level.  It does not invent
an analog linearization between physical codes.

## Consequence

The edge DAC **does not need uniformly spaced analog levels** for the temporal-
order learning primitive.  It needs:

```text
exact zero;
known signed physical levels;
monotonic magnitude ordering;
reciprocal equal/opposite endpoint action;
foreground calibration / codebook lookup;
phase-symmetric A/B reuse.
```

The physical C0c codebook has a genuine small deadband around zero because the
first nonzero capacitor branch is finite.  The formal pass shows that this
particular deadband and upper-code compression are compatible with the frozen
learning task and physical background.

## Claim boundary

This gate uses the **ideal nominal C0c level set**.  It does not yet include
capacitor mismatch, switch parasitic variation, binary carry DNL, or a distinct
measured codebook for every physical edge cell.

Bodies 1600–1609 are now spent.  The next physical bridge is C0d: introduce
fabricated capacitor mismatch, measure each edge cell's actual codebook, verify
monotonicity / missing-code behavior, and then feed those per-edge calibrated
codebooks back into the emulator.
