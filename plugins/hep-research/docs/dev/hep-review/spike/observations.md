# T0S spike observations and go/no-go decision

Exploration only (spec §15.1): nothing here is a capability or reliability claim, all 16 instances are
`exposed: true` and none may be used for G2 (case N25). Protocol and thresholds: `protocol.md`, committed at
2026-10-29T06:34:48+08:00 (commit 9044c6af), before the first dispatch (22:38:01Z = 06:38:01+08:00).

## 1. What ran

| Item | Value |
|---|---|
| Path | `spike.py packets` -> 16 packets (opaque assignment ids, material copied to neutral folders) -> 16 reviewers dispatched in one message with the Agent tool (general-purpose, fresh context) -> each wrote one JSON drop file and replied with its SHA-256 -> `spike.py ingest-many` read each drop by bytes (component-wise open, no symlinks, regular files, 256 KiB limit) and kept it as a raw blob -> `spike.py project` -> reports -> `spike.py score` against the expected files (copied into `expected/` only after every submission had landed) |
| Instances | 4 x C01 (known defect), 4 x C02 (correct control), 4 x C03 (missing input), 4 x C04 (unplanned requirement); text + JSON statistics material (BLUE combination, chi-square ndf, weighted mean, correlated propagation, Asimov significance) with a statistics obligation (decision_required) and a computing obligation (recompute within 0.1%) |
| Submissions | 16 of 16 landed, 16 of 16 parsed, 16 of 16 `digest-bound` (the declared SHA-256 matched the bytes read) |
| Wall time | dispatch to last drop: 2.5 minutes; protocol commit to this report: within the 96-minute box |
| Cost per case | host-reported subagent tokens 57,986-62,064 per reviewer (median about 58,700; most of it the subagent's fixed context), 6-8 tool calls, 38-68 s; money not observable (recorded as unavailable) |

Per-instance outcomes, finding counts, planning gaps, raw digests: `run1-summary.json`.

## 2. Scores against the pre-registered thresholds (protocol §3), counted strictly

| Type | Criterion | Result | Notes |
|---|---|---|---|
| C01 | defect located with relevant evidence | **4 / 4** | Checked by hand against `expected/`: x01a names the zero off-diagonal and gives 0.042 and sigma = 0.2815; x01b ndf = 9 (p 0.898); x01c 1/sqrt(sum 1/sigma^2) = 0.1469; x01d the -2 rho term, sigma_R = 0.05625. All `violated` with findings naming the element |
| C02 | false alarms | **1 / 4** (x02c) | The "false alarm" is correct: my instance's stated uncertainty 0.0055 is 0.74% from the true 0.005541, outside the 0.1% tolerance the obligation sets (I rounded to 4 decimals). Construction error of the instance, counted against the reviewer anyway |
| C03 | gap kept (undetermined/not-examined with the missing input named) | **3 / 4** | x03a gave `violated` while naming the missing correlation. The reviewer is right: my stated 172.71 +- 0.46 is unreachable for any rho in [0, 1] (recomputed: 172.607-172.653, sigma 0.471-0.607), so a defect exists whatever the missing value. Construction error, counted as a failure to keep the gap per the letter of the protocol |
| C04 | projection gives met = false with the unplanned requirement as a planning gap | **4 / 4** | Mechanical. Reviewers also named the unplanned REQ-2 in `suggested_obligations` in 4 of 4 (recorded, not scored) |
| Submission | landed, parses, names its assignment | **16 / 16** | |

Not scored but observed: x04b's reviewer marked the "correct" linear fit violated for chi-square 26.48 at ndf 8
(p = 8.7e-4), which I confirmed: my generator's random draw made a bad fit. x04c's stated uncertainty is 1.5% off by
rounding; that reviewer noticed it and still wrote `supported` ("rounding"), while x02c's reviewer wrote `violated`
for the same kind of discrepancy: **inconsistent handling of a tolerance across reviewers**, a real failure mode.

## 3. Decision

**go** (protocol §3: C01 >= 3/4 with evidence: 4/4; C02 false alarms <= 1/4: 1/4; C03 >= 3/4: 3/4; C04 4/4;
submissions >= 15/16: 16/16). The decision steers investment only; it is not a capability claim (spec §18.2).

Caveat that the decision does not hide: three of my sixteen instances (x02c, x03a, x04b) were wrong as constructed
and the reviewers caught all three. Author-written gold is author self-assessment (spec §15.4); the G2 pilot needs
instances whose expected results are checked by a deterministic oracle before any reviewer sees them (T03 step 7).

## 4. Fields actually needed (input to schema 0.x)

- Per answer: `obligation_id`, `outcome`, `reasoning`, `missing_inputs` (named, structured: reviewers used it for
  C03 and also to flag unsourced inputs on correct work), `findings` with `element` and `evidence`, plus
  `suggested_obligations` at record level (used in 4/4 C04 and in 3 other cases). Keep all of these.
- A finding's `severity` (major/minor) was used and is useful for presentation only; it must not feed flags.
- The tolerance needs a machine-readable form with a rounding rule (decimal string, relative/absolute, and how stated
  precision is treated), otherwise reviewers disagree (x02c vs x04c). Spec §10.2 decimal strings plus an explicit
  `comparison` rule per tolerance.
- `tools_used` is free text today; the closure needs `tools: [...]` as structured executor/tool ids (spec §8.3), and
  an attempt object (method, observation completed/failed/not-run, executor, tools, environment refs) separate from the
  answer. Reviewers ran python3/numpy/scipy in 16/16 cases, so attempts are almost never `tools: []`.
- `started_at`/`ended_at` self-reported: keep as data, never as evidence (one reviewer mistyped).
- Submissions are small (1-6 KB); a 256 KiB drop limit is ample.

## 5. Reviewer failure modes seen

1. Tolerance literalism varies between reviewers (x02c violated vs x04c supported for the same rounding issue).
2. `violated` on a C03-type instance when the stated numbers are inconsistent for every admissible value of the
   missing input: arguably correct, but it shows the C03 type needs instances whose stated numbers are reachable.
3. A reviewer mistyped its own timestamp into the submission.
4. Reviewers widen scope on correct work (unsourced correlation values, units): they used `missing_inputs` and
   `suggested_obligations` for this rather than findings, as instructed, so no false `violated` resulted.

## 6. Host measurements

H1 readable, H2 writable, H3 parallel, H4 file transfer yes + hash yes, H5 and H6 pending-next-session: see
`../host-profile.md`.

## 7. Recommended schema 0.x changes (relative to spec §6)

1. Make `missing_inputs` a first-class structured list on answers (`{name, needed_for, basis}`) so C03 handling is
   mechanical: an answer with outcome `supported` or `violated` and a non-empty `missing_inputs` on the same criterion
   is allowed (x03a), but the projection lists the gap.
2. Tolerances as `{quantity, value: decimal-string, kind: relative|absolute, precision_rule}`; the computing domain
   card states that a value quoted to fewer digits than the tolerance needs is a finding.
3. `suggested_obligations` as a record-level list; the coordinator, not the reviewer, turns them into plan revisions.
4. Attempts separate from answers, with structured `tools` (spec §8.3 item 4).
5. Pilot instances validated by a deterministic oracle script before dispatch.
