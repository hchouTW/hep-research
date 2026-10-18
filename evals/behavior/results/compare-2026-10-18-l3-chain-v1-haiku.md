# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 62.5% [42.7, 78.8] | 62.5% [42.7, 78.8] | 1 (no change) | +0.029 [+0.008, +0.056] |
| L3 | natural | claude-haiku-5-5 | 24 | 50.0% [31.4, 68.6] | 62.5% [42.7, 78.8] | 0.375 (B better) | +0.035 [+0.001, +0.074] |

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r2→fail, l3-fault-response-unit-mismatch r1→pass, l3-ml-to-inference r0→pass

