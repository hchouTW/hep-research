# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 62.5% [42.7, 78.8] | 83.3% [64.1, 93.3] | 0.0625 (B better) | +0.061 [+0.021, +0.100] |
| L3 | natural | claude-haiku-5-5 | 24 | 54.2% [35.1, 72.1] | 79.2% [59.5, 90.8] | 0.146 (B better) | +0.124 [+0.004, +0.250] |

Flips in L3|forced|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-double-counted-efficiency r0→pass, l3-ml-to-inference r0→pass, l3-response-unfold-report r2→pass, l3-theory-vs-published r1→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r1→pass, l3-fault-response-clean r2→pass, l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r1→pass, l3-fault-response-missing-orientation r2→pass, l3-ml-to-inference r0→pass, l3-ml-to-inference r1→pass, l3-response-unfold-report r0→fail, l3-response-unfold-report r1→fail, l3-theory-vs-published r0→fail, l3-theory-vs-published r2→pass

