# g2x: Codex-authored held-out suite with cross-family grading (frozen 2026-10-29, before the suite exists)

Spec v9 sections 15.2-15.5. This suite answers the two caveats left by g2h (`../../g2h-report.md` section 3): the
suite was at the ceiling, and the same model family wrote the problems, the gold and the grades. The g2h protocol
applies except where this file differs. This file, `codex-brief.md`, `seal.py`, `grader-instructions.md` and
`run_g2x.py` are committed before Codex is run; the commit order is the evidence.

## 1. Authorship and custody

**Author: Codex** (OpenAI Codex CLI 0.164.0, default model of the user's account, alias not pinned).
- The user runs it in their own terminal, in an empty directory holding only `codex-brief.md` as `BRIEF.md`.
- It runs with `--ephemeral`, so no session transcript holding the answers is kept on the host.
- Claude does not run, see or steer the authoring. Claude wrote only the brief, which sets format, counts and
  difficulty, names the exposed families to avoid, and contains no problem content.

**Seal** (run by the user): `seal.py seal`.
- It checks the layout and runs every Codex oracle, printing pass counts only.
- It copies the public instances to the run folder and writes salted commitments of every private file.
- **The user then encrypts the whole author folder with a passphrase that is never on the host, and deletes the
  plaintext.** Claude commits `commitments.json` before the first dispatch.

**Held-out status: met** for the gold, the oracles, the author notes and the calibration labels (`user-held`;
encrypted on the host, plaintext absent).

**Reveal**:
- Only after every planned trial has been ingested and the results committed, the user decrypts the folder.
- `seal.py verify` checks every commitment and reruns the oracles.
- A mismatch or a failing oracle makes the affected instances unscorable (spec 15.4 item 4).

**Residual limits:**
- Codex's gold is author self-assessment. The executable oracles carry it, not the statements alone.
- The brief, written by Claude, shapes the suite's form.
- The reviewers are still Claude. That is what is being measured.

## 2. Suite and trials

| Item | Value |
|---|---|
| Instances | 16, opaque `x........`: C01 8 (1-3 defects; ≥ 4 with several, ≥ 2 interacting), C02 4 (≥ 2 unusual but correct methods), C03 2, C04 2. Length, step count and difficulty as in `codex-brief.md` |
| Obligations | as in g2h: uncued `O-stat` criterion, `O-compute` unchanged |
| Trials | 3 per instance, 48 in all; contexts `g2x-<instance>-t<k>`; fresh Agent-tool subagents; the driver's packets sent verbatim |
| Budget | Claude: 48 trials + 3 grader dispatches (calibration, scoring forward, scoring reversed), at most 54. Codex: 1 authoring run + 2 grading runs (calibration, scoring) |

## 3. Cross-family grading (after the reveal)

**Graders**:
- **Claude forward**: a fresh subagent.
- **Claude reverse**: a fresh subagent, items in reversed order.
- **Codex**: `codex exec --ephemeral -s workspace-write` in a folder holding only the instructions and the items. Run
  by Claude after the reveal, since nothing is held out by then.

All three use `grader-instructions.md`.

**Items** (from `run_g2x.py items`, in a fixed seeded order):
- one `defect` item per (C01 trial, gold defect), against all findings of that trial;
- one `finding` item per C01 finding, against all gold defect statements.

**Calibration**: each grader grades the 10 Codex-written calibration items. Every grader must reproduce all 10
labels, or the C01 evidence is uncalibrated and the scientific gate fails.

**Combination**: a grade counts only if all three graders give the same grade and it is not `unsure`. Anything else
is **unadjudicated**, counted as not detected and reported separately.

## 4. Scoring (pre-registered; `run_g2x.py score`)

| Type | Rule |
|---|---|
| C01 | **A defect is detected in a trial** if some obligation is `violated` with a finding and its `defect` item is unanimously `accept`. **A trial succeeds** if every defect is detected |
| C02 | Any finding or `violated` is a false alarm. **Success** is both obligations supported with no findings |
| C03 | As in g2h, with the keywords from the gold |
| C04 | `plan_requirements_met` is false, with REQ-2 a planning gap |

**Engineering gate**: as in G2, on all 48 trials.

**Scientific gate**:
- C01:
  - at least 80% of the (trial, defect) pairs detected;
  - at least 6/8 instances with every defect detected at least once.
- C02: at most 2/12 false alarms.
- C03: at least 5/6.
- C04: 6/6.
- All three graders calibrated.

**Reported regardless of the gates**:
- the defect-level miss rate, by single versus multiple and interacting defects;
- findings outside the gold, recorded as unadjudicated (spec 15.4), and listed;
- the three denominators.

## 5. Outcome

- **The gate passes**: the claim extends to the Codex-authored, cross-graded suite, with the measured miss rate stated
  beside it.
- **The gate fails**: that is the measurement this suite was built to obtain. It is reported with every trial. The
  claim stays at the g2h wording, with this failure as a known limit.
- **Either way**, the schema 1.0.0 decision uses the record-vocabulary test of the g2h protocol, section 5.

No trial is dropped or re-run to improve a score.
