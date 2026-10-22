# Decision record: independent review mechanism, P1

Status: **partly decided 2026-10-21** (see Decision: items 1, 2, 5 and 6 decided; the release and the P3 budget open). Written at the end of P1 of
`docs/dev/independent-review-spec.md` (13th edition, "the spec"). Labels: **Confirmed** (checked against the
repository or by a committed test), **Inferred** (a reading to sanity-check), **Unresolved** (needs a decision).

Terminology: "review packet" and "shadow slot" in this record and in the spec are the mechanism's terms. They are
unrelated to `docs/dev/cross-artifact-check/review-packet.md` (a human, maintainer-named review of the G-ENFORCE inputs) and
`docs/dev/cross-artifact-check/shadow-review.md` (a difference review between check suites).

## Question

May hep-research ship an agent-driven independent review of drafts (layers 1 and 2 only: contracts and protocol),
in which the author agent dispatches reviewer agents through the host's own mechanism with a fixed two-line message,
while the architecture keeps its statements that the plugin has no required subagents and no dispatch API? And on
which terms does a closed review count as evidence?

## What P1 delivered (Confirmed)

| Part | Where | Test |
|---|---|---|
| Seven schemas, Python rules, the shared state table, decide and check | `contracts/review.py`, `contracts/schemas/review_*.json` | `tests/contracts/test_review_contract.py`, `test_review_state.py`, `test_review_lcs.py` |
| Driver: every command of spec section 2, observe, receipt, repair, pre-close check, re-review, report, event-log lock | `skills/hep-authoring/scripts/review.py`, `review_lib/` | `tests/skills/hep_authoring/test_review_*.py` |
| Units, LCS mapping, scope, sampling; facts and design canaries with two-sided witnesses; packets and the generator | `review_lib/units.py`, `canary.py`, `packet.py` | `test_review_units.py`, `test_review_canaries.py`, `test_review_generator.py` |
| Lens table, Claude Code host notes | `skills/hep-authoring/assets/review-lenses.json`, `review-hosts.json` | used by every driver test |
| Procedure, ownership row, routing examples and cases | `skills/hep-authoring/references/independent-review.md`, `docs/routing-contract.md`, `tests/routing/make_cases.py` | `tests.routing.test_routing_static`, `tools/check_ownership.py` |

The end-to-end test drives one review with only `next` through four lenses and four shadows, a reject and
re-dispatch, a returned-empty, a timeout, an arbitration (uphold-finding), an adopted-unverified change, a
change_reverted, two change_confirmed, an escalate with report and human resolve, a re-review with changed, added and
removed units, and close; `contracts/review.py check` exits 0 on it, and two runs are byte-identical.

## Counterexamples and what they show

| Case | Without the mechanism | With P1 | Label |
|---|---|---|---|
| A reviewer agent copies the dispatch nonce wrongly or reads another slot's folder | nothing records it | `dispatch_mismatch`, `read_outside_packet` (`test_review_receipt.py`) | Confirmed |
| A lens reviewer ticks every unit `supported` without looking | indistinguishable from a careful review | `canary_missed`; a shadow repeating one refutation four times is `refutation_weak` | Confirmed |
| The author declines a high finding | no record | arbitration item; `uphold_not_honored` if declined again (`test_review_repair_check.py`) | Confirmed |
| The author edits, disposes `changed`, then reverts the edit | no record | pre-close check writes `change_reverted` (end-to-end test) | Confirmed |
| The author writes the sidecar itself | — | not detected; out of scope by design (spec section 10) | Confirmed (absence) |

## The subagent position and the three architecture statements

Position (spec section 9): the plugin still dispatches no agent and requires no subagent. `review.py next` prints the
next action; `dispatch SLOT` builds a packet and prints two lines; the author agent passes them to a new agent through
the host's mechanism (on Claude Code a non-fork subagent type; on a host without subagents, a new session per slot).
`next` sequences one review inside hep-authoring and routes no work between skills. No `agents/` or `hooks/` folder
was added. (**Confirmed**: `git diff --stat` of the P1 branch.)

Proposed clarifying sentences:

