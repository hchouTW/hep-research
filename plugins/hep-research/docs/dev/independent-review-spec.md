# Independent Review Mechanism — 13th Edition (Final)

Agent-driven review, using layers 1 and 2 only, with stronger automation.

Baseline: hep-research 0.21.0, contracts 3.2.0 (rechecked 2026-10-21; the design rounds ran on 0.20.0 / contracts 3.1.0, and every repository fact cited here is unchanged in 0.21.0). In the git repository the plugin lives in `plugins/hep-research/`; all paths are relative to that folder. This document stands on its own. Every rule is fully defined here, and nothing depends on an earlier edition. Any mention of an earlier edition names it explicitly, for example "12th edition U0294".

> Translation note: this is an English translation of `proposal-final.md` (Chinese). Where the spec matches literal Chinese tokens, such as the normative words in §4.3 and the attribution phrases in §4.4, the Chinese tokens are kept, with English glosses, because they are part of the matching rules.

## Purpose of the final edition

This is the final design after ten real review rounds. The last round, on the 12th edition, gave these results:

- 7 of 8 slots passed receipt.
- All 8 canaries were hit, and all 8 were corrected exactly.
- The script verdicts matched the author's manual re-check exactly.

The final edition fixes every finding that round confirmed (§12). It also adds §13, "Final status", and an appendix with the review history.

Main changes from the 12th edition:

1. **escalate is no longer terminal.** A new `human_resolved` event lets the process continue after a human resolves the open items, and the review can then close normally.
2. **Only the decision procedure can close a review.** `report` only produces the report. Closing is done by the `close` action from row 14, which runs the pre-close check before it writes `closed`.
3. **decide reads only the event log.** Whether a sidecar exists, and its hash, are recorded by observe in an `observed` event.
4. **The refutation duplicate ratio also works on shadow slots.** Its threshold is now the smaller of the configured value and the number of deep units, with a minimum of 3.
5. **The `sources` scope covers only real citations.** A unit must carry a `file:line`, a URL, or an attribution phrase plus a named document. A term that is only in quotation marks does not count.
6. **Conflicts are judged per verdict**, and the LCS tie-break rule is now complete.
7. **P1 implements both facts and design canaries**, which shrinks the part of the review that has no quality control.
8. **Field definitions for all auxiliary files**: `scope.json`, `items.json`, `canary.json`, `slots.json` and the unit table.

## 0. Threat model

**It guards against negligence and laziness, not deliberate fraud.**

- The author agent is assumed to follow the protocol and not to forge records. Reviewer agents may be lazy, but they do not lie.
- Under that assumption, the mechanism catches:
  - reviewers seeing what they should not see;
  - reviews that are not thorough enough, or are only box-ticking;
  - review results that are never handled, or that the author adopts without declaring verification;
  - content changed during the review or after close;
  - records that contradict each other, or a stalled process.
- §10 lists the forms of deliberate fraud, which this mechanism cannot detect.

## 1. Design principles

1. Review state does not live in the author's records.
2. A review is valid only for one packet. On re-review, a new agent for the same lens must explicitly confirm or reopen every earlier verdict. The script does not decide which old conclusions still hold.
3. Blind mode needs no main record: a single document saved as a file can be reviewed.
4. Every guarantee states its preconditions. Every field the reviewer fills in that the script cannot verify is marked "self-reported".
5. Agents perform reviews by default. Dispatch is fixed at release time, and the author cannot hand-pick reviewers afterwards.
6. Anything a script can decide is not left to an agent's judgment.
7. Contracts and process are separate. The new `contracts/review.py` holds only schemas and pure checks. The process driver lives in hep-authoring's scripts.
8. The plugin dispatches no agents and requires no subagent. The author agent dispatches agents through the host's own mechanism.
9. Quantity is not a substitute for quality: quality thresholds require only what a script can verify.
10. Instructions and format come from one source. The instructions a reviewer reads, the output example and the receipt checks are all generated from the same schema and configuration; only the scope description is hand-written. A test also confirms that the field table in §5 of this document matches the schema.
11. External state enters decisions only through observation events (`observed`). This includes files in the review directory, such as sidecars and packets: observe records whether they exist and their hashes, and decide reads only the event log.
12. **"Not found" does not mean "does not exist".** Fetch tools may truncate or summarise content. Any judgment that some content does not exist needs more evidence than a judgment that it does.

## 2. Components and locations

| Component | Location | Contents |
|---|---|---|
| Contract | `contracts/review.py`, `contracts/schemas/review_*.json` | Seven schemas: config, unit table, packet manifest, review record, event, head and observation. **The state-transition table and state computation** are pure functions shared by the process driver and `check`, so there are not two implementations that can drift apart. `check` only reads files and produces nothing. |
| Process driver | `skills/hep-authoring/scripts/review.py` | The commands in the table below, plus sentence splitting, scope assignment, sampling, unit mapping, diff, the canary generator and the instruction-file generator |
| Lens table | `skills/hep-authoring/assets/review-lenses.json` | Scope rules, canary types and witness rules, and the matching skill review points |
| Host notes table | `skills/hep-authoring/assets/review-hosts.json` | Isolation preconditions, how to obtain the session start time, the instruction files and settings to record, and the host's shared directories |
| Review procedure | `skills/hep-authoring/references/independent-review.md` | Procedures for the author, reviewer and arbiter agents |
| Configuration | `<project>/reviews/review-config.json` | Follows the `review_config` schema |
| Private directory | Default `$XDG_STATE_HOME/hep-research/reviews/`, or `~/.local/state/hep-research/reviews/` when that variable is unset | Canaries, witnesses, sampling seeds and the slot mapping table |

**Commands**

| Command | Purpose |
|---|---|
| `start DOC [--supersede ID --reason TEXT]` | Start a review: split sentences, assign scope, sample, and allocate slots and models |
| `next` | Run observe, then decide, and print the next action |
| `dispatch SLOT` | Build this attempt's packet with its canaries, seed and instruction file, validate the example, produce the dispatch message, and write a `dispatched` event |
| `returned SLOT` | Run by the author agent when the host reports that an agent has finished |
| `receive SLOT` | Validate the sidecar and write `accepted` or `rejected` |
| `withdraw SLOT --reason R` | Withdraw an attempt |
| `dispose FINDING --as X --reason TEXT [--verified EVID \| --adopted-unverified]` | Handle a finding. X is `changed`, `partially-changed`, `declined` or `unresolved`. Only `changed` and `partially-changed` must carry `--verified` or `--adopted-unverified`. |
| `arbitrate` | Create arbitration items and arbitration slots |
| `rereview` | Start the next round |
| `repair CODE` | List how to fix a repair code; the next `next` confirms the fix |
| `escalate --reason TEXT` | Write an `escalated` event |
| `report` | Produce the report and write `reported` (with the report hash). It does **not** close the review. |
| `close` | Run only when decide row 14 asks for it: run the pre-close check, and write `closed` only if it passes |
| `resolve ITEM --by NAME --decision D --reason TEXT` | A human resolves an escalated item; writes `human_resolved` |

decide can also print two actions that **do not map to a command**: `await` means "do nothing; wait for a host notification or a deadline", and `stop` means "the process has ended or hit an error".

**Implementation details**

- `contracts/schemas/review_record.json` is the single source for field names, enum values and required-field rules. The instruction-file generator, the output example and the receipt checks all read it. A separate test in `tests/` compares the field table in §5.3 of this document with the schema.
- Hash-chain canonicalisation and encoding are imported from the plugin's public interface `contracts.revocation` (`canonical_sha256` and `encode`). Where `contracts.revocation` gets them internally is part of the plugin's existing design and outside this mechanism's scope. The review event log does not go through `read_protected`.
- `reads[]` uses a direct `$ref` to the traceability schema's `read_event`; hep-citations owns the semantics of read records.
- The built-in schema validator does not support `oneOf`, `if/then`, `maxItems` or `maximum`. Formats that depend on kind and basis, and the bounds and allowed ranges of fields, are therefore implemented with `anyOf` plus Python rules in `contracts/review.py`.
- Only the author agent writes the event log, and it takes a file lock before every write: `fcntl` on POSIX, `msvcrt` on Windows. Reviewer agents never write the event log.

## 3. File layout

