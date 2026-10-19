# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 6 | 33.3% [9.7, 70.0] | 100.0% [61.0, 100.0] | 0.125 (B better) | +0.212 [+0.212, +0.212] |
| L3 | natural | claude-sonnet-5-5 | 6 | 66.7% [30.0, 90.3] | 66.7% [30.0, 90.3] | 1 (no change) | +0.030 [+0.030, +0.030] |

Flips in L3|forced|claude-sonnet-5-5: l3-ml-to-inference r0→pass, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→pass, l3-ml-to-inference r5→pass

Flips in L3|natural|claude-sonnet-5-5: l3-ml-to-inference r1→pass, l3-ml-to-inference r2→fail
