# G2 held-out follow-up ("g2h"): frozen EvaluationProtocol (frozen 2026-10-29, before the suite exists)

Spec v9 sections 15.2-15.5. This follow-up was run because the G2 suite was at the ceiling (`../../g2-report.md`, caveats
1-2). It asks whether the result holds on a harder, uncued suite whose gold Claude does not hold, before schema 1.0.0
is frozen. The G2 protocol (`../frozen-protocol.md`) applies except where this file differs. The commit that adds this
file comes before the suite is generated; the commit order is the evidence.

## 1. Custody (U1 option a for this suite)

- **The seed is the only secret, and only the user holds it.** The user generates it (at least 128 bits) and types it
  into the generator in their own terminal, without echo. It is never written to disk, typed into this session or
  shown to Claude before every planned trial has ended.
- The generator derives the gold (type, family, variant, defect statement and accepted keywords of every opaque
  instance) and the 32-byte nonces (HMAC-SHA256(seed, "nonce:" + name)) from the seed. `generate` writes only the
  instances and the salted commitments SHA-256(nonce ‖ gold); no gold file exists until `reveal`.
- The user reveals the seed only after every planned trial has been ingested. `reveal` re-derives the gold, checks
  every commitment, and only then writes the gold and the nonces. A mismatch makes the batch unscorable (spec 15.4
  item 4).
- **Held-out status: met for the per-instance gold** (`user-held-off-host`, basis declared).
- **Residual limits, recorded rather than hidden:**
  - The generator source and the calibration items/labels are on this host, outside the repository, in
    `~/.local/state/hep-research/hep-review/g2h-pilot/private/`. They name the defect families but not which instance
    carries which defect. They are bound below and published after the trials. Reviewers are told to read only their
    packet, so their compliance is advisory.
  - Claude wrote the generator, its oracles and the calibration labels (author self-assessment, spec 15.4).
  - Claude, as coordinator, can read the instances. Dispatch prompts are the driver's packets, sent verbatim.

| Bound item | SHA-256 |
|---|---|
| generator `make_g2h_instances.py` (plain digest; published after the trials) | `e3136b55cdcc1dab0124f56abc7270eb317169f02437851f019033feb5116d8e` |
| `calibration-items.json` (salted; nonce in the private folder) | `681141437febb49906da09d748bff6107b6b0d7d7d14b5a40b96590fae781ea2` |
| `calibration-labels.json` (salted) | `bf61367d707055dbe6ab335c284277d60cc3b4fb80ee6adae7b79ea1b5cc3ec4` |
| per-instance gold | `commitments.json`, written by `generate` and committed before the first dispatch |

## 2. Suite (what is harder than G2)

| Item | Value |
|---|---|
| Instances | 15 opaque ids `h........`. **C01**: 5, one known defect from each of five statistics families. **C02**: 5, one correct control per family; for three families the seed picks either the textbook form or a correct but differently written method. **C03**: 3, a missing input that the stated numbers depend on. **C04**: 2, correct material with REQ-2 left unplanned |
| Difficulty | The defects are not named in the criterion text. Several are one-symbol or one-count changes in a correct-looking method statement, and every family also appears as a correct control, so the topic alone does not reveal the answer |
| Criterion | `O-stat`: "The statistical treatment is appropriate for the stated model and inputs and the stated results follow from it; a missing input needed to decide is named rather than assumed." No list of defect classes. `O-compute` is unchanged from G2 |
| Trials | 3 per instance, 45 in all; context `g2h-<instance>-t<k>`; fresh Agent-tool subagents; packet from `coordinator.packet_text`; driver `run_g2h.py` (the G2 path with the criterion above) |
| Budget | at most 50 subagent dispatches: 45 trials + 1 calibration grader + 2 scoring graders (one with the order swapped); no retries |

## 3. Grader

Same instructions as G2 (`../grader-instructions.md`). Calibration on the 10 committed items (all four spec 15.4
categories) must reproduce all 10 labels, or the C01 evidence is "uncalibrated" and the scientific gate fails. The
grader runs only after the reveal, because it needs the defect statements. A trial whose forward and reversed grades
differ, or that is graded `unsure`, counts as unadjudicated, not as a success.

## 4. Scoring (pre-registered; `run_g2h.py score`)

| Type | Trial success |
|---|---|
| C01 | `O-stat` is violated with a finding, and the grader accepts that finding against the defect statement |
| C02 | both obligations are supported and there are no findings. Any finding or `violated` counts as a false alarm; false alarms are reported separately for the differently written method |
| C03 | `O-compute` is not supported, at least one obligation is undetermined or not examined, and a `missing_inputs` entry of either obligation contains one of that instance's committed keywords |
| C04 | `plan_requirements_met` is false, with REQ-2 a planning gap |

**Engineering gate**: as in G2, on all 45 trials.

**Scientific gate** (on all 45 planned trials):
- C01: at least 12/15 trials, and at least 4/5 instances successful at least once.
- C02: at most 3/15 false alarms.
- C03: at least 7/9.
- C04: 6/6.

The report also gives per-family results and the three denominators.

## 5. Outcome and the schema decision

- **Scientific gate passes**: the G2 claim (pilot-checked-scope) extends to this harder suite, now held out for the
  gold, with the residual limits in section 1.
- **Scientific gate fails**: the failure is reported with every trial and per-family detail. The claim stays at the G2
  wording, with this failure attached as a known limitation.
- **The schema 1.0.0 freeze** is recommended only if (1) the engineering gate passes and (2) no trial shows that the
  record vocabulary could not express what a reviewer meant: no invalid submission caused by the schema, and no
  answer forced into the wrong outcome. The scientific result decides the capability claim, not the freeze.

No trial is dropped or re-run to improve a score.