```
<project>/reviews/
  review-config.json
  <review-id>/
    review_log.jsonl
    review_head.json
    units/round-<n>.json
    round-<n>/
      <slot_id>/attempt-<k>/
        packet/
          manifest.json        names, sizes and sha256 of the other packet files
          instructions.md      generated automatically from the schema and config
          document.md          this slot's version of the document (lens slots include canaries)
          units.json
          scope.json
          items.json           arbitration slots only: arbitration items (§5.2)
        work/                  the only working directory for this attempt
        review_record.json
    report.md

<private_dir>/<review-id>/
  slots.json                   mapping of slot_id to role
  round-<n>/<slot_id>/attempt-<k>/
    canary.json                canaries, key diffs and witnesses
    sample_seed
```

- `slot_id` is a randomly assigned label (S1, S2, …). Directory names reveal neither the role nor how slots relate to each other. There are three roles: lens, shadow and arbiter.
- `packet_sha256` is the sha256 of `manifest.json`.

## 4. Units, scope and sampling

### 4.1 Sentence splitting

- Markdown is split by paragraph and by sentence-ending punctuation (`。`, `？`, `！`, `；`, `.`, `?`, `!`, `;`). Each table row, each code block (including indented code blocks inside list items) and each heading is one unit. LaTeX is split by `\section` and by paragraph.
- Each unit's text must be a contiguous excerpt of the delivered document, after whitespace normalisation. A P1 test checks this; without it, `finding_shape` could not be satisfied.
- List numbers and bullets (`1.`, `-`, `*`) belong to the sentence that follows them and are never split into units of their own. They are stripped before the substantive test. A fragment made only of punctuation, list markers or whitespace is merged into the previous unit.
- Each unit records `id`, its section, kind, text, `text_sha256`, `substantive`, and `in_scope` for each lens.

### 4.2 Mapping between rounds

1. Take the `text_sha256` sequences of the two rounds' units and compute the **true longest common subsequence** with dynamic programming. When there are several longest solutions, choose the one that is lexicographically smallest, comparing positions in the old sequence first and then positions in the new sequence. For example, old `[a]` against new `[a, a]` maps to the first `a` of the new sequence. This makes the result deterministic.
2. Units on the subsequence are marked `unchanged`.
3. Between two adjacent alignment points, the remaining old units and remaining new units are paired by position and marked `changed`. Unpaired old units are `removed`, and unpaired new units are `added`.
4. The algorithm is quadratic in the number of units, in both time and space. A 500-unit document needs about 250,000 cells, which is acceptable. Above 5,000 units, the report raises a warning.

### 4.3 Substantive units

A unit is substantive if it is not a heading and contains any of the following:

- a number, a back-quoted identifier, a path, a quoted citation, or a URL;
- a normative word. The Chinese tokens are matched literally: 必須 (must), 不得 (must not), 不能 (cannot), 不會 (will not), 不包含 (does not include), 從不 (never), 只有 (only), 應 (shall), 應該 (should), 至少 (at least), 至多 (at most), 只能 (may only), 一律 (always), 禁止 (prohibited). The English tokens are must, must not, should, shall, cannot, never, always and only.

The report records the share of substantive units, and P3 calibrates it.

### 4.4 Scope

| Lens | Units in scope |
|---|---|
| `facts` | Substantive units that contain a path or file name that exists in the baseline plugin, or a host term listed in `review-hosts.json` (setting keys, environment variables, instruction file names and so on) |
| `sources` | Substantive units that contain a `file:line`, a URL, or an attribution phrase plus a named document or source. Attribution phrases include 寫著 ("states"), 依⋯文件 ("according to … document") and "according to". A sentence that only puts a term in quotation marks does not count. In the last live round, only 1 of the 15 deep units in the sources slot actually carried a source; the reviewer honestly marked them unresolved and was rejected for it. |
| `design` | All substantive units |
| `bypass` | Substantive units that contain a normative word, a threshold number, a rule code or a state-machine row number |
| Domain lens | Substantive units that match the lens's keywords |

### 4.5 Skim, deep and sampling

- **`skim_units`**: all units in scope. Each must be marked `ok`, `issue` or `n/a`. Every `issue` must map to a finding, and the share of `n/a` must not exceed `na_max_ratio`.
- **`deep_units`**:
  1. Group in-scope units by section, with sections in document order.
  2. Shuffle the section order with the private seed.
  3. Take one unit from each section in turn, choosing within a section with the same seed, until `deep_sample` units are drawn.
  4. If there are fewer than `deep_sample` in-scope units, all of them are deep units.

  Deep sampling is done once, at `start`, with **the round seed**. Re-dispatches within the same round reuse the same deep units. Each attempt also has its own seed, which is used only to generate canaries.

  The same seed and unit table always produce the same sample.
- **Shadow slots**: `focus_units` are the main lens's canary units plus two decoy units, all treated as deep units.
  - Decoys are drawn first from **the main lens's deep units for this round**, excluding canary units. This way the main lens and the shadow both judge the same units, so conflicts can be found.
  - If there are not enough, decoys are drawn from the same lens's in-scope units.
  - Decoys must be able to meet that lens's evidence requirements: decoys for facts and sources must contain a path, `file:line` or URL that exists in the baseline plugin.
  - Shadow slots carry no canaries of their own.
- **Top-up sampling in re-review rounds** also uses the private seed and is equally deterministic.

## 5. Schemas

### 5.1 Configuration `review_config` (1.0.0)