| Statement | Proposed sentence | P1 action |
|---|---|---|
| `docs/architecture.md:12` (no required subagents) | "The independent review (hep-authoring, docs/dev/decision-independent-review.md) keeps this: the plugin dispatches and requires no subagent; the author agent passes a fixed message to agents through the host's own mechanism." | added to the table row |
| `docs/routing-contract.md:7` (no coordinator skill, no dispatch API) | "The independent review driver (`skills/hep-authoring/scripts/review.py`) is not one: it sequences one review inside hep-authoring, dispatches no agent and routes no work between skills (docs/dev/decision-independent-review.md)." | added after the rule |
| `docs/protected-data-architecture.md:526` (architectural invariant: no hooks, MCP servers, commands, background processes, or required subagents) | append: "The independent review is agent-driven but optional to the plugin: its driver prints the next action and a fixed dispatch message; the author agent dispatches through the host's own mechanism, and no plugin component dispatches or requires a subagent (docs/dev/decision-independent-review.md)." | added as a separate line under the invariant, its wording unchanged (decided 2026-10-21) |

The two edited sentences are reversible text edits; if the maintainer rejects the position, revert them with the
mechanism.

## Evidence bases

The review record's bases follow `docs/maintenance.md:118-126` (Confirmed: the lines define locator at 120-121 and
third-party at 122-123, with exhaustive and person). The mechanism adds two non-independent categories:
`tool-output` (a plugin tool's output; external evidence, never an independent basis) and `internal` (other units of
the reviewed document; neither external nor independent). A locator counts as independent only for a paper, equation,
table or page (a specification page inside the plugin counts) that was read and hashed as a whole file, never the
reviewed document or another file the author wrote for it; the record states this with `source_kind`. The report
counts independent and tool-output evidence separately. (Adopted 2026-10-21, see Decision.)

## Contracts version

P1 bumps contracts from 3.2.0 to **3.3.0**. The spec's sections 11 and 13 say "3.2.0"; that text predates the 0.21.0
release, which used 3.2.0 for simulated dataset-records (Confirmed: `contracts/__init__.py` at `c4f7954`). P4 then
takes 3.4.0. No `KNOWN_CAPABILITIES` entry is added (**Inferred**, recorded in the `# 3.3.0` block of
`contracts/__init__.py`): review records live under `<project>/reviews/`, not in an `artifacts_dir`, and no envelope
artifact declares them, so no reader can misread one as an artifact. The plugin release that carries it is the next
free number (0.22.0 at the time of writing; **Unresolved** until merge).

## Relation to v6.3 O04, O14 and decision-enforce

The mechanism does not settle O04 ("reviewers other than the author") or O14 ("which reviewer roles may accept reports
as evidence"), `docs/dev/cross-artifact-check/custodian-gate-requirement.md:42-43`. A closed agent review is **not** presented as
meeting the "a review record exists" criterion of `docs/dev/cross-artifact-check/decision-enforce.md:20`: the report's limitations,
the procedure reference and `review.py --help` say so. Decided 2026-10-21: it does not count (see Decision). The mechanism writes no attestation; the attestation reviewer role is still under Q-06
(`contracts/schemas/attestation.json`).

## Cost

| Item | Estimate | Label |
|---|---|---|
| A review round | 8 agents (four lenses, four shadows), plus one per arbitration item; 1-12 minutes per slot in the ten hand-run rounds; worst case times attempts (2) and rounds (3) | Inferred from spec Appendix A |
| P3 evaluation | at least 20 documents with injected errors of known types; four arms (author self-check, one lens, four lenses, four lenses with different models); about 8 agents per round per arm | Unresolved (budget) |
| Driver run time | the end-to-end test (two rounds, 20 attempts) takes about 2 s; a 833-unit document (the spec) starts in about 0.3 s | Confirmed on the development machine |
| Maintenance | the record schema is the single source of the instruction file, the example and receipt; the spec-table test fails when spec section 5.3 and the schema drift | Confirmed |

## Owner

hep-authoring (ownership row "Independent review packets, review records and the review log"; claim terms
`independent review`, `review packet`). The decisions below are the maintainer's.

## Options

| Option | Do | Consequence |
|---|---|---|
| **Accept** | keep the two clarifying sentences; approve the invariant sentence at `docs/protected-data-architecture.md:526`; adopt the evidence categories; release with contracts 3.3.0; fund P3 | P2-P4 proceed as in spec section 11 |
| **Accept without the invariant edit** | keep the mechanism and the two sentences; leave the invariant as is | the invariant and the mechanism coexist with this record as the explanation |
| **Hold** | keep the branch unreleased until P3 data exist | no user can run a review; thresholds stay provisional either way |
| **Reject** | revert the P1 commits | no change to the plugin |

## Implementation readings (Inferred; each chosen between readings of the spec)

1. `start` writes `round_started` before the first `observed` (spec A1 lists observe before it): the log's first
   record must name the review and its configuration so that the head binds a review id.
2. The exhaustive test (spec 6.5) asserts that neither `report` nor `close` (which produces the final report) is printed
   while an arbitration item is needed or dispatched or a finding is open, reopened or declined-pending, for every
   state without a pending escalation. While an escalation waits for a human, row 2 prints the interim `report` for
   that human whatever else is open; everything else pauses (tested separately).
3. "Every finding changed in the previous round appears in the next round's carry_forward" holds unless all its units
   were removed; such a finding goes to dispose (`removed-pending`, A4.3). The test checks both branches.
4. "A round with a changed finding goes to rereview, not close" holds when the document differs from the round's
   source. When the edit was reverted (spec 6.7, note), decide prints `close` and the pre-close check writes
   `change_reverted`; the end-to-end test covers this.
5. Slot roles stay private: `round_started` lists slot ids and models only; `dispatched` records the canary count and
   the expected count (`canaries_per_slot` for a lens slot, 0 otherwise) so that `check` can report
   `canary_shortfall` and `no_control` without the private directory.
6. A shadow slot has no skim units; its focus units are the main lens's canary units of its latest dispatched attempt
   (or, when the lens is not dispatched yet, of its attempt 1, generated once and stored) plus two decoys.
7. One arbitration slot per arbitration item; item ids `A<round>.<n>`, finding ids `<round>/<slot>/<id>`,
   carry-forward refs `CF<n>`.
8. Each packet's `document.md` starts with a one-line comment, so the manifest never carries the hash of the delivered
   document (spec 5.2), also for shadow and arbiter packets whose text is otherwise the original.
9. The human decision vocabulary (spec 2 leaves `--decision D` open): `finding:` close or reopen; `item:` its
   conclusions; `slot:` accept-missing (then it counts as done for row 10); `verdict:` uphold or supersede;
   `round-limit` extend or accept.
10. Forbidden reads add `skills/hep-authoring/scripts/review_lib/` to the listed implementation files; "the author's
    traceability records" is the project's `artifacts_dir` (from `hep-research.project.json`, default
    `hep-research-artifacts/`).
