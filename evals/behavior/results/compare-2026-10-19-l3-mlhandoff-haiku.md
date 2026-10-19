# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 3 | 0.0% [0.0, 56.1] | 100.0% [43.9, 100.0] | 0.25 (B better) | +0.515 [+0.515, +0.515] |
| L3 | natural | claude-haiku-5-5 | 3 | 100.0% [43.9, 100.0] | 66.7% [20.8, 93.9] | 1 (A better) | -0.151 [-0.151, -0.151] |

Flips in L3|forced|claude-haiku-5-5: l3-ml-to-inference r0→pass, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→pass

Flips in L3|natural|claude-haiku-5-5: l3-ml-to-inference r0→fail
