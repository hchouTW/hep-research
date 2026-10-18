# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-sonnet-5-5 | 24 | 20.8% [9.2, 40.5] | 54.2% [35.1, 72.1] | 0.00781 (B better) | +0.155 [+0.046, +0.257] |
| L3 | natural | claude-sonnet-5-5 | 24 | 12.5% [4.3, 31.0] | 37.5% [21.2, 57.3] | 0.0312 (B better) | +0.116 [+0.022, +0.220] |

Flips in L3|forced|claude-sonnet-5-5: l3-fault-response-clean r0→pass, l3-fault-response-double-counted-efficiency r1→pass, l3-fault-response-double-counted-efficiency r2→pass, l3-fault-response-missing-orientation r0→pass, l3-fault-response-missing-orientation r1→pass, l3-fault-response-missing-orientation r2→pass, l3-fault-response-unit-mismatch r0→pass, l3-fault-response-unit-mismatch r2→pass

Flips in L3|natural|claude-sonnet-5-5: l3-fault-response-clean r0→pass, l3-fault-response-clean r1→pass, l3-fault-response-clean r2→pass, l3-fault-response-double-counted-efficiency r1→pass, l3-fault-response-missing-orientation r1→pass, l3-fault-response-missing-orientation r2→pass

