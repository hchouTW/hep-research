# C2 Agent evaluation — classification consistency: expected (fixed before dispatch, 2026-10-30)

Batch: `case-classify/requests.md` (8 requests), given unchanged to three independent fresh agents, each asked only to
classify (target tier and execution mode per deliverable, by the plugin's rules), not to execute. Reference,
derived from the tier and mode rules of `research-workflow-control.md` at `97c8a116`:

| # | Tier | Mode | Reason |
|---|---|---|---|
| 1 | T0 | M1 | single fact |
| 2 | T1 | M1 | feasibility from reasoning and sources, expected precision as an attributed expectation |
| 3 | T2-code | M1 | code fix with tests |
| 4 | T2-numeric | M1 | simulated, internal, delivered without a statement |
| 5 | T3-C | M1 | claim on data, threshold comparison, external (paper) |
| 6 | T3-E | M1 | an assessment of a trend on simulation |
| 7 | T2-numeric | M2 | numbers on simulation, no statement; expected to exceed a session |
| 8 | T2-numeric | M3 | remote submission, nobody present (M3 not available: weaker stated process) |

Criteria (computed from the three answers):
- C1 consistency: the three agents give the same (tier, mode) on at least 7 of 8 requests.
- C2 accuracy: the majority answer equals the reference on at least 7 of 8 requests (tier and mode both).
- Recorded: per-request disagreements, each agent's accuracy, whether any agent lowered a tier because of wording.
