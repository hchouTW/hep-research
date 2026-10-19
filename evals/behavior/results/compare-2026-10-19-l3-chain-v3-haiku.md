# Campaign comparison (A → B, paired)

| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |
|---|---|---|---|---|---|---|---|
| L3 | forced | claude-haiku-5-5 | 24 | 62.5% [42.7, 78.8] | 66.7% [46.7, 82.0] | 1 (B better) | +0.074 [-0.080, +0.244] |
| L3 | natural | claude-haiku-5-5 | 24 | 50.0% [31.4, 68.6] | 50.0% [31.4, 68.6] | 1 (no change) | -0.005 [-0.154, +0.145] |

Flips in L3|forced|claude-haiku-5-5: l3-fault-response-double-counted-efficiency r0→fail, l3-fault-response-double-counted-efficiency r1→fail, l3-fault-response-double-counted-efficiency r2→fail, l3-ml-to-inference r1→pass, l3-response-unfold-report r0→pass, l3-response-unfold-report r1→pass, l3-response-unfold-report r2→pass

Flips in L3|natural|claude-haiku-5-5: l3-fault-response-clean r0→pass, l3-fault-response-clean r1→fail, l3-fault-response-clean r2→fail, l3-fault-response-double-counted-efficiency r0→fail, l3-fault-response-double-counted-efficiency r1→fail, l3-fault-response-unit-mismatch r0→fail, l3-fault-response-unit-mismatch r2→fail, l3-ml-to-inference r0→pass, l3-ml-to-inference r1→pass, l3-ml-to-inference r2→pass, l3-response-unfold-report r0→pass, l3-response-unfold-report r2→pass

