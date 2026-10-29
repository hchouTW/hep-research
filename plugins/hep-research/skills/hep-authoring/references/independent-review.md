# Independent review of a draft

Use when a draft (a paper section, a design note, a handover note; one Markdown document) should be reviewed by
agents that did not write it, with a record a script can check. The design is
`<plugin root>/docs/dev/independent-review-spec.md` (13th edition); this file is the procedure. P1 status: facts
and design lenses carry controls (canaries); sources and bypass slots run without controls and the report marks them
`no_control`; LaTeX, `--rerun` and hosts other than Claude Code are not implemented yet.

**What it guards against.** Negligence and laziness: reviewers seeing what they should not, box-ticking reviews,
findings that are never handled or adopted without declared verification, content changed during the review or after
close, contradicting records, a stalled process. It does not detect deliberate fraud by the author agent (spec
section 10), and it is not an attestation.

**What a closed review is not.** A closed agent review is not a review record by a reviewer other than the author in
the sense of the v6.3 open conditions O04 and O14 (`<plugin root>/docs/dev/cross-artifact-check/custodian-gate-requirement.md`), and
it does not meet the "a review record exists" criterion of `<plugin root>/docs/dev/cross-artifact-check/decision-enforce.md`
(maintainer decision 2026-10-21, `<plugin root>/docs/dev/decision-independent-review.md`): the author agent could
forge it. It is advisory input that a human reviewer may cite in their own record. Say so when you report it.

**Scope.** This mechanism reviews the document. A recorded review of the analysis, fit, derivation or code the document reports (obligations, tiers, a commit log) is hep-review's: hand it over rather than widening this review.

**Terminology.** "Review packet" and "shadow slot" here are this mechanism's terms. They are unrelated to
`<plugin root>/docs/dev/cross-artifact-check/review-packet.md` (a human review of the G-ENFORCE inputs) and
`<plugin root>/docs/dev/cross-artifact-check/shadow-review.md` (a difference review between check suites).

## Files and tools

| What | Where |
|---|---|
| Driver | `<plugin root>/skills/hep-authoring/scripts/review.py` (`--help` lists every command) |
| Contract and check | `<plugin root>/contracts/review.py check <review dir>`; `check --record-only RECORD --role reviewer\|arbiter\|expert\|filter` |
| Schemas | `<plugin root>/contracts/schemas/` `review_config`, `review_units`, `review_manifest`, `review_record`, `review_event`, `review_head`, `review_observation`, `review_filter_record` (the filtering pass); `review_record` with role `expert` is the expert slot's record |
| Lens table, host notes | `<plugin root>/skills/hep-authoring/assets/review-lenses.json`, `<plugin root>/skills/hep-authoring/assets/review-hosts.json` |
| Configuration | `<project>/reviews/review-config.json` (`start` writes one with defaults when missing; `models` is required), or the review's own `<project>/reviews/<review-id>/review-config.json` after `start --own-config` |
| Review directory | `<project>/reviews/<review-id>/`: the event log and head, unit tables, packets, records, the report file (report.md) |
| Private directory | config `private_dir`, else `$XDG_STATE_HOME/hep-research/reviews/` or `~/.local/state/hep-research/reviews/`: canaries, witnesses, seeds, the slot table. Outside the project and the host's shared directories |

**Copies of the document.** Review a document that exists nowhere else on the host. `start` warns when the plugin
or the project holds a copy or version of it (at least half of its longer units), and receipt rejects a record that
cites one (`read_outside_packet`), but an agent can still read one without citing it; git history and installed
plugin caches are not scanned. **Slots.** A lens with no unit in scope gets no slot, and its shadow only when it can
have focus units; `start` lists both under `no_slot` and the report says why.

Every command prints one JSON object with a `status`. Pass `--now` and `--observation FILE` only for reproducible test
runs. All review state is in files, so a review resumes after a host restart.

## Author agent

1. `python3 <plugin root>/skills/hep-authoring/scripts/review.py start DOC` from the project root (add
   `--supersede ID --reason TEXT` when the document already has an unfinished review).
2. Repeat: run `next`, do the action it prints, run `next` again, until it prints `stop`. When the host reports that
   an agent has finished, run `returned SLOT`.

**Optional settings** (contracts 3.4.0 and 3.6.0; spec sections 5.1, 6.9, 6.10 and A2), all off unless set, and set at
`start`. They are written to the shared `review-config.json`, and `start` refuses to change it while another
unfinished review uses it, unless you add **`--own-config`**: the review then gets its own configuration file,
`reviews/<review-id>/review-config.json` (the shared file, or the defaults, with the options and `--models` applied),
recorded in the review's log; the shared file is not changed, so concurrent reviews can use different settings. Do
not edit either file during a review (`config_changed`; `repair config_changed` names the file).

