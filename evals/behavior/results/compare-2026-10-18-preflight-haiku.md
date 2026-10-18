# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L1 | forced | claude-haiku-5-5 | 66 | 62.1% [50.1, 72.9] | 90.9% [81.6, 95.8] | 2.1e-05 (B better) | +0.130 [+0.043, +0.223] |
| L1 | natural | claude-haiku-5-5 | 66 | 56.1% [44.1, 67.4] | 74.2% [62.6, 83.3] | 0.00754 (B better) | +0.078 [+0.024, +0.132] |
| L2 | forced | claude-haiku-5-5 | 12 | 75.0% [46.8, 91.1] | 75.0% [46.8, 91.1] | 1 (no change) | +0.000 [+0.000, +0.000] |
| L2 | natural | claude-haiku-5-5 | 15 | 40.0% [19.8, 64.3] | 46.7% [24.8, 69.9] | 1 (B better) | +0.009 [-0.087, +0.086] |
| L3 | forced | claude-haiku-5-5 | 3 | 0.0% [0.0, 56.1] | 0.0% [0.0, 56.1] | 1 (no change) | +0.071 [+0.071, +0.071] |
| L3 | natural | claude-haiku-5-5 | 3 | 0.0% [0.0, 56.1] | 0.0% [0.0, 56.1] | 1 (no change) | +0.000 [+0.000, +0.000] |

Flips in L1|forced|claude-haiku-5-5: rt-wp11-bound-bc-1 r0→pass, rt-wp11-crdb-1 r0→pass, rt-wp11-crdb-1 r1→pass, rt-wp11-crdb-1 r2→pass, rt-wp11-crdb-3 r0→pass, rt-wp11-crdb-3 r1→pass, rt-wp11-crdb-3 r2→pass, rt-wp11-interp-1 r0→pass, rt-wp11-interp-1 r1→pass, rt-wp11-interp-1 r2→pass, rt-wp11-interp-4 r0→pass, rt-wp11-interp-4 r1→pass, rt-wp11-interp-4 r2→pass, rt-wp11-prop-1 r0→pass, rt-wp11-prop-1 r1→pass, rt-wp11-prop-1 r2→pass, rt-wp11-ts-1 r2→pass, rt-wp11-xexp-1 r1→fail, rt-wp11-xexp-2 r0→pass, rt-wp11-xexp-2 r1→pass, rt-wp11-xexp-2 r2→pass

Flips in L1|natural|claude-haiku-5-5: rt-rc-ams-latest-1 r1→pass, rt-rc-ams-latest-2 r0→fail, rt-rc-ams-latest-2 r1→pass, rt-rc-ams-paper-1 r1→pass, rt-wp11-bound-bc-1 r0→fail, rt-wp11-crdb-2 r0→pass, rt-wp11-crdb-3 r0→pass, rt-wp11-crdb-3 r2→pass, rt-wp11-interp-1 r0→pass, rt-wp11-interp-3 r0→pass, rt-wp11-interp-3 r1→fail, rt-wp11-interp-4 r0→pass, rt-wp11-interp-4 r1→pass, rt-wp11-prop-1 r1→pass, rt-wp11-ts-1 r1→pass, rt-wp11-xexp-1 r1→pass, rt-wp11-xexp-2 r0→pass, rt-wp11-xexp-4 r2→pass

Flips in L2|natural|claude-haiku-5-5: l2-ctx-companion-missing r2→fail, l2-meas-ams-numbers r2→pass, l2-meas-ams-numbers-zh r2→pass

