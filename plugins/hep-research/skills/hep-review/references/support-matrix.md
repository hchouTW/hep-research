# hep-review support matrix

What hep-review supports, and on what evidence. A row is never stronger than what was measured. Claims live in
`assets/claims.json`; they are written and checked through the claim lifecycle in
`scripts/hep_review_support/evaluation.py`, never by hand. A changed host profile, packet text, validator or reader
moves a live claim to needs-reassessment.

## Review capability

| Domain / method | Format | Material | Host | Tier | State | Evidence |
|---|---|---|---|---|---|---|
| Statistics: assumption check + recompute (0.1%) | text + JSON | single page, up to 3 planted defects, closed-form checks | Claude Code CLI, macOS | R2 | **needs-reassessment** (was pilot-checked-scope) | G2, g2h, g2x: 141 trials, 0 content misses, 0/39 control false alarms; the packet text and validator changed after these pilots |
| Statistics, multi-step | text + JSON | 800-2,000 words, two interacting planted defects (numerical and convention defects included) | Claude Code CLI, macOS | R2 | **evaluated-scope** | G3: defect detection 71/72 (95% CI 0.925-0.9997), false alarms 0/15 (CI 0-0.2181); more than two defects per instance not measured |
| Any other domain: measurement design, detector, theory, ML, code | any | any | any | any | **not-run** | none; route measurement-design review to hep-measurement and manuscript review to hep-authoring |

## Records and tiers

| Capability | State | Evidence |
|---|---|---|
| R0 consultation, R1 recorded review, R2 floor (non-author, fresh context, no other evaluations seen) | supported (engineering) | G1; `tests/contracts/test_hep_review_*.py`, `tests/skills/hep_review/` |
| R3 controlled evaluation | **unsupported on this host** | needs runtime restrictions the host does not enforce (`assets/host_profile.json`: `runtime_restrictions_enforced` false) |
| Commit log, head continuity, checkpoints, fork and migration, export / verify / import | supported (engineering) | G1 and the freeze review; persistence across sessions (H5) and checkpoint round trip (H6) are unknown until measured |
| Schema 1.0.0 (hep-review/1); 0.x records readable and labelled experimental | supported | freeze review; golden 0.1.0 layer-1 bytes |
| Submission fidelity | digest-bound or file-transfer supported; host-transcript **unsupported** here (reviewers can write transcripts) | host profile H2, H4 |

## Optional extensions (spec T05–T07)

| Extension | State | Why |
|---|---|---|
| T05 formats: LaTeX scanner, Python AST, source/PDF mapping | **unsupported** (not built) | outside the measured scope; would need its own readers, negative cases and evaluation |
| T06 controlled tools: argv, environment, permissions, timeouts, execution provenance | **unsupported** (not built) | the host cannot enforce the limits, so any claim would be unenforced |
| T07 evidence-based carry-over | **unsupported** (not built) | depends on T05/T06 |

## Hosts

| Host | State |
|---|---|
| Claude Code CLI, macOS (`claude-code-cli-macos`) | measured (T0S H1–H4); H5/H6 unknown |
| Any other host (Claude Code on Linux or Windows, Cowork, Codex as reviewer host) | **not-run**: re-measure the host profile before relying on it |