- `--lens-model LENS=MODEL` (repeatable; config `lens_models`) fixes the model of that lens's lens slot in every round,
  re-review rounds included. MODEL must be in `models`. The lens's shadow keeps the rotation and never shares the
  fixed model while `models` has another. **Recommended: the strongest model of `models` on the design lens**, for
  example `--models haiku,sonnet,opus --lens-model design=opus`: in the P3 tuning run Haiku missed the design-lens
  canaries (repeated values and terms) in 8 of 9 attempts, and 4 of 5 Haiku design-lens slots were exhausted; in the
  first live run with `--lens-model design=sonnet` all 5 design-lens slots were accepted at the first attempt.
- `--filter-model MODEL` (config `filter`) adds one filtering pass after round 1: one agent of MODEL judges every
  accepted round-1 finding (controls excepted) as `keep` (the page should change) or `drop` (wrong, a preference, a
  duplicate or a setup artefact), with a reason. **Recommended, with the strongest model.** In the P3 tuning run one
  Opus pass raised precision from 0.53 to 0.88 and kept every substantive issue (4 minor ones lost); in the first live
  run (five references, `--filter-model opus`) it raised precision from 0.59 to 0.84, kept 39 of 40 real issues and cost
  about 10% of the review's tokens. On five further references Opus raised precision from 0.65 to 0.92 and a Sonnet
  filter on the same findings only to 0.69, so use the strongest model. Its decisions are advice: nothing is deleted, and you still verify and dispose every
  finding.
