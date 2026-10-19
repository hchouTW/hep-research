# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 95.8% [79.8, 99.3] | 87.5% [69.0, 95.7] | 0.625 (A better) | -0.029 [-0.074, +0.000] |
| L3 | natural | claude-sonnet-5-5 | 24 | 95.8% [79.8, 99.3] | 91.7% [74.2, 97.7] | 1 (A better) | -0.008 [-0.023, +0.000] |

Flips in L3|forced|claude-sonnet-5-5: l3-ml-to-inference r0→fail, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→fail, l3-theory-vs-published r1→fail

Flips in L3|natural|claude-sonnet-5-5: l3-ml-to-inference r0→fail, l3-ml-to-inference r1→fail, l3-ml-to-inference r2→pass
