# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 54.2% [35.1, 72.1] | 75.0% [55.1, 88.0] | 0.0625 (B better) | +0.068 [+0.018, +0.117] |
| L3 | natural | claude-sonnet-5-5 | 24 | 37.5% [21.2, 57.3] | 54.2% [35.1, 72.1] | 0.289 (B better) | +0.062 [+0.000, +0.119] |

Flips in L3|forced|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-unit-mismatch r1→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r1→fail, l3-fault-response-missing-orientation r2→fail, l3-fault-response-unit-mismatch r0→pass, l3-theory-vs-published r0→pass, l3-theory-vs-published r1→pass, l3-theory-vs-published r2→pass

