# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 6 | 83.3% [43.6, 97.0] | 33.3% [9.7, 70.0] | 0.25 (A better) | -0.227 [-0.227, -0.227] |
| L3 | natural | claude-haiku-5-5 | 6 | 66.7% [30.0, 90.3] | 83.3% [43.6, 97.0] | 1 (B better) | +0.061 [+0.061, +0.061] |

Flips in L3|forced|claude-haiku-5-5: l3-ml-to-inference r1→fail, l3-ml-to-inference r4→fail, l3-ml-to-inference r5→fail

Flips in L3|natural|claude-haiku-5-5: l3-ml-to-inference r5→pass
