# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 3 | 66.7% [20.8, 93.9] | 0.0% [0.0, 56.1] | 0.5 (A better) | -0.242 [-0.242, -0.242] |
| L3 | natural | claude-sonnet-5-5 | 3 | 66.7% [20.8, 93.9] | 66.7% [20.8, 93.9] | 1 (no change) | +0.121 [+0.121, +0.121] |

Flips in L3|forced|claude-sonnet-5-5: l3-ml-to-inference r0→fail, l3-ml-to-inference r2→fail

Flips in L3|natural|claude-sonnet-5-5: l3-ml-to-inference r1→fail, l3-ml-to-inference r2→pass
