# G2 narrow pilot: frozen EvaluationProtocol (T04; frozen 2026-10-29 before the first trial)

Spec v9 sections 15.2-15.5. Supersedes `protocol-draft.md` where they differ. The commit that adds this file precedes
every pilot dispatch; the commit order is the evidence.

## 1. Custody (U1, answered 2026-10-29: option b)

The user approved the deterministic oracles of `make_pilot_instances.py`; no secret gold. Claude generated the
instances with the random seed `14b0e3a9d3ff573d` (recorded, not secret) and runs every trial. Gold
(`expected/*.json`, `oracle.json`), the calibration labels and these grader instructions are committed by salted
SHA-256 in `commitments.json`; the 32-byte nonces are kept outside the repository and published only after every
planned trial has finished. **Held-out isolation: unmet** (reviewers share the filesystem; Claude holds the gold). The
result can claim at most "pilot-checked-scope, oracle-checked, not held out".

## 2. Suite

| Item | Value |
|---|---|
| Domain / method / format | statistics (estimator weights, binomial uncertainty, correlated propagation) with a computing obligation (recompute within 0.1%); text + JSON |
| Instances | 16 new instances (4 per type C01-C04) from the seed above; families not used in the T0S spike; opaque ids `p0162bce8` ... `pf95c79fc` |
| Trials | 3 per instance, 48 in all; each trial its own review context (`g2-<instance>-t<k>`), a fresh Agent-tool subagent, packet from `coordinator.packet_text` at this commit |
| Obligations | `O-stat` (required, decision_required, method `assumption-check`, evidence `reasoning`); `O-compute` (required, method `recompute`, evidence `recomputation`, tolerance 0.001 relative); both target `analysis.md` and `data.json`; materials declared authored by `pilot-generator` |
| Path | full R2: snapshot -> intent, manifest, plan -> packet -> dispatch -> assignment with the host invocation id -> drop file read by bytes (declared SHA-256 when reported) -> record re-derived by the store -> report -> export and third-party recompute |
| Budget | at most 60 subagent dispatches: 48 trials + 1 calibration grader + 2 scoring graders (one order-swapped); no retry; a failed or late dispatch is a recorded outcome |
| Dispatch order | all trials of a batch in one message; at most 16 per batch; no trial's packet holds another evaluation |

## 3. Grader (C01 reason match only)

A fresh-context subagent with `grader-instructions.md`. **Calibration first**: the 8 items of
`calibration-items.json` (2 per spec 15.4 category); it must reproduce all 8 committed labels; otherwise the C01
evidence part is "uncalibrated" and the scientific gate is not passed. Then **scoring**: one grader dispatch with every
C01 trial whose `O-stat` is `violated` with a finding, items in a fixed order, and a second dispatch with the order
reversed (bias probe, spec P15); a trial whose two grades differ is marked grader-instability and counts as
unadjudicated, not as success. `unsure` counts as unadjudicated.

## 4. Scoring (pre-registered; `run_pilot.py score`)

| Type | Trial success |
|---|---|
| C01 | `O-stat` violated with at least one finding, and the grader accepts the finding against the oracle's defect statement |
| C02 | both obligations `supported` and no finding on either |
| C03 | `O-stat` `undetermined` or `not-examined`, and its `missing_inputs` mention one of: sigma, uncertaint(y), measurement 3, third |
| C04 | `plan_requirements_met` false with REQ-2 listed as a planning gap (mechanical) |

A trial that is not started, has no submission, or has an invalid submission is a failure in every count.

**Engineering gate**: every trial completed; fidelity digest-bound or file-transfer; layer 1 recomputed byte for byte
from the export; head continuity verified; no quarantine.

**Scientific gate** (on all 48 planned trials): C01 >= 10 of 12 trials and >= 3 of 4 instances at least once; C02 false
alarms <= 2 of 12; C03 >= 10 of 12; C04 12 of 12. Reported with first-attempt, at-least-once and all-scheduled success
per instance, never a power of a single-run rate; the three denominators of spec 15.3.

## 5. Outcome handling

Both gates pass -> pilot-checked-scope for exactly this domain / method / format / host, with the custody limit above;
schema 1.0.0 may then be frozen as a separate, reviewed step. Either gate fails -> the claim stays experimental and the
failure is reported with all trials. No trial is ever dropped or re-run to improve a score.
