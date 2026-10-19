# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 83.3% [64.1, 93.3] | 75.0% [55.1, 88.0] | 0.625 (A better) | -0.049 [-0.117, -0.006] |
| L3 | natural | claude-haiku-5-5 | 24 | 79.2% [59.5, 90.8] | 83.3% [64.1, 93.3] | 1 (B better) | -0.031 [-0.116, +0.023] |

Flips in L3|forced|claude-haiku-5-5: l3-ml-to-inference r0→fail, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→fail, l3-theory-vs-published r2→fail

Flips in L3|natural|claude-haiku-5-5: l3-ml-to-inference r2→pass, l3-response-unfold-report r1→pass, l3-theory-vs-published r2→fail

