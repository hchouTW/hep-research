# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 79.2% [59.5, 90.8] | 87.5% [69.0, 95.7] | 0.5 (B better) | +0.000 [-0.057, +0.058] |
| L3 | natural | claude-sonnet-5-5 | 24 | 79.2% [59.5, 90.8] | 91.7% [74.2, 97.7] | 0.375 (B better) | +0.024 [+0.000, +0.058] |

Flips in L3|forced|claude-sonnet-5-5: l3-response-unfold-report r0→pass, l3-response-unfold-report r1→pass

Flips in L3|natural|claude-sonnet-5-5: l3-ml-to-inference r0→pass, l3-ml-to-inference r1→fail, l3-ml-to-inference r2→pass, l3-response-unfold-report r0→pass, l3-response-unfold-report r2→pass

