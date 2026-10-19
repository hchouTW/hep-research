# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 62.5% [42.7, 78.8] | 62.5% [42.7, 78.8] | 1 (no change) | +0.056 [-0.038, +0.162] |
| L3 | natural | claude-haiku-5-5 | 24 | 50.0% [31.4, 68.6] | 54.2% [35.1, 72.1] | 1 (B better) | -0.010 [-0.153, +0.138] |

Flips in L3|forced|claude-haiku-5-5: l3-fault-response-clean r0→fail, l3-fault-response-double-counted-efficiency r0→fail, l3-response-unfold-report r1→pass, l3-theory-vs-published r2→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-clean r1→fail, l3-fault-response-clean r2→fail, l3-fault-response-double-counted-efficiency r0→fail, l3-fault-response-double-counted-efficiency r2→fail, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r1→fail, l3-fault-response-missing-orientation r2→fail, l3-fault-response-unit-mismatch r1→pass, l3-response-unfold-report r0→pass, l3-response-unfold-report r1→pass, l3-response-unfold-report r2→pass, l3-theory-vs-published r0→pass

