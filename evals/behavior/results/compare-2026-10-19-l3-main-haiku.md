# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 75.0% [55.1, 88.0] | 91.7% [74.2, 97.7] | 0.125 (B better) | +0.084 [+0.006, +0.213] |
| L3 | natural | claude-haiku-5-5 | 24 | 83.3% [64.1, 93.3] | 70.8% [50.8, 85.1] | 0.25 (A better) | -0.014 [-0.080, +0.054] |

Flips in L3|forced|claude-haiku-5-5: l3-ml-to-inference r0→pass, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→pass, l3-response-unfold-report r0→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-status-failed r0→fail, l3-ml-to-inference r0→fail, l3-response-unfold-report r1→fail
