# M2c proposal: the `allowed_outputs` matching rule and O15 (v6.3 analysis-check programme)

Status: **approved 2026-10-16; M2c is being built** (see Decision). This is step 3 of the "Decision change" in
`decision-enforce.md`. M2c (D05d run lineage, D08 run cases) starts only after this decision. Labels: **Confirmed**,
**Inferred**, **Unresolved**.

## What M2c is (from the brief, C9 and D05d)

- **The `run-lineage/v1` suite** reads, without changing anything:
  - the batch adapter's campaign computational-run, cross-checked against `state.json` collection records, chunk
    digests, the recorded bundle digests, `digest_of` and `check_campaign`;
  - single runs, through `contracts/verify_run.py`.
- **A result binding** per root: the result, the terminal run or campaign merge, unit, binning, scope and validation
  status, the merge result file by bytes digest, the campaign uid, the execution bundle, and the analysis bundle and
  lock digests used. It is written after execution and never changes the bundle.
- **Acceptance:** V20, V33, V38, V53, V54, V55, V56, V61, V62, V63 and V70. Then V32 (D10, post-execution), and the
  post-execution part of V60.
- **Fixtures, all synthetic and in temporary folders:**
  - the batch adapter on `examples/batch-partition`'s fake schedulers, with a freeze added in the test fixture (run
    only with `--out <tmp>`);
  - `core.partition.campaign` with `executors.LocalExecutor` for the `state.json` cases;
  - `examples/local-partition` for single runs.

  No change to `core/partition/`, and no state-changing campaign call outside the tests' own temporary campaigns.

Two decisions are open before D05d can be built.

## 1. The `allowed_outputs` matching rule (Open Question, D05d)

**Today (Confirmed):**
- `blinding.allowed_outputs` in `hep-research.project.json` is a list of strings with no matching rule
  (`contracts/schemas/project_config.json`). The only use in the checkout is a bare file name, `"sidebands.json"`, in
  `tests/core/test_blinding.py`.
- The brief's default: until a rule exists, only results with status `asimov` or `synthetic` count as
  blinding-permitted, and anything else is unverified.

**Options:**

| Option | An entry matches | Weakness |
| --- | --- | --- |
| A. Artifact IDs | the envelope `artifact_id` of a cited output, exactly | the producer writes the ID; a file without an envelope cannot be listed |
| B. Exact paths | the project-relative POSIX path of a cited output file, exactly, plus the bytes digest the result binding records | a rename breaks the match (fails closed) |
| C. Output kinds | an artifact type or output kind | one entry allows every future file of that kind; no reviewer can bound it |
| D. Path patterns (globs) | any path the pattern covers | the same unbounded set as C, plus the ambiguity of glob dialects |

**Recommendation (Inferred): A and B together, as explicitly prefixed exact entries. No kinds, no patterns.**
- `artifact:<artifact_id>` matches an output whose envelope `artifact_id` equals it exactly.
- `path:<project-relative path>` matches a cited file whose normalized path equals it exactly. The path has no `..`,
  is not absolute, and contains no glob characters. The match is recorded with the bytes digest from the result
  binding, so a file changed after the match is a different output.
- **Unprefixed entries** such as `"sidebands.json"` match **nothing**. A result binding citing such an output stays
  `unverified` (`blinding.allowed_output_ambiguous`), with a next step: rewrite the entry with a prefix. This keeps
  today's projects valid while refusing to guess which of several files a bare name means.
- **A match is a policy declaration, not a fact.** The project config is agent-writable, and its authoritative copy
  covers `agent_policy` only. An outcome that rests on a matched entry is therefore declaration-based (C12): flagged
  in diagnostics, and unverified in the formal-use view until an accepted review lists the report.
- **A blinded spec citing an output that neither has status `asimov` or `synthetic` nor matches an entry** is
  violated (V70). Reports and summaries carry digests and statuses only, never values.

**Compatibility (Confirmed by the schema):** both prefixes are plain strings, so the project-config schema does not
change.

## 2. O15: campaigns, a local backend, a format-version field

| Question | Recommendation (Inferred) | Why |
| --- | --- | --- |
| Which executions must go through a campaign? | **None, as a checker rule.** Every root records the evidence level its records support: single runs are `declared`; campaigns with collection records and one common bundle digest are `campaign-recorded`. Whether a purpose needs `campaign-recorded` is the custodian's purpose policy, beside `accept_pre_execution_only` (`custodian-gate-requirement.md`). | A checker rule would decide policy. The brief already gives each level its meaning, and a checksum never upgrades a level. |
| A local backend for the batch adapter? | **No, not in M2c.** | The brief's fixtures cover every case without one (fake schedulers with a test-side freeze, `LocalExecutor` for `state.json`). A backend is a new adapter capability with its own validation and approval of each submission. |
| Ask `core/partition` for a format-version field? | **Not now; record it as a later request to the steward (hep-computing).** The campaign reader determines capability from the fields present, as the brief says. An old campaign without `collected` stays `declared`. | M2c does not need it, and `core/partition/` must not change in this programme. A version field would make capability detection explicit later, as a separate, reviewed change. |

## Scope and cost if approved (Inferred)

- **D05d:**
  - the campaign reader;
  - single-run reuse of `verify_run.py`;
  - the result-binding format: a new schema `result_binding.json`, a v6.3 sidecar. It is not the attestation or
    permit schema, so G-SCHEMA does not apply;
  - the blinding rule above;
  - R-CLOSE and the status rules.
- **D08 run cases:** RUN-CHAIN, RUN-STATUS, RUN-LINEAGE, RUN-EVIDENCE, RUN-CAMPAIGN, and CASE-CHAIN post-execution.
- **D10 post-execution:**
  - V32: semantic drift at run time, checked against the lock digest the result binding records;
  - the post-execution part of V60: the result files a report's binding cites must be in the permit's `artifacts`.

  These are advisory checks in `permit.py`, with no permit schema change.
- **Estimate:** 4–5 sessions, on the basis of M2a (similar size: a reader, a new sidecar format, about a dozen V
  cases).
- **Result:** 80 of 80 V parts on synthetic data. Every rule stays in shadow mode.

## Risks (Inferred)

- **Campaign records are agent-writable.** `campaign-recorded` guards against mistakes and forged chunk files, not a
  forged `state.json` (brief, C9). Reports must say so at every level they show.
- **The fake-scheduler fixture needs a freeze added on the test side.** The example must stay unchanged; the brief
  requires approval to change it.
- **Context cost.** Measured per slice in D08; M2c re-measures it.

## Owner

Programme owner: hchouTW. Implementer: Claude Code session (self-reviewed, C15).

## Decision

*To be completed by the owner:*
1. The matching rule: approve A+B as prefixed exact entries, or choose another.
2. O15: approve the three answers, or change them.
3. Build M2c now, or keep it paused.

**Decided 2026-10-16 by the owner (hchouTW): "approve and build".**
- The matching rule is approved as written: prefixed exact entries `artifact:` and `path:`, no kinds, no patterns.
  Unprefixed entries match nothing, and a match is declaration-based.
- The three O15 answers are approved as written.
- M2c is built now, on synthetic campaigns only, under the brief's guardrails:
  - no change to `core/partition/`;
  - no state-changing campaign call outside the tests' own temporary campaigns;
  - `examples/batch-partition/run.py` only with `--out <tmp>`.