- `--expert-model MODEL` (config `expert`, contracts 3.6.0) adds one **expert slot** to round 1: one agent of MODEL reads
  the whole document as a domain expert and reports only substantive physics, statistics or method errors (a general
  statement false in some regime, inconsistent reasoning, treatments called equivalent that are not, statements the
  plugin's own tools contradict), never style. It is dispatched with the other round-1 slots, carries no canaries,
  has at most two attempts and never escalates; its findings are filtered, disposed and reported like any other, and
  a changed one is rechecked by the design lens in round 2. Reason: in two evaluation runs the substantive errors no
  reviewer found were whole-page reasoning errors. **Recommended with the strongest model, together with the lens
  slots and `--filter-model`, for references whose physics matters:** in a prospective test on five references (one
  Opus expert per page, about 10% of the lens slots' tokens) all 9 of its findings were upheld, 4 of them substantive,
  3 of which no lens slot raised; the lens slots in turn found 2 substantive tool-enforcement gaps the expert did not.
  It does not replace the lens slots. `start` prints its slot
  as `expert_slot`. To run only the expert slot (for an evaluation), start with `--own-config --expert-model MODEL`,
  run `next`, then `dispatch` only that slot, `returned` and `receive` it; its findings are in the accepted record and
  the review stays unfinished (the other slots are never dispatched).

| `next` prints | Do |
|---|---|
| `dispatch` with slots | For each slot: `dispatch SLOT`, then pass the two lines it prints, and only those, to a new agent. On Claude Code name a non-fork subagent type. On a host without subagents, open a new session per slot |
| `await` | Nothing: wait for a host notification or the deadline |
| `receive` | `receive SLOT` for each slot listed (writes accepted or rejected) |
| `withdraw` | `withdraw SLOT --reason host-failure` or `--reason timeout`, as printed |
| `repair` | `repair CODE` shows the fix; fix it; `next` confirms |
| `arbitrate` | `arbitrate` (creates arbitration items and slots; `next` then dispatches them) |
| `filter` | `filter` (only with `--filter-model`, after round 1's records are received: creates the filter slot; `next` then dispatches it like any other slot, at most two attempts) |
| `dispose` | Verify each finding, then `dispose FINDING --as ...` (below). With a filtering pass, `next` also prints its advice per finding (`filter`) |
| `escalate` | `escalate --reason TEXT`; `next` then asks for `report`; hand the report file (report.md) to a human |
| `report` | `report` (writes the report file, report.md; it does not close the review) |
| `rereview` | `rereview` (starts the next round; every change gets a fresh review) |
| `close` | `close` (runs the pre-close check; writes `closed` only if it passes) |
| `stop` | Finished, or waiting for a human, or an error: read `reason` |

The dispatch message is always exactly:

```
Read and follow the instruction file below exactly.
REVIEW-DISPATCH nonce=<nonce> instructions=<packet>/instructions.md sha256=<instructions_sha256>
```

Never translate or reword the first line, add context, or tell a reviewer how to fill a field.

**Isolation (Claude Code).** Set `CLAUDE_CODE_FORK_SUBAGENT=0` in `env` of `settings.json` and restart the host, or
add `Agent(fork)` to `permissions.deny` (a warning: the docs do not say when the rule takes effect). With neither,
`next` prints the repair `isolation_precondition`. The host's start time is read from the process `CLAUDE_PID` names
(undocumented host behaviour); if the settings changed after it, `next` prints `isolation_not_yet_effective` (restart
the host). Without `CLAUDE_PID` the report says the setting's effect could not be confirmed.

**During the review.** Do not put packets, drafts, canaries or your own tool outputs in the host's shared directories
(the Claude Code scratchpad and tool-result folders): `shared_dir_contamination`. Do not edit the review's
configuration file (`config_changed`).

**Verify before you dispose.**

| Disposition | Use when | Needs |
|---|---|---|
| `changed`, `partially-changed` | You edited the document for this finding; the edit must touch one of its units | `--verified EVID` (same bases as reviewers, for example `locator:path:12-14`) or `--adopted-unverified` |
| `declined` | The finding is wrong; a high-severity decline goes to arbitration | a reason |
| `unresolved` | The evidence conflicts and you cannot decide | a reason; a human decides |

A reopened finding (arbitration upheld it, the next round reopened it, or the edit was reverted) can only be changed,
partially changed or unresolved. A finding on units removed in the next round can only be changed (with the deletion
as reason) or declined.

- Save a copy of every web page you fetch and record the URL form used. To conclude that something does not exist,
  try at least two URL forms (for example the `.md` version and the normal page) and ask for a verbatim quote.
- If a reviewer gave a verbatim quote you cannot reproduce, dispose `unresolved`, never `declined`.
- If two or more independent reviewers quote the same verbatim text, say so when you report.
- A filter `drop` is not a reason to decline by itself: verify the finding as usual; when you decline it, you may cite
  the filter's reason after you have checked it. A filter `keep` does not verify a finding either.
- Attach the report file (report.md) unchanged when you report back, with the line on O04/O14 above.

## Reviewer and arbiter agents

They follow their generated instruction file (instructions.md), which lists every field, its computation, the read rules, the quality
rules with this slot's thresholds, the full evidence-basis table and an example that passes `check --record-only`.
In short: run the R0 isolation self-check (stop if any prior conversation is visible); read only the packet, plugin
files and public sources; write only in `work/`; skim and judge deep units; give each claim one verdict with external
evidence where the lens needs it and real refutation attempts; quote the challenged text exactly in `value`; mark
every carry-forward item on re-review; write `review_record.json.tmp`, check it, then rename it.

The filter agent (with `--filter-model`) reads `findings.json`: the pooled round-1 findings under random ids, with no
reviewer, slot, lens or model; the raising slot's id, its reported identity and the model names are also removed
from each finding's free text (`[redacted]`; the counts are in the private directory and the report). It writes one decision per finding (`keep` or `drop`, a reason, and `duplicate_of` the
kept finding for a drop that repeats it) to `filter_record.json`, checked with `check --record-only --role filter`.
Receipt rejects a record with a finding missing or decided twice, an unknown id (`decisions_incomplete`), or a
`duplicate_of` that is not a kept finding (`duplicate_target`). After two failed attempts the filter is not applied
and the report says so; nothing escalates.

The expert agent (with `--expert-model`) reads the whole document.md of its packet (no skim or deep list, no controls) and writes
`review_record.json` with role `expert`: one claim, one `unsupported` or `partially-supported` verdict with evidence
and one finding per substantive error, nothing for style; finding nothing is a valid record. It is checked with
`check --record-only --role expert`. Receipt applies the reviewer rules except coverage, controls and re-review, with
any evidence basis allowed (external preferred), and rejects a finding no such verdict lists
(`finding_without_verdict`).

The arbiter judges only the items in `items.json` (both verdicts of a conflict in full, or a finding with the author's
reason for declining it) and writes one conclusion per item: `uphold-finding` or `accept-decline` for a decline,
`uphold-first` or `uphold-second` for a conflict, or `unresolved`.

## Humans

`resolve ITEM --by NAME --decision D --reason TEXT` settles an escalated item: `finding:<id>` (`close`, `reopen`),
`item:<id>` (the item's conclusions), `slot:<round>/<slot>` (`accept-missing`), `verdict:<id>` (`uphold`,
`supersede`), `round-limit` (`extend`, `accept`). The process then continues. This mechanism writes no attestation.

## Evidence bases

The bases follow `<plugin root>/docs/maintenance.md` (locator, third-party, exhaustive, person; lines 118-126).
`tool-output` (a plugin tool's output) is added by this mechanism and is never an independent basis; `internal`
evidence (other units of the document) is neither external nor independent. A locator is independent only for a
paper, equation, table or page (a specification page inside the plugin counts) that was read and hashed, and never
for the document under review or files the author wrote for it. The report counts independent and tool-output
evidence separately.

## Check and report

The report lists the configuration (with `lens_models`, `filter`, `expert` and the review's own configuration file when
set), the expert slot's outcome and findings, and, with a filtering pass, the identity strings it removed, the findings
it kept first and the findings it dropped in a separate section with its reasons.

`python3 <plugin root>/contracts/review.py check <review dir>` is read-only. Exit 0 when the review is closed and
consistent (warnings such as `adopted_unverified`, `no_control`, `canary_shortfall`, `weak_config`,
`no_model_diversity` are listed), 3 when it is not closed or a finding is open, 1 when the log is broken, the document
changed after close, a received packet, unit table or record changed, or an upheld finding was declined again.

Done when `next` prints `stop` with the review closed, `contracts/review.py check` exits 0 on the review directory,
and the report file is attached unchanged with the O04/O14 line.