| Field | Default | Allowed range | Basis |
|---|---|---|---|
| `models[]` | required | at least 1 | — |
| `max_rounds` | 3 | 1–5 | Provisional; higher is looser |
| `max_attempts_per_slot` | 2 | 1–3 | Provisional; higher is looser |
| `attempt_timeout_minutes` | 40 | 20–120 | In the first three live rounds, the longest slot took about 12 minutes; the default is about 3× that |
| `deep_sample` | 15 | 5–50 | Provisional; lower is looser |
| `max_units_per_claim` | 3 | 1–5 | Provisional; higher is looser |
| `na_max_ratio` | 0.3 | 0–0.5 | Provisional; higher is looser |
| `unresolved_max_ratio` | 0.3 | 0–0.5 | Provisional; higher is looser |
| `refutation_duplicate_max` | 0.2 | 0–0.3 | Provisional; higher is looser |
| `refutation_min_attempts_for_ratio` | 5 | 3–10 | Provisional; higher is looser. Effective threshold = min(configured value, this slot's number of deep units), minimum 3 |
| `canaries_per_slot` | 2 | 1–3 | Provisional; lower is looser |
| `extra_lenses[]` | empty | additions only | — |
| `private_dir` | see §2 | must be outside the project tree and the host's shared directories | — |

- Python rules check the allowed ranges. Any out-of-range value triggers `config_out_of_range`.
- When any quality threshold is **looser than its default** (the last column above gives the loose direction), a `weak_config` warning is raised and written into the report. For example, setting `unresolved_max_ratio` to 0.49 triggers it even though 0.49 is inside the allowed range.
- Every value marked "provisional" is on the P3 calibration list. The report prints the full configuration actually used.

### 5.2 Packets

- **Common to all slots**: `manifest.json`, `instructions.md`, `document.md`, `units.json` and `scope.json`.
- **`scope.json`**: `slot_id`, `lens`, `skim_units[]`, `deep_units[]`, `focus_units[]`, and every threshold that actually applies to this slot (`max_units_per_claim`, `na_max_ratio`, `unresolved_max_ratio`, `refutation_duplicate_max`, `refutation_min_attempts_effective`).
- **`items.json`** (arbitration slots only): for each item, `item_id`, `type`, `units[]` and `unit_texts`, plus `first` and `second` for a conflict, or `finding` and `decline_reason` for a decline.
- **`units.json` fields are restricted to an allow-list**:
  - `id`, `section`, `kind`;
  - `text`, in this slot's version;
  - `substantive`;
  - `in_scope`, for this slot's lens only;
  - `role` (`skim`, `deep`, `focus` or null).

  It contains **no hashes**, and no scope for other lenses. If the packet held hashes of the original text, a reviewer could re-hash `document.md` and find the mutated units.
- **`instructions.md`** is assembled by the generator from the `review_record` schema, the configuration and the slot role. It contains:
  - every required field and how to compute it. For example, `packet_sha256` is the result of running `sha256sum` on `manifest.json`. A locator's `sha256` is the result of running `sha256sum` on **the whole file**, and a separate `lines` field records which lines were read.
  - the read rules and the working directory;
  - the quality rules for this role, and how each threshold is computed;
  - the evidence-basis table for this role, **listed in full** rather than referring to other sections;
  - one output example.
- **Example validation**: at build time, the example is extracted from **the `instructions.md` actually written**, parsed as JSON and checked with `check --record-only`. The build stops on failure. The example has no length cap.
- **Arbitration slots also get `items.json`.** Each arbitration item contains:
  - the item number and type;
  - the units involved and their original text, without canaries;
  - for a conflict: the full text of both verdicts (rationale, evidence, refutation attempts and findings), ordered first then second;
  - for a decline: the full finding and the author's reason for declining.

  Arbitration slots **can see the verdicts under arbitration**; arbitration cannot work otherwise. Apart from that, like every other slot, they see no verdict unrelated to their items.
- **No slot's packet contains**:
  - the dispatch message;
  - the hash of the original document;
  - the canaries' positions, original values or witnesses;
  - seeds or the slot mapping table;
  - the author's assessment of any verdict.

  A lens slot's `document.md` contains mutated units, but nothing in the packet says which ones they are.

### 5.3 Review record `review_record` (1.0.0)

| Field | Contents |
|---|---|
| `packet_sha256`, `dispatch_nonce`, `instructions_sha256` | Filled in using the methods in the instruction file |
| `role` | `reviewer` or `arbiter` |
| `reviewer` | `identity`, `context` (`fresh` or `human`), `model`, `host`, `slot_id`. **Self-reported** |
| `isolation` | `saw_prior_conversation`, `host_injected[]`, and `instruction_files_seen[]` or `unknown`. **Self-reported** |
| `reads[]` | Optional: a `$ref` to the traceability schema's `read_event`, recording the read level of literature sources; hep-citations owns the semantics |
| `paths_read[]` | `path` and the whole file's `sha256` |
| `skim[]` | `unit`, `mark` (`ok`, `issue`, `n/a`), `finding_id` |
| `claims[]` | `id`, `units[]`, `summary` |
| `evidence[]` | `id`, `basis`, and the required fields for that basis (table below) |
| `verdicts[]` | Exactly one per claim: `claim_id`, `verdict` (`supported`, `partially-supported`, `unsupported`, `unresolved`), `rationale` (must not be empty), `evidence_ids`, `refutation_attempts[]` (`{method, target, outcome}`), `finding_ids` |
| `carry_forward[]` | Used on re-review: `ref` and `status` (`confirmed` with evidence ids, or `reopened`). Includes findings disposed as changed in the previous round (§6.3) |
| `findings[]` | `id`, `kind` (`wrong-value`, `wrong-citation`, `internal-inconsistency`, `unlisted-claim`, `insufficient-evidence`, `scope`, `other`), `severity` (`high`, `medium`, `low`), `units[]` (1 to `max_units_per_claim` contiguous units), `value` (**must be an excerpt of the cited units' text in this slot's version**), `correction`, `description`, `fix` |
| `resolves[]` | Used by arbiters: `item_id`, `conclusion`, `rationale`, `evidence_ids` |
| `limitations` | Required |

All field names use `slot_id` and `carry_forward` consistently; no other spellings are used.

**Evidence bases**

| basis | Required fields | Counts as external evidence | Counts as an independent basis |
|---|---|---|---|
| `locator` | `ref` (path or URL), `lines` or section, `sha256` (the whole file for a local file; for a URL, the fetched copy saved in `work/`) | yes | It depends; see the note below |
| `third-party` | command, implementation name and version, `output_files[]` (in `work/`, each with sha256), and a statement of which implementation's own algorithm produced the expected value | yes | Yes. This corresponds to `docs/maintenance.md:122-123`: the expected value comes from another implementation's own algorithm, not from a library evaluating the assistant's own formula |
| `tool-output` | command, plugin version, `output_files[]` | yes | no |
| `exhaustive` | script (in `work/`) and its `script_sha256`, the enumeration range, `output_files[]` | yes | yes |
| `person` | name or role, date | yes | yes |
| `internal` | `units[]`: the cited unit ids, which **may not include the claim's own units or any unit within two positions of them** | no | no |

**Locator and `maintenance.md`**

`docs/maintenance.md:120-121` defines a locator as follows: "its formula or rule cites a located source (paper, equation, table or page; a review section alone is not enough) that was read and is recorded in the repository". This mechanism applies that definition as follows:

- **Counts as an independent basis** only when the cited source is one of those types (a paper, equation, table or page, including a specification page inside the plugin), and it has been read and recorded.
- **Extra conditions added by this mechanism**: the whole file's hash is recorded. The document under review, and other files the author wrote for this deliverable, do not count.
- **Other locators**, such as a range of lines in code, still count as external evidence but not as an independent basis. The report counts them separately.

### 5.4 Events

| Event | Key fields |
|---|---|
| `round_started` | round, `source_sha256`, unit-table hash, `config_sha256`, slots and models, author identity |
| `observed` | observation time; the delivered document's sha256; the config's sha256 and range-check result; host precondition results (including the session start time and the settings' modification time); hashes of instruction files and settings; shared-directory check results; whether mutated canary text appears in the delivered document; the current document's `changed` and `removed` units relative to this round's unit table; git HEAD |
| `dispatched` | slot_id, attempt, `packet_sha256`, nonce, `instructions_sha256`, deadline, this attempt's canary commitment and seed commitment (each a salted hash), and the attempt start time |
| `returned` | slot_id, attempt |
| `accepted`, `rejected` | slot_id, attempt, `review_sha256`, recomputation results at receipt, and quality metrics or reason codes |
| `withdrawn` | slot_id, attempt, reason (`timeout`, `host-failure`, `isolation-failure`, or `other` with an explanation). Uses up one attempt |
| `late` | A sidecar that appeared after withdrawal: its hash is recorded and it is not received, but it is listed in the report |
| `disposed` | finding reference; disposition (`changed`, `partially-changed`, `declined`, `unresolved`, `auto-canary`); reason; `verification`; `edited_units`; **the round in which it was disposed**; who disposed it. For a given finding, the latest entry wins |
| `change_confirmed`, `change_rejected` | A finding disposed as changed in the previous round is confirmed or reopened in this round by the same lens. Written automatically by `receive` from `carry_forward` |
| `arbitration_needed` | item_id, type, the verdicts or finding involved, first and second |
| `arbitration_resolved` | item_id, conclusion, hash of the arbitration record. Written automatically by `receive` when it receives an arbitration record |
| `escalated` | List of unresolved items. The process pauses for a human; **this is not a terminal event** |
| `human_resolved` | item or finding reference, who resolved it, the decision, the reason. Once every unresolved item has a `human_resolved`, the process continues |
| `change_reverted` | Finding reference. Written by the pre-close check |
| `closed`, `superseded` | Terminal events. `closed` records `report_sha256` and the delivered document's hash |
| `reported` | The report hash. Not a terminal event |

## 6. State machine

### 6.1 Observe and decide

- `next` first runs **observe**. It reads the delivered document, the config, the host settings, the instruction files and the shared directories, then writes an `observed` event.
- observe also records, for each attempt in the review directory, whether the sidecar exists, whether it is still `.tmp`, and its hash.
- Then **decide** runs. It **reads only the event log** and prints the next action. decide is a pure function; the time it needs comes from the observation time in the latest `observed` event.
- observe also runs before every `dispatch` and `receive`.

### 6.2 Slot states

Only the slot's **latest attempt** is considered.

| State | Condition |
|---|---|
| `none` | No `dispatched` yet in this round |
| `dispatched` | There is a `dispatched`, no sidecar, no `returned`, and the deadline has not passed |
| `returned-empty` | There is a `returned`, but `review_record.json` does not exist |
| `overdue` | The latest observation time is past the deadline, and `review_record.json` does not exist |
| `submitted` | `review_record.json` exists (not `.tmp`), and this attempt has no `accepted`, `rejected` or `withdrawn` yet. A sidecar that appears for a withdrawn attempt is recorded as `late`, not `submitted` |
| `accepted`, `rejected`, `withdrawn` | The corresponding event has been written |
| `exhausted` | The latest attempt is `rejected` or `withdrawn`, and all attempts are used up |

Precedence when determining state: `exhausted` > `rejected`/`withdrawn` > `accepted` > `submitted` > `returned-empty` > `overdue` > `dispatched` > `none`.

### 6.3 Finding states

| State | Entered by | Next step |
|---|---|---|
| `open` | The record containing the finding is accepted | dispose |
| `changed` | Disposed as changed or partially-changed, and the `edited_units` at that time cover at least one of the finding's units | Re-checked before close in this round (§6.7); at the start of the next round, added to the same lens's `carry_forward` |
| `change-confirmed` | In the next round, the same lens marks it confirmed in `carry_forward` (`change_confirmed` event) | — |
| `unresolved` | Disposed as unresolved | Handed to a human (§6.5 row 11) |
| `declined-pending` | Disposed as declined, with severity high | Create an arbitration item |
| `reopened` | The arbitration conclusion is uphold-finding; or the pre-close check finds the change was reverted; or in the next round the same lens marks it reopened in `carry_forward` (`change_rejected` event) | dispose, choosing only changed, partially-changed or unresolved |
| `closed` | Disposed as declined (medium or low); the arbitration conclusion is accept-decline; auto-canary; `superseded-by-arbitration` | — |

### 6.4 Arbitration item states

| State | Entered by |
|---|---|
| `needed` | The conditions in §6.6 hold, but there is no `arbitration_needed` yet |
| `dispatched` | There is an `arbitration_needed`, and the matching arbitration slot is not yet accepted |
| `resolved` | `arbitration_resolved` with a conclusion other than unresolved |
| `unresolved` | `arbitration_resolved` with conclusion unresolved, or the arbitration slot is `exhausted` |

When an arbitration slot becomes `exhausted`, its items become `unresolved` directly; this takes precedence over `dispatched`.

### 6.5 Decision rules, in priority order

| Row | Condition | Action |
|---|---|---|
| 1 | Event log or head fails verification | `stop` (error) |
| 2 | There is a `closed` or `superseded`; or the review is `escalated` and some items have no `human_resolved` yet | If escalated with no `reported` after this escalation: `report`. Otherwise: `stop` (waiting for a human) |
| 3 | The latest `observed` carries a repair code | `repair` |
| 4 | A slot is `submitted` | `receive` |
| 5 | A slot is `returned-empty` | `withdraw --reason host-failure` |
| 6 | A slot is `overdue` | `withdraw --reason timeout` |
| 7 | A slot is `none`, or `rejected`/`withdrawn` with attempts left | `dispatch` (all of them listed at once) |
| 8 | A slot is `dispatched` | `await`, with the earliest deadline |
| 9 | A lens or shadow slot is `exhausted` | `escalate` |
| 10 | All lens and shadow slots are accepted, and an arbitration item is `needed` (including a high finding that was just declined) | `arbitrate` |
| 11 | An arbitration item is `unresolved`, or a finding is `unresolved` | `escalate` |
| 12 | A finding is `open` or `reopened` | `dispose` |
| 13 | The delivered document differs from this round's `source_sha256` | Below the round limit: `rereview`; at the limit: `escalate` |
| 14 | None of the above | `close`: run the pre-close check (§6.7). If it passes, produce the report and write `closed`. If not, write `change_reverted`, and the next decide returns to row 12 |

- Arbitration slots go through rows 4 to 8 like any other slot. Row 9 covers only lens and shadow slots. When an arbitration slot becomes `exhausted`, its arbitration items become `unresolved`, and row 11 handles them.
- When `receive` receives an arbitration record, it automatically writes `arbitration_resolved` and updates the states of findings and verdicts.
- The P1 exhaustive test enumerates every combination of slot, arbitration-item and finding states and confirms three things:
  - every combination maps to a row;
  - report is never printed while any arbitration item is `needed` or `dispatched`;
  - report is never printed while any finding is `open`, `reopened` or `declined-pending`.

### 6.6 Creating arbitration items

- **conflict**: two accepted **verdicts**, one supported and one unsupported, whose claims cite overlapping units, form a conflict item.
  - A verdict can appear in several conflict items. If it is overturned in one item and wins in another, it becomes `unresolved` and goes to a human.
  - The main lens's verdicts on its own canary units do not count, because they judge mutated text. The shadow's verdicts on those units count as usual.
- **decline**: a high-severity finding is declined.
- **first and second**: sorted by the lexicographic string order of `(slot_id, claim_id)` and recorded in `arbitration_needed`.

### 6.7 Arbitration conclusions and the pre-close check

**Arbitration conclusions**

| Item type | Allowed conclusions | Effect |
|---|---|---|
| decline | `uphold-finding` | The finding becomes `reopened` |
| decline | `accept-decline` | The finding becomes `closed` |
| conflict | `uphold-first`, `uphold-second` | The overturned verdict is marked superseded and its findings become `closed` (`superseded-by-arbitration`); the winning verdict's findings are disposed as usual |
| either | `unresolved` | Row 11 escalates to a human |

**Pre-close check**: this checks only findings **disposed as changed in this round**. For each one, it recomputes the `changed` and `removed` units between the unit table of the round in which the finding was disposed and the current delivered document. If none of the finding's units is in that list any more, the change was reverted. The finding then returns to `reopened` and is marked `change_reverted` in the report.

Note: if this round has any changed finding, the delivered document always differs from this round's `source_sha256`, so row 13 starts the next round before the review can reach close. The case the pre-close check actually stops is this: the author edits the document, disposes the finding as changed, and then reverts the document so that it matches this round's `source_sha256` again.

**Changed findings from the previous round**: at the start of the next round, they are added to the same lens's `carry_forward`. If the new reviewer agent marks one confirmed, `change_confirmed` is written and the finding becomes `change-confirmed`. If it marks one reopened, `change_rejected` is written and the finding returns to `reopened`.

### 6.8 Round limit

If the last round still has changes, the review escalates. This is deliberate: every change must pass a fresh review before the review can close. The report states the reason for the escalation.

## 7. Rules

### 7.1 Receipt rules (lens and shadow slots)

| Code | Condition |
|---|---|
| `schema_invalid` | Does not match the schema |
| `packet_mismatch` | `packet_sha256` differs from the one recorded in `dispatched` |
| `dispatch_mismatch` | The nonce or `instructions_sha256` differs from the one recorded in `dispatched` |
| `prior_conversation` | `saw_prior_conversation` is true |
| `same_identity` | The reviewer's identity is the same as the author's |
| `finding_shape` | A finding cites more than `max_units_per_claim` units or non-contiguous units; or `value` is not an excerpt of the cited units in this slot's version |
| `read_outside_packet` | `paths_read` contains any forbidden path (see the list below this table), or a file in a host shared directory whose modification time is earlier than this attempt's start time. Tool outputs the host saved automatically during the attempt may be read, but must be copied into `work/` before they are cited |
| `file_hash_mismatch` | For a local file in `paths_read` or in locator evidence (including URL copies fetched into `work/`), the whole file's sha256 differs from the declared one |
| `output_mismatch` | A file in `output_files[]` does not exist, is not in `work/`, or has a mismatched hash |
| `instructions_changed` | The instruction files changed between this attempt's `dispatched` and receipt |
| `claim_shape` | A claim has more than `max_units_per_claim` units or non-contiguous units; a verdict's claim_id does not exist; or a claim has no verdict, or more than one |
| `deep_missing` | Some deep unit is not covered by any claim |
| `skim_missing` | Some skim unit is unmarked; an `issue` has no matching finding; or the share of `n/a` exceeds `na_max_ratio` |
| `basis_missing` | A non-unresolved verdict on a deep unit has no external evidence (facts, sources and domain lenses) or no evidence at all (design and bypass) |
| `self_citation` | Internal evidence cites the claim's own units or units within two positions of them; or a refutation attempt's target is the claim's own unit |
| `refutation_weak` | A supported verdict has no refutation attempt, or one with an empty target. Or: the deep verdicts' refutation attempts total at least the effective threshold, and the duplicate ratio exceeds `refutation_duplicate_max`. The effective threshold is min(`refutation_min_attempts_for_ratio`, number of deep units), minimum 3. The duplicate ratio is the number of attempts whose `(method, target)` occurs more than once, divided by the total number of attempts. |
| `verdict_without_finding` | A partially-supported or unsupported verdict has no finding |
| `unresolved_dominant` | The share of this slot's deep units whose verdicts are all unresolved exceeds `unresolved_max_ratio` |
| `canary_missed` | A canary was not hit (see A5) |
| `carry_forward_missing` | On re-review, a carry_forward item is unmarked, or is marked confirmed without evidence |

For `read_outside_packet`, the forbidden paths are:

- the original delivered document;
- the private directory;
- the event log;
- the directories of other slots or other attempts;
- the author's traceability records;
- the mechanism's own implementation files, relative to the plugin root: `skills/hep-authoring/scripts/review*.py`, `skills/hep-authoring/assets/review-lenses.json`, `skills/hep-authoring/assets/review-hosts.json` and `contracts/review.py`.

The recomputation results at receipt are written into the `accepted` event. Later edits to files in response to findings do not affect a review that was already received.

### 7.2 Receipt rules (arbitration slots)

Skim, deep and canary rules do not apply to arbitration slots.

| Code | Condition |
|---|---|
| Common | `schema_invalid`, `packet_mismatch`, `dispatch_mismatch`, `prior_conversation`, `read_outside_packet`, `file_hash_mismatch`, `output_mismatch`, `instructions_changed` |
| `arbiter_identity` | The arbiter's identity is the same as the author's, or as any reviewer under arbitration |
| `resolves_incomplete` | `resolves` does not cover every item in `items.json`, or an item has more than one conclusion |
| `resolution_type` | A conclusion is not one of the values allowed for its item type (§6.7) |
| `resolution_basis` | A non-unresolved conclusion lacks evidence meeting the evidence requirements of the item's lens. When a conflict spans two lenses, the stricter requirement applies; facts and sources are stricter than design and bypass |

### 7.3 Repair codes

| Code | Condition | Fix |
|---|---|---|
| `config_changed` | The config differs from the one recorded for this round | Restore the config, or restart with `start --supersede` |
| `config_out_of_range` | A config value is outside its allowed range | Fix the config. If it was changed after the review started, use `start --supersede` |
| `canary_in_deliverable` | The full text of a mutated unit appears in the delivered document | Delete it |
| `isolation_precondition` | A host precondition does not hold (§A7) | Configure it per the host table. If a restart is needed, restart the host and then run `next` |
| `isolation_not_yet_effective` | The host table says this method of disabling requires a restart, and the settings file was modified after the host session started | Restart the host, then run `next`. All review state is in files, so the review can resume directly after the restart |
| `shared_dir_contamination` | A file in a host shared directory has a modification time that **falls outside every attempt window**, and it contains this review's packet text, canaries, dispatch message or the author's draft | Move it to the private directory or delete it. Files whose modification time falls inside an attempt window are treated as tool outputs the host saved for the reviewer. They are not contamination; they are only listed in the report |
| `change_without_edit` | A finding was disposed as changed or partially-changed, but the `edited_units` at that time cover none of its units | Edit the document, or dispose again |

If the session start time cannot be obtained, `isolation_not_yet_effective` is not triggered. A warning is raised instead, and the report states "cannot confirm whether the isolation setting has taken effect".

### 7.4 Overall check `contracts/review.py check`

| Code | Condition | Result |
|---|---|---|
| `log_broken` | Hash chain, head or event transitions are invalid | fail |
| `not_closed` | The review has not reached `closed` | incomplete |
| `changed_after_close` | After close, the delivered document's hash differs from the one recorded in `closed` | fail |
| `artifacts_changed` | A received packet, unit table or sidecar has been modified | fail |
| `finding_open` | A finding is still `open`, `reopened` or `declined-pending` | incomplete |
| `uphold_not_honored` | After an arbitration uphold-finding, the author still declined | fail |
| `adopted_unverified` | A finding was disposed as changed or partially-changed with `adopted-unverified` | warning; all are listed in the report |
| `no_model_diversity` | Every slot uses the author's model, or every slot uses the same model | warning |
| `canary_shortfall` | A lens slot has fewer canaries than `canaries_per_slot` | warning |
| `no_control` | A lens slot has no canaries at all | warning; the report marks the slot as having "no quality control" |
| `weak_config` | A quality threshold is set at the loosest end of its allowed range | warning |
| `superseded_reviews`, `late_records` | Other review-ids for the same delivered document; records that appeared after withdrawal | listed in the report |

## 8. Automation

### A1. Process

- `start DOC` does these steps in order:
  1. split sentences and assign substantive units and scope;
  2. sample;
  3. allocate slots and models;
  4. observe;
  5. write `round_started`.
- **Packets are built at dispatch.** `dispatch SLOT` does these steps in order:
  1. generate this attempt's canaries and seed;
  2. build the packet and the instruction file;
  3. extract the example from the instruction file actually written, and validate it;
  4. write `dispatched`.

  Because every attempt regenerates its canaries, packets cannot all be built at `start`.
- If the delivered document already has an unfinished review, `start` refuses to run unless `--supersede` is given.
- The author agent's loop is: run `next`, do the action it prints, run `next` again, and repeat until `stop`. When the host reports that an agent has finished, run `returned`.
- **The dispatch message is always two lines**:

  ```
  Read and follow the instruction file below exactly.
  REVIEW-DISPATCH nonce=<nonce> instructions=<packet>/instructions.md sha256=<instructions_sha256>
  ```

  The first line is a fixed English sentence; it is never translated or reworded.
- With `--now`, `--seed` and fixed observation inputs, the whole process is byte-for-byte reproducible.

### A2. Lenses, slots and models

- Fixed lenses: `facts`, `design`, `sources`, `bypass`. Domain lenses are added automatically by keyword. The author can only add lenses with `extra_lenses`, never remove them.
- Each lens has one shadow slot. Arbitration slots are created as needed.
- Models are assigned in rotation. Where possible, a shadow uses a different model from its main lens, and an arbiter uses a different model from both parties under arbitration.

### A3. Recomputation and verification

- At receipt, the hashes of the following are recomputed: `paths_read`, local locator evidence (including URL copies fetched into `work/`), all `output_files[]`, and the script files of exhaustive evidence.
- With `--rerun`, commands on a read-only allow-list are re-run. If the cwd or plugin version differs from the record, the result is marked not-comparable.

### A4. Re-review

`rereview` builds the mapping as in §4.2, then:

1. Each lens's deep units = its in-scope `changed` and `added` units, plus the units of all that lens's findings from the previous round (renumbered through the mapping), topped up at random to `deep_sample` if short.
2. `carry_forward` = all of that lens's non-canary verdicts from the previous round, renumbered through the mapping. Items marked `reopened` must be judged again in this round, and a new verdict that is not supported must carry a finding.
3. Verdicts and findings that map to `removed` units are listed for dispose and can only be disposed as changed (with a deletion reason) or declined.

Every round and every attempt regenerates canaries and rebuilds the shadow slots.

### A5. Canaries

**Generation**

- Types follow the lens table.
- The replaced **full string** appears exactly once in the document, and the new string does not appear in it. Canaries for different slots are never in the same unit.
- **Key diff**: first locate the difference with a character-level diff, then widen it on both sides:
  - if the difference is inside a number, widen it to the whole numeric token (digits, decimal points and hyphens), such as a line-number range;
  - if the difference is inside an identifier, widen it to the whole identifier.

  A numeric key diff is matched on the digits alone, and must not be directly preceded or followed by another digit. Matching therefore does not depend on any following unit word or on the language used.
- **Witness**: every canary needs a witness showing that the packet contents, or the sources the reviewer may read, reveal the error. Otherwise the candidate is not used.
  - facts and sources: the original value can be found in some file of the baseline plugin (record path and line number).
  - design: the cited row, section or rule actually exists, and its content contradicts the mutated statement (record the cited unit).
  - bypass: the original value of the same parameter appears in the packet's `scope.json`, the config table, or another unit of the document. The "exactly once" constraint applies only to the replaced full string, not to this parameter value.
- **The witness must prove two things**:
  - the original value is right, by the rules above;
  - the new value is wrong. Examples:
    - for facts and sources, the new line range does not contain the cited content, or contains different content;
    - the new number differs from the actual value in the plugin;
    - for design, the new row or section's content does not match the statement;
    - for bypass, the new threshold contradicts the packet's `scope.json` or the config table.

  If either is missing, the candidate is not used.
- If no qualifying candidate is found, the slot gets one canary fewer and `canary_shortfall` is triggered. With no canaries at all, `no_control` is triggered.

**Hit**

A hit is a finding that passes `finding_shape`, cites the canary unit, and whose `value` contains the new value's key diff.

Because `value` must be an excerpt of the cited units and the number of units is capped, one finding cannot hit several canaries scattered across the document.

The correction is tracked separately as the "exact-correction rate": the share of hits whose `correction`, `description` or `fix` contains the original value's key diff. The exact-correction rate appears only in the report and does not affect receipt.

**Automatic disposal**

A hit finding whose `units` are all canary units is written as `auto-canary` by `receive`.

### A6. Arbitration

See §6.4, §6.6, §6.7 and §7.2.

### A7. Isolation preconditions, instruction files, settings and shared directories

**Isolation preconditions (Claude Code)**

| Method | What the official docs say | How this mechanism treats it |
|---|---|---|
| Set `CLAUDE_CODE_FORK_SUBAGENT=0` in `env` in `settings.json` | Sub-agents docs, section "Let Claude wait for a subagent": after setting it, "Run `claude` again from your shell, or open a new VS Code conversation." | If the settings file was modified after the session started, `isolation_not_yet_effective` is triggered |
| Add `Agent(fork)` to `permissions.deny` | The docs say this rule prevents Claude from starting a fork, but not when it takes effect | Warning; the R0 isolation self-check is the fallback |
| Neither set | — | `isolation_precondition` is triggered |

Whichever method is used, the author agent must name a non-fork subagent type when it dispatches.

**Instruction files to record** (per the Claude Code memory and sub-agents docs)

- `~/.claude/CLAUDE.md`, `~/.claude/rules/`;
- `CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md` in the working directory and each parent directory;
- `.claude/rules/`, including path-scoped rules;
- `CLAUDE.md` in subdirectories, marked on-demand;
- `AGENTS.md` and `.claude/AGENTS.md`, marked conditional:
  - they require v2.1.277 or later;
  - by default they are read only when neither the working directory nor any parent has a `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` (`~/.claude/CLAUDE.md` does not count);
  - the "Project instructions" setting can change this behaviour;
- files pulled in by `@path` from any of the above;
- the subagent definition file used for dispatch, and its `memory` and `omitClaudeMd` fields;
- the managed policy file and `claudeMd` in managed settings: record their hashes if readable, otherwise mark them not-inspectable.

**Settings to record**

- **Settings that affect loading**:
  - `claudeMdExcludes`;
  - the "Project instructions" setting value (`claude-md-and-agents-md`, `claude-md`, `managed-only`, and so on);
  - the value of `cc-plugin-agents-md@builtin` in `pluginConfigs`. It is read only from `~/.claude/settings.json`, files given with `--settings`, and managed settings; project and local settings files are ignored. Before v2.1.285 the ID was `agents-md@builtin`.
  - `--add-dir`, and `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`. Only when this variable is set do directories added with `--add-dir` load their `CLAUDE.md`.
  - `--setting-sources`.
- **Settings that affect isolation**: `CLAUDE_CODE_FORK_SUBAGENT`, and `Agent(fork)` in `permissions.deny`.

**Host shared directories**

In a Claude Code cloud session, all agents share one scratchpad directory, and tool results are stored in the same session directory. observe checks these directories before every dispatch and receive.

**Timing**

Instruction files and settings are recorded once at each `dispatched` and once at receipt. Any change within one attempt is rejected with `instructions_changed`. git HEAD is recorded but not judged. A separate advisory scan is also done, and its results go into the report.

### A8. Report

`report.md` is generated by the script, and the author agent attaches it unchanged. It contains:

- the configuration actually used, and the `weak_config` result;
- for each slot:
  - its model;
  - its number of attempts, with the reasons for any reject or withdraw;
  - its skim-mark distribution and deep-verdict distribution;
  - its share of partially-supported verdicts;
  - the count of each evidence basis, with independent bases and tool-output counted separately;
- for canaries:
  - the hit rate, split into skim and deep;
  - the exact-correction rate;
  - the witnesses, in two parts: original right and new wrong;
  - the slots with `canary_shortfall` or `no_control`;
- shadow review results;
- each finding's disposition, and whether the author verified it;
- arbitration conclusions, `change_reverted`, `change_confirmed`, `change_rejected`, `late` and `returned-empty`;
- the list of tool outputs the host saved automatically during attempts;
- the results of the host-precondition, instruction-file and shared-directory checks, and the categories of host-injected content;
- all review-ids for the same delivered document;
- the limitations from §10 that actually applied in this round.

## 9. Protocol

### Author agent

- Run `start`, then run `next` repeatedly and do the action it prints, until `stop`. When the host reports an agent has finished, run `returned`.
- **Dispatch**: pass the fixed two lines, and only those, to a new agent. On Claude Code, name a non-fork subagent type. On hosts without subagents, open a new session for each slot.
- During the review, do not put packets, drafts, canaries or your own tool outputs in the host's shared directories.
- **Verify before dispose**:
  - after verifying, record it with `--verified <evidence>`, using the same basis categories as reviewers;
  - if you cannot verify but still want to adopt the finding, use `--adopted-unverified`;
  - declined needs a reason;
  - if the evidence conflicts and you cannot decide, use `unresolved` and hand it to a human.
- **Rules for author verification**:
  - When fetching web pages, save a copy and record the URL form used.
  - To conclude that some content does not exist, try at least two URL forms (for example the `.md` version and the normal web page), and query in a way that asks for a verbatim quote.
  - If a reviewer gave a verbatim quote and the author cannot reproduce it, the only allowed verdict is "unresolved" (dispose as `unresolved`), never "not adopted".
  - If two or more independent reviewers quote the same verbatim text, the report must flag it.
- When reporting back, attach `report.md` unchanged.

### Reviewer and arbiter agents

They follow the instruction file, which covers:

- the R0 isolation self-check: if any prior conversation is visible, record it and stop; record the categories of host-injected content;
- the read rules and the working directory;
- skim and deep review;
- the evidence-basis table;
- how to write a finding: `value` gives the text being challenged, and `correction` gives what the reviewer believes is right;
- how to handle carry_forward on re-review;
- write `.tmp` first, self-check with `check --record-only`, and rename only after it passes.

The arbiter's instruction file contains only the rules that apply under §7.2, plus the full evidence-basis table.

### Humans

A human uses `resolve` to handle escalated items and may choose to give a final sign-off. This mechanism does not write attestations. The attestation reviewer role is a free string, and the plugin's `contracts/schemas/attestation.json` notes that "reviewer roles are assigned under Q-06", which is still undecided.

This mechanism also does not settle the v6.3 open conditions O04 ("reviewers other than the author") and O14 ("which reviewer roles may accept reports as evidence"), which are listed in `docs/dev/v6.3/custodian-gate-requirement.md:42-43`. A closed agent review does not by itself meet the "a review record exists" criterion of `docs/dev/v6.3/decision-enforce.md:20`; whether it can is a maintainer decision. The terms "review packet" and "shadow" here are unrelated to `docs/dev/v6.3/review-packet.md` (a human review of the G-ENFORCE inputs) and `docs/dev/v6.3/shadow-review.md` (a difference review between check suites).

### Plugin registration and ownership

- **Ownership table**: add a row to `docs/routing-contract.md`:
  - Topic: Independent review packets, review records and the review log
  - Owner: hep-authoring
  - Claim terms: `independent review`, `review packet`
  - Capability-matrix row: `—`

  Per the rules in `tools/check_ownership.py`, the owner's Owns line must declare at least one of these terms. No other skill may claim either term in its Owns line, in the "Use when" part of its description, or in the README's skill table. Matching is case-insensitive, treats hyphens as spaces, and uses word boundaries.
- **Routing cases**: add example sentences to the existing hep-authoring and hep-citations rows of the routing contract. Test cases go in the table in `tests/routing/make_cases.py`, and `tests/routing/cases.json` is then regenerated. `cases.json` is a generated file that `tests/routing/test_routing_static.py` compares byte for byte, so it must not be edited by hand. Chinese cases use the language code `zh-Hant`.
- **Architecture decision (needs maintainer approval)**: three statements each cover something different:
  - `docs/architecture.md:12`: no required subagents;
  - `docs/protected-data-architecture.md:526`: no required subagents, and this sentence is one of the architectural invariants in §11 of that document;
  - `docs/routing-contract.md:7`: no coordinator skill and no dispatch API.

  Position: the plugin still dispatches and requires no subagent. `next` only drives the review process inside hep-authoring; it does not dispatch work between skills. This position must be written up as a decision record in `docs/dev/`, with one clarifying sentence added at each of the three places. Changing the architectural-invariant sentence needs special approval.
- **Evidence bases**: the definitions of locator, third-party, exhaustive and person follow `docs/maintenance.md:118-126`. `tool-output` is a category this mechanism adds, and it is not an independent basis. The decision record must state this distinction.
- **Relation to 0.20.0 `evidence_records`**: 0.20.0 added the `computational-run` field `extension.evidence_records`, which references run records by path and sha256. tool-output and third-party evidence in review records could later be wrapped as computational-run records and referenced that way. P1 does not do this; it is listed for evaluation in P4.

## 10. Guarantees and limitations

### Detectable under the §0 assumptions

- The delivered document changed during the review or after close, or mutated units leaked into it.
- Isolation problems:
  - inconsistent dispatch;
  - a reviewer that can see the prior conversation;
  - reads of forbidden paths, including host shared-directory files that existed before the attempt started and the mechanism's own implementation files;
  - the author contaminating the shared directories;
  - wrong isolation-precondition settings;
  - **on hosts where the session start time can be obtained**, settings changed after the session started.

  The parts that concern reviewer-agent behaviour assume it reports truthfully.
- Wrong or stale hashes of local files and outputs, and output files outside the working directory.
- Weak review work:
  - deep units not covered;
  - evidence without a basis;
  - citing the claim's own or adjacent units;
  - boilerplate refutation attempts;
  - verdicts missing findings;
  - findings too broad, or a value that is not original text;
  - incomplete skim marks;
  - missed canaries.
- Conflicting verdicts; a declined high finding without arbitration; arbitration conclusions not honoured; findings not handled; findings adopted by the author **without declaring** verification.
- Changes after dispose:
  - disposed as changed without an edit;
  - an edit later reverted;
  - a previous round's change not confirmed by the next round;
  - old verdicts silently carried over on re-review.
- An agent that finished without leaving a record; reviewer timeouts; an attempt to close while arbitration is unresolved.
- Several reviews of the same delivered document.
- Accidental damage to the event log, or invalid transitions.

### Out of scope: deliberate fraud

- The author agent writes the sidecar itself. It holds the original document, so it can find the canaries and make every recomputation pass.
- The author agent tells reviewer agents in advance how to fill in fields, through a channel other than the dispatch message.
- Dispatch by fork, then the reviewer agent does not report truthfully.
- Rewriting the whole event log and head, or deleting a review's directory.
- Modifying the canaries or sampling seeds in the private directory. The private directory is neither encrypted nor permission-isolated.

Guarding against these needs something the author cannot change: external custody, a process other than the author, or host-level isolation. All of these go beyond layers 1 and 2.

### Other limitations

- Canaries and sampling measure only a lower bound.
- A canary hit only requires pointing at the mutated value, so there may be a few false hits, where a reviewer happens to question the same value for another reason. The exact-correction rate helps to watch for this.
- When the document under review is the review mechanism itself (such as this document), reviewer agents can learn the canary types from the document, which makes canaries less hidden.
- Isolation preconditions can confirm only setting values and setting times, not how a running session actually behaves. On hosts where the session start time cannot be obtained, even setting times cannot be compared, and only a warning is raised.
- The mechanism does not know about shared paths that the host table does not list.
- Blind spots within one model family are correlated.
- Content hashes for remote sources are valid only for the fetched copy. Fetch tools may truncate or summarise content (principle 12). In live testing, the `.md` URL and the normal web-page URL of the same document returned different content.
- Who wrote a file in a host shared directory can only be inferred from its modification time: files inside an attempt window are always treated as the reviewer's tool outputs. Files the author writes during an attempt window will be misattributed to the reviewer.
- Modification times can be wrong because of copying, restoring or clock skew, which can lead to wrong judgments.
- Refutation attempts are checked only for an empty target and for repeated `(method, target)` pairs. Changing one character each time avoids the duplicate check.
- tool-output is not checked for relevance to the claim.
- Substantive units and scope are decided by rules.
- A locator is checked only for "actually read, with location and hash recorded", not for whether the cited content is really relevant to the claim.
- Cost: in the first three live rounds, each round dispatched 8 agents, and a single slot took about 1 to 12 minutes. The worst case multiplies this by the number of attempts and rounds. The report lists the number of agents actually dispatched.
- P1 has only facts and design canaries. In P1, the sources and bypass slots are all `no_control`, and the report marks them; their quality can only be judged from the other rules and the shadow review.
- For slots dispatched in parallel, the tool outputs the host saves automatically fall in the same time window, and the mechanism cannot tell which slot a file belongs to. A reviewer may read another slot's tool output during its attempt.
- A reviewer's identity is a self-reported name, so `same_identity` and `arbiter_identity` catch only identical names.

## 11. Implementation order

| Phase | Contents | Acceptance criteria |
|---|---|---|
| P1 core | Seven schemas; `check`; all commands; the instruction-file generator (including validation of the example actually written, sharing one schema with the receipt checks); sentence splitting, LCS mapping, scope and sampling; the observe-plus-decide state machine (including arbitration write-back, `returned`, deadlines, `late` and the pre-close check); A2, A3 (without `--rerun`), A4, A6, A7, A8; facts and design canaries (with key diffs and two-sided witnesses) and shadows; file locking; the procedure document, ownership row, routing examples and `make_cases.py` cases; a draft decision record; contracts bumped to 3.3.0 (0.21.0 already used 3.2.0) | See the list below this table |
| P2 quality extensions | sources and bypass canaries (with witness rules); `--rerun`; LaTeX splitting; notes for other hosts | Tests for generating each canary type, for two-sided witnesses, and for the "no candidate found" case |
| P3 eval | At least 20 documents, each with real errors of known types injected by script. The error list comes from the injection script or from human labelling. Compare author self-check, a single lens, four lenses, and four lenses with different models | See the list below this table |
| P4 traced mode and evidence integration | Decided by the P3 results. Add `scope.independent_review` to traceability 1.1.0, with "valid only in 1.1.0" enforced by a code rule in `communication.py`. Evaluate referencing tool-output evidence through `evidence_records`. Bump contracts to 3.4.0 | Results for 1.0.0 records are unchanged |

**P1 acceptance criteria**

- Every rule in §7 has a negative test.
- Every decide row and every arbitration conclusion has a table test.
- The exhaustive test required by §6.5 passes, with two extra checks:
  - a round with a changed finding moves to the next round rather than closing;
  - a finding changed in the previous round always appears in the next round's `carry_forward`.
- The field table in §5.3 of this document matches the schema.
- On test data, canary witnesses prove both that the original value is right and that the new value is wrong.
- On random small sequences, the LCS mapping matches brute-force enumeration.
- The instruction-file generator's output example passes `check --record-only`.
- An end-to-end example uses only `next` to run four lenses and four shadows. It includes:
  - one reject and re-dispatch;
  - one returned-empty;
  - one timeout;
  - one arbitration (uphold-finding);
  - one `adopted-unverified`;
  - one `change_reverted`;
  - one `change_confirmed`;
  - one escalate, followed by the report, then a human `resolve` after which the process continues;
  - one re-review round with changed, added and removed units;
  - finally, closed.
- Numeric key diffs match under both Chinese and English corrections.
- A shadow slot given 4 identical refutation attempts is caught by `refutation_weak`.
- Every unit's text is a contiguous excerpt of the delivered document.
- With fixed `--now`, `--seed` and observation inputs, two runs are byte-for-byte identical.
- `run_all_checks.py`, the host-neutral, layering and ownership checks all pass.

**P3 acceptance criteria**

- For each lens, the canary hit rate, exact-correction rate, real-error detection rate and false-positive rate are reported with 95% confidence intervals.
- Every "provisional" value in §5.1 is chosen from data, with the reasoning written in the decision record.
- The partially-supported share and the skim and deep detection rates are all reported.

`review.*` rules are not registered in `contracts/rules/registry.json`. In 0.21.0 it still holds only the 23 `r-*` and `l2.*` rules.

## 12. How the 12th-edition review findings were handled

Slot labels refer to the 12th-edition round, and unit ids are 12th-edition ids. The author personally checked every item.

| Source | Finding | Handling in the final edition | Author verification |
|---|---|---|---|
| S6 | After escalate, no event could record a human's decision | `escalated` becomes a pause; new `resolve` command and `human_resolved` event | Verified (12th ed. §5.4, §6.5) |
| S8 | The P1 end-to-end example required both "report after escalate" and "finally closed", but escalated was terminal | As above; both can now happen in one review | Verified (12th ed. §11) |
| S8 | Running `report` directly closed the review, bypassing the preconditions of row 14 | `report` no longer closes; new `close`, requested only by decide | Verified (12th ed. §2 command table) |
| S8 | decide read sidecar files directly, contradicting principle 11 and the pure-function claim | observe records sidecar state; decide reads only the event log | Verified (12th ed. §6.1) |
| S8 | Where the state-transition logic lives was not stated, so `check` and the driver might each implement it | The state-transition table lives in `contracts/review.py`, shared by both | Verified (12th ed. §2) |
| S3 | Shadow slots have only 4 deep units, below the threshold of 5, so the duplicate-ratio check never runs | Effective threshold = min(configured value, deep units), minimum 3; negative test added in P1 | Verified (12th ed. §5.1, and the shadow packet's `scope.json`) |
| S3 | `weak_config` fired only at the loosest end, so 0.49 avoided it; and which end is loose was not stated | Config table gains a loose-direction column; anything looser than the default fires | Verified (12th ed. §5.1) |
| S1 (field) | The sources scope included sentences that only quoted terms; only 1 of 15 deep units carried a source, and honest unresolved verdicts were rejected | sources scope now covers only real citations | Verified (author counted S1's deep units in the 12th-ed. round) |
| S8 | LCS ties were broken only by old-sequence position, leaving several results | Compare old positions first, then new positions | Verified (author confirmed by brute force: old `[a]` vs new `[a, a]` has two longest alignments with the same old position) |
| S7 | An indented code block in a list item was split into two ordinary sentences whose text was not original text, so `finding_shape` could not be satisfied | Indented code blocks are also one unit; P1 tests that every unit is an original excerpt | Verified (U0389, U0390 in the 12th-ed. round) |
| S7 | A3 required recomputing the exhaustive script's hash, but the schema had no such field | New `script_sha256` | Verified (12th ed. §5.3) |
| S7, S8 | The generated instruction file marked every locator as an independent basis, contradicting "it depends" in §5.3 | Instruction file now generated from the same description in the schema | Verified (instruction files of the 12th-ed. round) |
| S8 | Deep-sampling timing and seed timing contradicted each other | Deep sampling uses the round seed, once, at `start`; per-attempt seeds are used only for canaries | Verified (12th ed. §4.5 and A1) |
| S8 | Conflicts were judged per unit, but a verdict covers up to 3 units, so it could be overturned and win at once | Judged per verdict; overturned-and-won becomes unresolved | Verified (12th ed. §6.6) |
| S8 | Every disposition required declared verification, inconsistent with the protocol | Only changed and partially-changed require it | Verified (12th ed. §2 and §9) |
| S8 | The Chinese/English numeric matching test was in P2, but P1's facts canaries already need it | Moved to P1 | Verified (12th ed. §11) |
| S8 | Slots dispatched together might read each other's host auto-saved files | Added to the §10 limitations | Verified (12th ed. §7.1) |
| S8 | Fields of `scope.json`, `items.json`, `canary.json`, `slots.json` and the unit table were undefined; Q-06 was not explained | Added in §5.2 and Appendix B; Q-06 source stated | Verified (comment in the plugin's `contracts/schemas/attestation.json`) |
| S6 | Row 12 printed two actions, breaking determinism | Row 12 prints only dispose; declined high findings are handled by row 10 | Verified (12th ed. §6.5) |
| S6 | P1 had only facts canaries, leaving every other lens without quality control, and §10 did not say so | P1 adds design canaries; §10 states the sources and bypass limitation | Verified (12th ed. §11) |
| S3 | `change_reverted` had no matching event | New event | Verified (12th ed. §5.4) |
| S3 | The field-table consistency test sometimes said it covered §5 and sometimes §5.3 | Unified as §5.3 | Verified (12th ed. §1, §2) |
| S1, S2, S7, S8 | 8 canaries | Disposed automatically | All hit, all exactly corrected |

## 13. Final status

### Settled and tested

- **Threat model and layering**: guards only against negligence and laziness; uses only layers 1 and 2; the plugin dispatches and requires no subagent.
- **Dispatch and isolation**: a two-line dispatch message plus the instruction-file hash; the R0 isolation self-check; a separate working directory per attempt. Across the last five rounds, all 40 slots reported that they could not see the prior conversation, and every dispatch message matched.
- **Canaries**: allocated by lens scope; two-sided witnesses; key-diff matching; the shadow reviews the original text. The valid canaries in the last two rounds had a 100% hit rate.
- **Evidence bases**: the four bases from `docs/maintenance.md:118-126`, plus tool-output and internal. In the last round's facts slot, all 19 pieces of evidence were external.
- **Author verification rule**: in the 10th-edition round it actually prevented a wrong judgment (whether fork requires a restart).

### Needs implementation and data before it is settled

- Every threshold marked "provisional" in §5.1: calibrated by P3.
- The rules for substantive units and scope: the last round still found the sources scope too broad, and P3 must measure their accuracy.
- The share of partially-supported verdicts in design and bypass slots varied widely between rounds, from 13% to 73%. Watch whether the rules still push reviewers away from marking supported.
- The relation between canary hit rate and real-error detection rate: so far there is canary data only.

### Maintainer decisions

1. Amend the three "no required subagents" statements, of which `docs/protected-data-architecture.md:526` is an architectural invariant.
2. Adopt the evidence-basis categories of `docs/maintenance.md` for review verdicts, and add tool-output.
3. Contracts version: bump to 3.3.0 in P1, because 0.21.0 used 3.2.0 for simulated dataset-records.
4. P3 eval cost: about 8 agents per round, about 1 to 12 minutes per slot, and at least 20 documents.

### Recommended next step

Start P1 in the order of §11. When P1 is done, use its end-to-end example to re-run the last review round, and confirm that the implemented tools match the results of these manually run rounds before starting P3.

## Appendix A: Review history

| Edition reviewed | Slots | Canaries | Receipt result | Main lesson |
|---|---|---|---|---|
| 3rd | 2 | none | no receipt rules | The author missed 4 high-severity issues that two independent reviewers found in one round |
| 6th | 3 | 2; facts 2/2, bypass 2/2, design 1/2 | no receipt rules | Canaries must match lens scope; the document must not show canary examples |
| 7th | 4 | 3, 3/3 | no receipt rules | The mapping table itself must not leak canaries |
| 8th | 8 | 4, 4/4 | 6/8 passed | Verbatim copying of the dispatch message is not workable; scope rules were too broad; a shared scratchpad causes cross-slot contamination |
| 9th | 8 | 8, actually 8/8 (script: 7) | 5/8 passed | Hit matching was too strict; the author must also verify before adopting a reviewer's claim |
| 10th | 8 | 8, actually 7/8 (script: 4) | 5/8 passed | The shortest diff can shrink to a single character; corrections may use another language or another correct answer |
| 11th | 8 | 7 valid, 7/7 (1 invalid) | 7/8 passed | Field names differed between spec and example; witnesses must prove the new value is wrong |
| 12th | 8 | 8, 8/8, all exactly corrected | 7/8 passed | Script verdicts matched manual re-check exactly for the first time; sources scope still too broad |

## Appendix B: Auxiliary file fields

| File | Fields |
|---|---|
| `units/round-<n>.json` | Per unit: `id`, `section`, `kind`, `text`, `text_sha256`, `substantive`, `in_scope` (one boolean per lens). Also `round`, `source_sha256`, and the mapping from the previous round (`unchanged`, `changed`, `added`, `removed`) |
| Packet `units.json` | The allow-list in §5.2, with no hashes |
| `scope.json`, `items.json` | See §5.2 |
| `canary.json` (private) | Per canary: `unit`, `original`, `mutated`, `old_key`, `new_key`, `witness_right`, `witness_wrong` |
| `slots.json` (private) | Mapping of `slot_id` to role (lens, shadow, arbiter) and model |
| `sample_seed` (private) | The round seed and each attempt's seed |
