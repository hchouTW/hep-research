# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 29.2% [14.9, 49.2] | 62.5% [42.7, 78.8] | 0.00781 (B better) | +0.180 [+0.051, +0.321] |
| L3 | natural | claude-haiku-5-5 | 24 | 20.8% [9.2, 40.5] | 50.0% [31.4, 68.6] | 0.0156 (B better) | +0.193 [+0.087, +0.327] |

Flips in L3|forced|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-clean r2→pass, l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-double-counted-efficiency r1→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r1→pass, l3-fault-response-missing-orientation r2→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r2→pass, l3-fault-response-double-counted-efficiency r0→pass, l3-fault-response-double-counted-efficiency r1→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r1→pass, l3-fault-response-missing-orientation r2→pass, l3-fault-response-unit-mismatch r2→pass

