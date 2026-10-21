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
the sense of the v6.3 open conditions O04 and O14 (`<plugin root>/docs/dev/v6.3/custodian-gate-requirement.md`), and
it does not meet the "a review record exists" criterion of `<plugin root>/docs/dev/v6.3/decision-enforce.md`. Whether
it can is a maintainer decision (`<plugin root>/docs/dev/decision-independent-review.md`). Say so when you report it.

**Terminology.** "Review packet" and "shadow slot" here are this mechanism's terms. They are unrelated to
`<plugin root>/docs/dev/v6.3/review-packet.md` (a human review of the G-ENFORCE inputs) and
`<plugin root>/docs/dev/v6.3/shadow-review.md` (a difference review between check suites).

## Files and tools

| What | Where |
|---|---|
| Driver | `<plugin root>/skills/hep-authoring/scripts/review.py` (`--help` lists every command) |
| Contract and check | `<plugin root>/contracts/review.py check <review dir>`; `check --record-only RECORD --role reviewer\|arbiter` |
| Schemas | `<plugin root>/contracts/schemas/` `review_config`, `review_units`, `review_manifest`, `review_record`, `review_event`, `review_head`, `review_observation` |
| Lens table, host notes | `<plugin root>/skills/hep-authoring/assets/review-lenses.json`, `<plugin root>/skills/hep-authoring/assets/review-hosts.json` |
| Configuration | `<project>/reviews/review-config.json` (`start` writes one with defaults when missing; `models` is required) |
| Review directory | `<project>/reviews/<review-id>/`: the event log and head, unit tables, packets, records, `report.md` |
| Private directory | config `private_dir`, else `$XDG_STATE_HOME/hep-research/reviews/` or `~/.local/state/hep-research/reviews/`: canaries, witnesses, seeds, the slot table. Outside the project and the host's shared directories |

Every command prints one JSON object with a `status`. Pass `--now` and `--observation FILE` only for reproducible test
runs. All review state is in files, so a review resumes after a host restart.

## Author agent

1. `python3 <plugin root>/skills/hep-authoring/scripts/review.py start DOC` from the project root (add
   `--supersede ID --reason TEXT` when the document already has an unfinished review).
2. Repeat: run `next`, do the action it prints, run `next` again, until it prints `stop`. When the host reports that
   an agent has finished, run `returned SLOT`.

| `next` prints | Do |
|---|---|
| `dispatch` with slots | For each slot: `dispatch SLOT`, then pass the two lines it prints, and only those, to a new agent. On Claude Code name a non-fork subagent type. On a host without subagents, open a new session per slot |
| `await` | Nothing: wait for a host notification or the deadline |
| `receive` | `receive SLOT` for each slot listed (writes accepted or rejected) |
| `withdraw` | `withdraw SLOT --reason host-failure` or `--reason timeout`, as printed |
| `repair` | `repair CODE` shows the fix; fix it; `next` confirms |
| `arbitrate` | `arbitrate` (creates arbitration items and slots; `next` then dispatches them) |
| `dispose` | Verify each finding, then `dispose FINDING --as ...` (below) |
| `escalate` | `escalate --reason TEXT`; `next` then asks for `report`; hand `report.md` to a human |
| `report` | `report` (writes `report.md`; it does not close the review) |
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
`next` prints the repair `isolation_precondition`. The session start time cannot be read, so the report says the
setting's effect could not be confirmed.

**During the review.** Do not put packets, drafts, canaries or your own tool outputs in the host's shared directories
(the Claude Code scratchpad and tool-result folders): `shared_dir_contamination`. Do not edit the configuration
(`config_changed`).

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
- Attach `report.md` unchanged when you report back, with the line on O04/O14 above.

## Reviewer and arbiter agents

They follow their generated `instructions.md`, which lists every field, its computation, the read rules, the quality
rules with this slot's thresholds, the full evidence-basis table and an example that passes `check --record-only`.
In short: run the R0 isolation self-check (stop if any prior conversation is visible); read only the packet, plugin
files and public sources; write only in `work/`; skim and judge deep units; give each claim one verdict with external
evidence where the lens needs it and real refutation attempts; quote the challenged text exactly in `value`; mark
every carry-forward item on re-review; write `review_record.json.tmp`, check it, then rename it.

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

`python3 <plugin root>/contracts/review.py check <review dir>` is read-only. Exit 0 when the review is closed and
consistent (warnings such as `adopted_unverified`, `no_control`, `canary_shortfall`, `weak_config`,
`no_model_diversity` are listed), 3 when it is not closed or a finding is open, 1 when the log is broken, the document
changed after close, a received packet, unit table or record changed, or an upheld finding was declined again.
