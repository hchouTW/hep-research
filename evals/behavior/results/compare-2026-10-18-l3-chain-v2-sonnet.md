# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 54.2% [35.1, 72.1] | 58.3% [38.8, 75.5] | 1 (B better) | -0.002 [-0.056, +0.054] |
| L3 | natural | claude-sonnet-5-5 | 24 | 37.5% [21.2, 57.3] | 62.5% [42.7, 78.8] | 0.0703 (B better) | +0.075 [+0.011, +0.135] |

Flips in L3|forced|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r2→fail, l3-fault-response-unit-mismatch r2→fail, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-fault-response-clean r2→fail, l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

