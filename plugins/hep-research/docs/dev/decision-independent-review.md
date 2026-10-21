# Decision record: independent review mechanism, P1

Status: **draft, 2026-10-21; not decided** (the Decision section is the maintainer's). Written at the end of P1 of
`docs/dev/independent-review-spec.md` (13th edition, "the spec"). Labels: **Confirmed** (checked against the
repository or by a committed test), **Inferred** (a reading to sanity-check), **Unresolved** (needs a decision).

Terminology: "review packet" and "shadow slot" in this record and in the spec are the mechanism's terms. They are
unrelated to `docs/dev/v6.3/review-packet.md` (a human, maintainer-named review of the G-ENFORCE inputs) and
`docs/dev/v6.3/shadow-review.md` (a difference review between check suites).

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
| `docs/protected-data-architecture.md:526` (architectural invariant: no hooks, MCP servers, commands, background processes, or required subagents) | append: "The independent review is agent-driven but optional to the plugin: its driver prints the next action and a fixed dispatch message; the author agent dispatches through the host's own mechanism, and no plugin component dispatches or requires a subagent (docs/dev/decision-independent-review.md)." | **not edited**: an invariant needs special approval |

The two edited sentences are reversible text edits; if the maintainer rejects the position, revert them with the
mechanism.

## Evidence bases

The review record's bases follow `docs/maintenance.md:118-126` (Confirmed: the lines define locator at 120-121 and
third-party at 122-123, with exhaustive and person). The mechanism adds two non-independent categories:
`tool-output` (a plugin tool's output; external evidence, never an independent basis) and `internal` (other units of
the reviewed document; neither external nor independent). A locator counts as independent only for a paper, equation,
table or page (a specification page inside the plugin counts) that was read and hashed as a whole file, never the
reviewed document or another file the author wrote for it; the record states this with `source_kind`. The report
counts independent and tool-output evidence separately. (**Unresolved**: adopting these categories for review
verdicts is a maintainer decision.)

## Contracts version

P1 bumps contracts from 3.2.0 to **3.3.0**. The spec's sections 11 and 13 say "3.2.0"; that text predates the 0.21.0
release, which used 3.2.0 for simulated dataset-records (Confirmed: `contracts/__init__.py` at `c4f7954`). P4 then
takes 3.4.0. No `KNOWN_CAPABILITIES` entry is added (**Inferred**, recorded in the `# 3.3.0` block of
`contracts/__init__.py`): review records live under `<project>/reviews/`, not in an `artifacts_dir`, and no envelope
artifact declares them, so no reader can misread one as an artifact. The plugin release that carries it is the next
free number (0.22.0 at the time of writing; **Unresolved** until merge).

## Relation to v6.3 O04, O14 and decision-enforce

The mechanism does not settle O04 ("reviewers other than the author") or O14 ("which reviewer roles may accept reports
as evidence"), `docs/dev/v6.3/custodian-gate-requirement.md:42-43`. A closed agent review is **not** presented as
meeting the "a review record exists" criterion of `docs/dev/v6.3/decision-enforce.md:20`: the report's limitations,
the procedure reference and `review.py --help` say so. Whether it may ever count is a maintainer decision
(**Unresolved**). The mechanism writes no attestation; the attestation reviewer role is still under Q-06
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
16. Host shared directories for Claude Code (`review-hosts.json`) are inferred patterns (the session scratchpad and
    tool-result folders); the session start time is treated as not obtainable, so `isolation_not_yet_effective` is
    replaced by a warning (spec 7.3, last paragraph) unless an observation input supplies the time.
17. The hep-authoring description gained "independent review of a draft by agents that did not write it", so the
    English routing cases have a trigger in its "Use when" part.

## Open items (stop conditions and questions for the maintainer)

1. **Packaging scan (stop condition).** `tools/check_packaging.py` rule `restricted-site-fact` matches
   `[A-Za-z0-9-]+\.local\b` (local hostnames) and so flags the Claude Code file name `CLAUDE.local.md`, which the spec
   requires verbatim (A7, committed unchanged as `docs/dev/independent-review-spec.md`) and which
   `review-hosts.json` must list. Clean `main` passes the scan. Passing it needs either narrowing the rule (for
   example `\.local\b(?!\.md)`), an allow-list entry the spec does not call for, or altering the spec text; this task
   did none of them. Maintainer decision needed.
2. The four maintainer decisions of spec section 13 (subagent statements and the invariant, evidence categories,
   contracts 3.3.0 and its release number, P3 budget) and whether a closed agent review may count toward O04/O14.
3. Confirm the Claude Code shared-directory patterns and any concrete way to read the session start time
   (`review-hosts.json`); until then the fallback warning applies.
4. Location of the spec and of this record (`docs/dev/` rather than a versioned subfolder such as `docs/dev/v6.3/`).

## Decision

(Left for the maintainer.)
