# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 54.2% [35.1, 72.1] | 79.2% [59.5, 90.8] | 0.0312 (B better) | +0.126 [+0.038, +0.244] |
| L3 | natural | claude-sonnet-5-5 | 24 | 37.5% [21.2, 57.3] | 79.2% [59.5, 90.8] | 0.00195 (B better) | +0.184 [+0.087, +0.285] |

Flips in L3|forced|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-response-unfold-report r2→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-unit-mismatch r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-fault-response-unit-mismatch r2→pass, l3-ml-to-inference r1→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