11. Record fields the spec leaves implicit: `limitations` is a non-empty string; a locator may carry `source_kind`
    (needed to decide independence) and, for a URL, `copy` (the fetched copy in `work/`); third-party evidence states
    `expected_from`; review-config carries `config_version`.
12. `instructions_changed` compares one hash over the recorded instruction files and the loading and isolation
    settings, taken at dispatch and at receipt.
13. A `changed` disposal whose edited units miss the finding leaves the finding in its previous state, and observe
    raises `change_without_edit` until it is disposed again.
14. File:line references and facts canaries accept extension-less paths (`LICENSE:2-3`).
15. `start` writes a default configuration when none exists (`--models`, else `host-default`); `escalate` runs only
    when decide asks for it; `report` runs at any time; `receive` exits 1 when it writes `rejected`.
16. Host shared directories for Claude Code (`review-hosts.json`): the session scratchpad and tool-result folders,
    observed on the macOS CLI and confirmed (Decision 6). The session start time is the start of the process named by
    `CLAUDE_PID` (`ps -o lstart=`); without it, `isolation_not_yet_effective` is replaced by a warning (spec 7.3, last
    paragraph) unless an observation input supplies the time.
17. The instruction file names `contracts/review.py` by its absolute path so that a reviewer can run the self-check;
    the packet and instruction hashes therefore differ between plugin installs at different paths. Runs on one
    install are byte-for-byte reproducible (tested); across installs they are not.
18. Fixes from the P3 stage-1 pilot (Decision 4): a lens with no unit in scope gets no lens or shadow slot, and a
    shadow is allocated only when its lens has canaries or decoy candidates (spec A2 says each lens has one shadow
    slot; an empty slot reviews nothing and costs an agent); a shadow whose focus would still be empty relaxes the
    decoy evidence rule rather than run empty. Receipt treats any file holding at least half of the document's longer
    units as a copy or version of the delivered document (`read_outside_packet`), and `start` warns about such files
    in the plugin and the project. Design canaries add two types under the spec's design witness rule (the cited unit
    exists and contradicts the mutated statement): a repeated value made inconsistent, and a repeated back-quoted
    name misspelt once.
19. The hep-authoring description gained "independent review of a draft by agents that did not write it", so the
    English routing cases have a trigger in its "Use when" part.

## Open items (stop conditions and questions for the maintainer)

