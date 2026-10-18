# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 54.2% [35.1, 72.1] | 75.0% [55.1, 88.0] | 0.0625 (B better) | +0.132 [+0.028, +0.270] |
| L3 | natural | claude-sonnet-5-5 | 24 | 37.5% [21.2, 57.3] | 66.7% [46.7, 82.0] | 0.0391 (B better) | +0.145 [+0.040, +0.278] |

Flips in L3|forced|claude-sonnet-5-5: l3-fault-response-unit-mismatch r1→pass, l3-response-unfold-report r0→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r2→fail, l3-fault-response-unit-mismatch r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→pass, l3-response-unfold-report r1→pass, l3-theory-vs-published r1→pass

