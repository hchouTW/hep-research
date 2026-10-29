# G3 evaluation: frozen EvaluationProtocol (frozen 2026-10-29, before the suite exists)

Spec v9 §15 and §18 (T08, G3). The suite is built to **measure a miss rate**: three earlier suites (141 trials) gave
0 content misses, so none was measured. The g2x protocol (`../pilot/g2x/frozen-protocol.md`) applies wherever this
file is silent. This file, `codex-brief.md`, `run_g3.py` and the parameterised `seal.py` are committed before Codex
runs; the commit order is the evidence.

## 1. Authorship and custody (as in g2x)

**Codex authors the suite** in the user's terminal:
- `codex exec --ephemeral -s workspace-write` in an empty folder holding only `BRIEF.md`;
- if scipy is unavailable, the oracles use the standard library only.

**The user seals it**: `seal.py seal --expect 20 --prefix g`. Then the user encrypts the author folder with a
passphrase that is never on the host and deletes the plaintext.

**Claude**:
- commits `commitments.json` before the first dispatch;
- commits every result before decryption.

**Reveal**: `seal.py verify`, then the Codex oracles are re-run.

**Held-out**: met for the gold, oracles, notes and calibration labels.

**Residual limits**:
- Codex's gold is author self-assessment, carried by its oracles.
- Claude wrote the brief.
- The reviewers are Claude; that is what is measured.

## 2. Suite and trials

| Item | Value |
|---|---|
| Instances | 20, ids `g` + 8 hex |
| C01 | 12 instances, 2–4 defects each: ≥ 6 interacting, ≥ 4 numerical or Monte Carlo, ≥ 3 needing particle-physics conventions |
| C02 | 5 instances, ≥ 3 unusual but correct |
| C03 | 2 instances |
| C04 | 1 instance |
| Material | 800–2,000 words, 5–10 steps; text and JSON only |
| Defect tags | interacting, numerical, convention (from the gold) |
| Obligations and packet | as in g2h/g2x, with the packet's separate-hash / `unavailable` wording (commit `1dfb15fa`) |
| Trials | 3 per instance, 60 in all, contexts `g3-<instance>-t<k>`, fresh Agent-tool subagents |
| Budget | Claude: 60 trials + 3 grader dispatches, at most 66. Codex: 1 authoring run + 2 grading runs |

## 3. Grading

The grading is the same as in g2x:
- **Graders**: Claude forward, Claude reversed, and Codex (`codex exec --ephemeral`, after the reveal).
- **Instructions**: `../pilot/g2x/grader-instructions.md`.
- **Items**: defect items and finding items, in the seeded order.
- **Calibration**: every grader must reproduce all 12 Codex-written calibration labels.
- **Combination**: a grade counts only when all three graders give it; anything else is unadjudicated.

## 4. Measurement (pre-registered; `run_g3.py score`)

| Output | Definition |
|---|---|
| Defect detection | The share of (trial, defect) pairs detected (g2x rule: an obligation `violated` with a finding, and the defect item unanimously `accept`), with a 95% Clopper-Pearson interval. It is reported overall, by tag (interacting, numerical, convention) and for untagged defects |
| C02 false alarm | Any finding or `violated` on a control, with its interval |
| C03 gap kept | As in g2h, with the keywords from the gold |
| C04 | `plan_requirements_met` false with REQ-2 |
| Findings outside the gold | Unadjudicated and listed |
| Three denominators | Task, known defect, predicted finding |

**Engineering gate**: as in G2, on all 60 trials.

## 5. Claim rule

- **evaluated-scope** is recorded for exactly the measured scope if the engineering gate passes and all three graders
  are calibrated. The scope is statistical analyses of up to 2,000 words with up to four planted defects, text and
  JSON, R2, Claude Code on macOS. Otherwise the claim stays at pilot-checked-scope, with the reason.
- **There is no pass threshold** on detection: the claim states the measured rates with their intervals.
- **Usage warnings** are attached to the claim if detection is below 0.8 or the false-alarm rate is above 0.2.
- No trial is dropped or re-run to improve a number.
