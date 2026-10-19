# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 87.5% [69.0, 95.7] | 95.8% [79.8, 99.3] | 0.5 (B better) | +0.053 [+0.000, +0.159] |
| L3 | natural | claude-sonnet-5-5 | 24 | 91.7% [74.2, 97.7] | 95.8% [79.8, 99.3] | 1 (B better) | -0.007 [-0.045, +0.025] |

Flips in L3|forced|claude-sonnet-5-5: l3-ml-to-inference r0→pass, l3-ml-to-inference r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-ml-to-inference r1→pass, l3-ml-to-inference r2→fail, l3-response-unfold-report r1→pass

