# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L1 | forced | claude-sonnet-5-5 | 66 | 98.5% [91.9, 99.7] | 100.0% [94.5, 100.0] | 1 (B better) | +0.006 [+0.000, +0.019] |
| L1 | natural | claude-sonnet-5-5 | 66 | 54.5% [42.6, 66.0] | 90.9% [81.6, 95.8] | 8.43e-06 (B better) | +0.217 [+0.101, +0.338] |
| L2 | forced | claude-sonnet-5-5 | 12 | 66.7% [39.1, 86.2] | 100.0% [75.8, 100.0] | 0.125 (B better) | +0.099 [+0.000, +0.225] |
| L2 | natural | claude-sonnet-5-5 | 15 | 33.3% [15.2, 58.3] | 60.0% [35.7, 80.2] | 0.125 (B better) | +0.105 [+0.000, +0.257] |
| L3 | forced | claude-sonnet-5-5 | 3 | 0.0% [0.0, 56.1] | 0.0% [0.0, 56.1] | 1 (no change) | +0.000 [+0.000, +0.000] |
| L3 | natural | claude-sonnet-5-5 | 3 | 0.0% [0.0, 56.1] | 0.0% [0.0, 56.1] | 1 (no change) | +0.143 [+0.143, +0.143] |

Flips in L1|forced|claude-sonnet-5-5: rt-rc-ams-latest-2 r1→pass

Flips in L1|natural|claude-sonnet-5-5: rt-rc-ams-exists-1 r0→pass, rt-rc-ams-exists-1 r1→pass, rt-rc-ams-latest-1 r0→pass, rt-rc-ams-latest-1 r1→pass, rt-rc-ams-latest-1 r2→pass, rt-rc-ams-latest-2 r0→pass, rt-rc-ams-latest-2 r1→pass, rt-rc-ams-latest-2 r2→pass, rt-rc-ams-paper-1 r0→pass, rt-rc-ams-paper-1 r1→pass, rt-rc-ams-paper-1 r2→pass, rt-wp11-bound-bc-2 r0→pass, rt-wp11-crdb-1 r1→pass, rt-wp11-crdb-1 r2→pass, rt-wp11-crdb-2 r0→pass, rt-wp11-crdb-2 r2→pass, rt-wp11-crdb-3 r0→pass, rt-wp11-crdb-3 r1→fail, rt-wp11-crdb-3 r2→pass, rt-wp11-interp-1 r0→pass, rt-wp11-interp-1 r1→pass, rt-wp11-interp-1 r2→pass, rt-wp11-interp-3 r0→pass, rt-wp11-interp-3 r2→fail, rt-wp11-interp-4 r0→fail, rt-wp11-prop-1 r0→pass, rt-wp11-prop-1 r1→pass, rt-wp11-prop-1 r2→pass, rt-wp11-xexp-2 r1→pass, rt-wp11-xexp-2 r2→pass

Flips in L2|forced|claude-sonnet-5-5: l2-th-benchmark-source r2→pass, l2-th-qed-conventions r0→pass, l2-th-qed-conventions r1→pass, l2-th-qed-conventions r2→pass

Flips in L2|natural|claude-sonnet-5-5: l2-meas-ams-numbers-zh r1→pass, l2-th-benchmark-source r0→pass, l2-th-benchmark-source r1→pass, l2-th-benchmark-source r2→pass