1. **Packaging scan (stop condition; resolved by the maintainer 2026-10-21, options A and B).**
   `tools/check_packaging.py` flagged host-documented names that spec A7 requires: rule `restricted-site-fact`
   (local hostnames, `[A-Za-z0-9-]+\.local\b`) matched the Claude Code per-directory memory file and the project-local
   settings file (the names `CLAUDE` and `settings` followed by `.local` and `.md` or `.json`) in the spec and in
   `review-hosts.json`; rule `private-path` matched the inferred shared-directory patterns in `review-hosts.json`.
   Chosen: (A) the hostname rule no longer matches a name followed by `.md` or `.json` (a hostname never is;
   `tests/tools/test_check_packaging_rules.py` keeps planted hostnames failing); (B) `review-hosts.json` writes the
   paths with the placeholders `<tmp>` (the resolved system temporary folder) and `<claude-config>`
   (`$CLAUDE_CONFIG_DIR`, else `~/.claude`), filled in by observe, so the private-path rule is unchanged. Not chosen:
   exempting the two files (too broad), moving the host notes out of the plugin or editing the spec (both contradict
   the spec).
2. Decided 2026-10-21: the architecture statements, the evidence categories, O04/O14 and the host facts (see
   Decision). Open: the release that carries contracts 3.3.0, after a live pilot review; the P3 budget.
3. Resolved 2026-10-21: the shared-directory patterns are confirmed and the session start is read from `CLAUDE_PID`
   (Decision 6).
4. Location of the spec and of this record (`docs/dev/` rather than a versioned subfolder such as `docs/dev/cross-artifact-check/`).

## Decision

Maintainer, 2026-10-21 (recommendations accepted; the numbers follow spec section 13):

1. **Architecture statements: accepted.** The plugin dispatches and requires no subagent. The two clarifying
   sentences stay in `docs/architecture.md` and `docs/routing-contract.md`, and the drafted sentence is added as a
   separate line under the invariant at `docs/protected-data-architecture.md:526`; the invariant's wording is
   unchanged.
2. **Evidence categories: adopted.** The bases of `docs/maintenance.md:118-126` (locator, third-party, exhaustive,
   person) apply to review verdicts as defined there; `tool-output` and `internal` are added as non-independent
   categories. This is the independence rule accepted on 2026-10-20 for sci-fix oracles, applied unchanged.
3. **Release: open.** Recommended: 0.22.0 (contracts 3.3.0; the ams02-research companion needs no change), after one
   live pilot review on a real document (about 8 to 10 agent runs, spec section 13 "Recommended next step"), each
   paid run approved first.
4. **P3 budget: staged; stage 1 run 2026-10-21** (5 documents, author self-check vs four lenses and shadows, Sonnet
   and Haiku, 54 agent runs, about 5 million subagent tokens; report outside the repository,
   `~/Workspace/hep-research-tasks/p3-pilot/results/REPORT.md`). Planted errors: self-check 9/12, independent review
   10/12 (intervals overlap); facts canaries 7/7 hit and exactly corrected. It found two driver bugs, fixed in this
   PR (one seed reused across reviews repeated nonces; plugin-relative paths were rejected), and P2 items: copies of
   the delivered document elsewhere on the host leak it (two reviewers diffed against the plugin original), design
   canaries never fired on documents without numbered references, empty-scope slots still cost an agent. Full P3
   only after those; the three are fixed in this PR (reading 18). Recommended: stage it. A pilot of 5 documents with two arms (author self-check, four lenses;
   about 50 agent runs) checks the injection script and the provisional thresholds; the full design (at least 20
   documents, four arms, about 19 agent runs per document, about 500 with re-dispatches) only after it.
5. **O04/O14: a closed agent review does not count** as a review record by a non-author reviewer and does not meet
   the "a review record exists" criterion of `docs/dev/cross-artifact-check/decision-enforce.md:20`. Reason: the threat model
   excludes deliberate fraud by the author agent (spec sections 0 and 10), who can write a reviewer's record; an
   enforcement gate needs records the author cannot produce. It is advisory input that a human reviewer may cite in
   their own record. Revisit only if P4 adds external custody or a process other than the author's.
6. **Host facts: confirmed.** On the Claude Code CLI on macOS (2026-10-21) session scratchpads are
   `<tmp>/claude-<uid>/<project-slug>/<session>/scratchpad` and tool results
   `<claude-config>/projects/<project-slug>/<session>/tool-results`; the host exports `CLAUDE_PID`, and the start of
   that process (`ps -o lstart= -p $CLAUDE_PID`) is the session start (it matched the session's start, 19:09:16 local).
   Both are undocumented host behaviour (`documented: false` in `review-hosts.json`); without `CLAUDE_PID` the
   fallback warning applies. `skills/hep-authoring/scripts/review_lib/observe.py` `session_start()` implements the
   method; tests use a faked `ps`.
