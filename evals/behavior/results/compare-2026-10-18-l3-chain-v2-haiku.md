# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 62.5% [42.7, 78.8] | 58.3% [38.8, 75.5] | 1 (A better) | -0.020 [-0.081, +0.034] |
| L3 | natural | claude-haiku-5-5 | 24 | 50.0% [31.4, 68.6] | 58.3% [38.8, 75.5] | 0.727 (B better) | -0.014 [-0.098, +0.067] |

Flips in L3|forced|claude-haiku-5-5: l3-fault-response-clean r0→fail, l3-fault-response-missing-orientation r0→fail, l3-theory-vs-published r0→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-clean r2→fail, l3-fault-response-double-counted-efficiency r1→fail, l3-fault-response-double-counted-efficiency r2→fail, l3-fault-response-missing-orientation r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-ml-to-inference r1→pass, l3-theory-vs-published r0→pass

