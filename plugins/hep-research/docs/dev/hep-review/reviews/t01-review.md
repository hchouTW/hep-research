# T01 independent review: hep-review kernel (commit 5e4ef528)

- Date: 2026-10-29
- Reviewer: independent agent (did not write the code)
- Read: `contracts/hep_review.py` (all), `contracts/schemas/hep_review_*.json` (record, definitions; others skimmed),
  `contracts/fixtures/hep_review/byte_vectors.json`, `tests/contracts/hep_review_fixtures.py`,
  `test_hep_review_json.py`, `test_hep_review_decision_table.py`, `test_hep_review_kernel.py`; spec v9 (en)
  sections 1.3, 3.1-3.2, 4, 6, 7, 8, 10, 15.6, 19.
- Ran: the three test modules (73 tests, OK); scratch scripts outside the repository that build bundles with the
  test fixture builder and call `validate` / `project` / `decide_summary` / `render_report`; the same projection
  under `PYTHONHASHSEED=1..4`. No repository file was changed apart from this report.

Attestation used in every "summary output" result below: `report_mode=current`, `validator_is_latest_approved=true`,
`head_continuity=verified`. So "summary output" means the report prints the no-defect sentence.

### F1 blocker: Layer 1 changes between processes (set iteration order)

- Location: `contracts/hep_review.py:893` and `:907-910` (`_tier_of`)
- Spec clause: §7.6 (layer 1 is reproducible byte for byte), §7.3 historical check, N60, D23
- Evidence: `extra = (... set difference ...) | set(ob["independence_requirements"])` is a set. The loop
  `for c in extra:` adds one `tier_reasons` string per unmet condition, so the order of the strings follows string
  hashing, which changes per process. One required obligation with
  `independence_requirements=["second-reviewer","domain-expert","different-institute","cross-check"]` and one
  supported review gives these layer-1 digests: `999bfa7f…` (seed 1), `6fae9536…` (seed 2), `4e32654b…` (seed 3),
  `32530da4…` (seed 4). A third party who recomputes from the export (N60), or `check_historical`, gets
  "mismatch" on an untouched record. The tests do not catch this: one process uses one seed, and no fixture has
  two or more unmet extra conditions.
- Fix: iterate `sorted(extra)`. Add a test that projects in subprocesses with two different `PYTHONHASHSEED`
  values and compares the bytes. Also check that layer 1 never iterates any other set (none found today).

### F2 major: Renaming or merging through obligation_map gets around the whole downgrade list

- Location: `contracts/hep_review.py:422-429` (`_downgrades`, `elif oid in omap` branch)
- Spec clause: §8.1 (every bullet), §8.2.2, A22a, N56
- Evidence: field-by-field checks (methods, evidence, independence, decision_required, tolerances,
  adoption_policy, criterion and assumptions) run only when the old ID is still present. For a mapped ID the code
  only asks that at least one target be required. Example: parent obligation `O1` has tolerance `0.001`,
  `second_method_required=true`, `verification_required=true`, `qualifications=["stats"]`. The revision maps
  `O1 -> O1b`, where `O1b` has `decision_required=false`, `required_methods=[]`, `evidence_requirements=[]` and a
  new criterion. `check_plan(p2, p1, intent)` returns `[]`. One `supported` review of `O1b` then gives
  `supported`, R2, and summary output.
- Fix: when an old required obligation maps to new IDs, apply the same checks to each required target (or to their
  union for a split, plus the scope judgment). Without an `equivalent_or_stronger` judgment for the target, a
  changed criterion or changed assumptions are rejected. Add rename and merge rows to the A10/A22a test.

### F3 major: Positive answers skip qualification and adoption_policy, and an author's response record can support an obligation

- Location: `contracts/hep_review.py:978-981` (`cur_answers`) and `:1131-1163` (`_outcome`)
- Spec clause: §7.1 (supported needs a "qualified judgment"), §7.2 (adoption under adoption_policy; "the item
  remains pending until done"), §6.5 (author may not judge), §1.3.4
- Evidence: `_qualified` and the adoption policy are applied only to findings. (a) The plan sets
  `verification_required=true`, `second_method_required=true`, `qualifications=["stats"]`. The reviewer's
  assignment has `qualified={"satisfied":false}`. One `supported` answer with no verification and no second
  method gives outcome `supported`, R2, summary output. (b) A `type: "response"` record from `author-a` on an
  `author` assignment, carrying `answers:[{verdict:"supported"}]`, gives outcome `supported`, R1, summary output.
  The only effect of authorship here is the non-author tier drop. Nothing stops an author record from producing
  the outcome.
- Fix: count an answer toward an outcome only if its record type is submission, verification or adjudication.
  Require `_qualified(assignment)`. Apply the obligation's adoption_policy to positive answers as well: when
  verification or a second method is required, keep the outcome `undetermined` (pending) until a qualified
  verification, or an attempt with a different method, is current. Use the same rule for `not-applicable`
  discharges.

### F4 major: Any not-applicable reason other than three fixed strings counts as a valid discharge

- Location: `contracts/hep_review.py:210` and `:553-564`; the schema `discharge.reason_category` is a free string
  (`contracts/schemas/hep_review_record.json:53-54`)
- Spec clause: §7.1 ("not-applicable must not be used because of missing data, difficulty or budget"), A07,
  §1.3.4
- Evidence: `{"reason_category":"data-unavailable","basis":"self-reported","reason":"we lack the data"}` on a
  required obligation gives outcome `not-applicable`, `plan_requirements_met=true`, summary output at R2. The
  refusal works only for the literal strings `missing-data`, `difficulty` and `budget`. The discharge basis is
  never checked (`self-reported` passes), and neither is the discharger's qualification.
- Fix: make `reason_category` an enum of allowed applicability reasons (for example `condition-absent`,
  `out-of-scope-by-intent`) in the schema and the kernel, and reject anything else. Require basis `observed` or
  `declared`, and a qualified, non-author assignment, as in F3.

### F5 major: An author's judgment can refute or dispute a finding

- Location: `contracts/hep_review.py:840-856` (`_finding_states`)
- Spec clause: §6.5 (author may not dismiss findings), §7.2 (author disagreeing → response only; "not
  resolved by ... author denial"), §5.1 step 7
- Evidence: judgments count when `_qualified(jasg)` holds, whatever the record type or role. The fixture's author
  assignment is `qualified: true`, as an author is a qualified physicist. Case: a required obligation `O1` is
  supported. An optional obligation `O2` has `verification_required=true` and a violated answer with a finding.
  The author submits a `response` record with
  `{"kind":"finding_assessment","verdict":"refuted","basis":"self-reported"}`. The finding becomes `refuted`,
  `O2` becomes undetermined and is listed in `uncovered_optional`, all flags are false, and the summary is output.
  The defect is gone on the author's word alone. For a finding adopted directly, the same author judgment makes
  it `disputed` (`has_disputed_findings=true`): an author denial is being counted as a substantive conflict.
- Fix: in `_finding_states`, count `finding_assessment` judgments only from verification, submission or
  adjudication records whose actor is not an author of the finding's material. Show author judgments as
  responses. A suspected conflict they raise stays open until a reasoned judgment record decides it.

### F6 major: R3 can be reached from caller-supplied, self-anchored claim data

- Location: `contracts/hep_review.py:221` (`BUNDLE_KEYS` includes `claim_binding`), `:917`, `:931-957`
  (`_claim_binding_ok`; line 954)
- Spec clause: §15.6 (a claim-binding commit is written to the case log; chain from a *trusted* checkpoint;
  *this case's* fingerprint), §4.1 R3, A26, N37, N63
- Evidence: (a) the binding is a top-level bundle key. It is not a committed object, it is not covered by the
  commit chain or `payload_digest`, and it is not tied to `as_of_seq`. (b) `trusted_checkpoint` is read from the
  binding itself, so any chain is "trusted" if it starts where it says it starts. (c)
  `fp = plan.get("capability_fingerprint", binding.get("case_fingerprint"))`: when the plan has no fingerprint,
  the case fingerprint is taken from the binding, and the binding only has to agree with itself. A one-commit
  chain built by hand passes:
  `claim={"state":"evaluated-scope","fingerprint":"z"}`, `chain_segment=[{commit:{seq:7}, digest:…,
  object_digests:[digest(claim)]}]`, `trusted_checkpoint={seq:7, digest:same}`, `case_fingerprint:"z"`. With one
  required restriction observed as enforced, this gives `achieved_tier=R3`, and the summary "R3 (review within the
  evaluated scope): …" is output (with `r3_state_matches=true`). The existing N37 test only checks a binding whose
  `case_fingerprint` disagrees with its own claim.
- Fix: require the binding as an object committed in the case log (a record kind such as `claim-binding`) and
  read it from `entries`. Compute the case fingerprint from committed case objects (plan or host profile), never
  from the binding. Take the trusted checkpoint from a committed anchor or an injected, attested input, not from
  the binding. Do not fall back to the binding's own fingerprint: without a case fingerprint, R3 is not reached.

### F7 major: validate() does not apply schemas or plan admission, and the current validator's rule set leaves them out

- Location: `contracts/hep_review.py:328-329` (`VALIDATOR_RULES = {"0.1.0": (rule_check_object,)}`), `:487-584`
  (`validate`), `:1184-1203` (`_version_inconsistencies`)
- Spec clause: §3.1 / §3.2.1 (validator: structure includes schema), §7.3 (validator versions; version
  inconsistency for objects referenced by the head plan), §10.2 (bool is not int), §8.1, N21, N50
- Evidence: (a) a record with `"plan_revision": true` is admitted and bound to revision 1, because
  `True in {1: …}` is true in Python. The result is `supported`, R2, summary output. The commit check
  `head.get("seq") != i` also accepts `seq: true` for commit 1. The N21 test only checks the `is_int` helper and
  `schema_validate` on a plan. It never shows that the kernel path rejects a bool used as an integer. (b) A head
  plan that `check_plan` rejects (required→optional and decision_required dropped:
  `['downgrade.decision_required_dropped','downgrade.required_to_optional']`) projects normally. The demoted,
  not-examined obligation moves to `uncovered_optional`, and the summary is output at R2. The current validator
  does not report the head plan as a version inconsistency either, because its rule set holds only
  `check_object`. Rejection at commit is T02's job, but §7.3 makes the current validator responsible for marking
  admitted objects it judges non-compliant. Today it cannot judge a downgrade or a schema violation.
- Fix: add schema validation per `record_kind`, and `check_plan(plan, parent, intent)` for each committed plan
  revision, to the current version's rule set. In `validate`, make a failing plan an input error or a version
  inconsistency (see D24). Quarantine records that fail the schema. Add a kernel-path test for N21
  (`plan_revision: true`, `seq: true`).

### F8 minor: Very long integer tokens raise ValueError instead of IngestError

- Location: `contracts/hep_review.py:95-101` (`_int`), `:139-147`
- Spec clause: §10.2 (rejection, never a leak); N39 (similar: `RecursionError` must not leak)
- Evidence: `ingest_json(b"[" + b"1"*5000 + b"]")` raises a bare `ValueError: Exceeds the limit (4300 digits)…`.
  This is not an `IngestError`, so a caller catching `IngestError` crashes.
- Fix: in `_int`, reject tokens longer than 17 characters as `json.int_range` before calling `int()`, or catch
  `ValueError` there.

### F9 minor: render_report accepts "correct" / "passed" wording and a qualifier in another sentence

- Location: `contracts/hep_review.py:1250-1280`
- Spec clause: §4.4 (qualifier "in the same sentence"; "No tier may use an unqualified 'correct' or 'passed'"),
  N14, N36
- Evidence: `presentation={"title":"Analysis passed: physics is correct", "summary_sentence":"{tier_qualifier}.
  The analysis is correct and passed; no still-valid defect was observed within the scope of this check."}` is
  accepted. It renders `# Analysis passed: physics is correct` and a summary line in which the qualifier ends its
  own sentence before the no-defect phrase.
- Fix: require `summary_sentence` to contain `"{tier_qualifier}: " + NO_DEFECT` as one unit (or drop the template).
  Refuse a title or sentence that contains `correct`, `passed`, `pass` or `verified` (case-insensitive), or limit
  the title to a fixed set of choices.

### F10 minor: Locators are bound by material ID only, and located material is left out of the closure

- Location: `contracts/hep_review.py:639-641` (`_record_binding`), `:771` (`closure`)
- Spec clause: §6.4 (locators bind a material ID and digest), §8.3 item 2 (any other material the reviewer
  actually cited)
- Evidence: a finding with `locator={"material_id":"M2","digest":"00…00"}` (a digest not in the manifest) is
  admitted, and the finding is `supported`. The closure uses `targets ∪ cited_materials`, never
  `locator.material_id`. A finding that locates a non-target material therefore stays current after that material
  changes.
- Fix: quarantine a record whose locator digest differs from the manifest's `raw_ref.digest` for that material,
  and add `locator.material_id` to the closure's material set.

### F11 minor: Some disclosure wording is missing or inaccurate

- Location: `contracts/hep_review.py:1221-1246` (`decide_summary`)
- Spec clause: §4.3 (when advisory, the report must say "…neither observed nor enforced"), §4.4 (target vs achieved
  "with the reasons")
- Evidence: the advisory sentence is added only inside the summary text. A report that claims R2 with an advisory
  third condition but outputs no summary (for example because a defect exists) never contains the sentence. In
  the case "two required obligations, one examined", the disclosure for target R2 / achieved R1 reads
  `"…no admitted submission…; no claim-binding commit; no required runtime restriction is stated, so R3 is not
  claimed"`. Reasons for not reaching R3 (from obligations that reached R2) are mixed into the R2 shortfall.
- Fix: put the advisory sentence in `disclosure` whenever `advisory_conditions` names it and the achieved tier is
  R2 or higher. Build the target/achieved reasons only from obligations whose tier is below the target, and only
  from reasons for the tiers between their tier and the target.

### F12 minor: A mechanical answer conflict on an optional obligation is never open

- Location: `contracts/hep_review.py:985-991`, `:1086-1093`
- Spec clause: §7.4 (has_open_questions includes "an unverified conflict"), §7.2 (the validator marks a conflict
  mechanically)
- Evidence: optional `O2` has one `supported` answer and one `violated` answer without a finding. `O2` is marked
  undetermined and listed in `uncovered_optional`, `has_open_questions=false`, and the summary is output. For a
  required obligation, open is true only because the outcome is undetermined, not because of the conflict.
- Fix: add every obligation in `conflict_obs` without an adjudication to `open_reasons` as an unverified conflict,
  and keep such obligations out of `uncovered_optional`.

### F13 minor: Several tests pass on fixtures that do not represent their case

- Location: `tests/contracts/test_hep_review_kernel.py:331-338`; `tests/contracts/test_hep_review_decision_table.py:189-195`,
  `:234-239`, `:363-368`; `test_hep_review_kernel.py:563-571`
- Spec clause: §19.1 D17/D25/D23, N12, N38
- Evidence: (a) `test_n12_…` asserts `output_summary=True` for an N12-labelled input. The spec result for N12 is
  "see D17" (open=T, no summary). The test name says "suspicion stays open", but it asserts the opposite. (b) The
  D17 fixture's suspected conflict lists only one item in `between`, so it does not model two opposing records.
  (c) The D25 fixture's revision deletes a required obligation with `obligation_map=[]`. `check_plan` rejects that
  plan (`['downgrade.required_removed']`), so D25 is tested only on a plan that cannot be admitted. The admissible
  form of D25 (an unmapped *optional* old obligation that carries a violated finding) is untested. (d) D23 and N38
  call `check_historical` only with the same validator version (or an unknown one). No test recomputes with an
  older rule set against a newer one, for example the existing `STRICT_RULES["0.2.0-test"]`.
- Fix: rename and fix N12 so it expects D17's flags when a suspicion is recorded, and keep "free text alone does
  not create a conflict" as a separately named test. Give D17 a suspicion between two answers from two records.
  Build D25 from an optional old obligation, and assert that `check_plan` returns no errors. Add a historical
  check that produces a layer 1 with `0.1.0` and checks it with `0.1.0` while the current rules include
  `0.2.0-test`.

### F14 minor: project() trusts the disposition fields of a dict the caller passes in

- Location: `contracts/hep_review.py:960-973`
- Spec clause: §7.6 (`project(bundle, validator_version)`), §7.3 (disposition is a pure output of the validator),
  A26
- Evidence: `project` takes the output of `validate` as a plain dict and reads `record_integrity`,
  `quarantined_*` and `input_error` from it. A caller that edits these (for example clears `quarantined_items`
  and sets `record_integrity="valid"`) gets a positive layer 1. `render_report` recomputes from the bundle, which
  limits the damage, but `project` itself is not the specified pure function of the bundle.
- Fix: make `project(bundle, validator_version)` call `validate` itself (keep the two-step form private), or
  check that the passed dict equals `validate(validated["bundle"], version)`.

### F15 minor: Creation-order checks cover only record→assignment/plan

- Location: `contracts/hep_review.py:287-319`, `:611-620`
- Spec clause: §6.4 (creation order), A25
- Evidence: the code checks only that a record comes after its assignment and plan. It does not check that an
  assignment comes after its plan, or that an assignment's `plan_revision` exists. It does not check that a
  content_ref inside a plan, packet or assignment names an object committed later. `check_object` catches only the
  specific keys `assignments`, `assignment_ids` and `assignment_refs`.
- Fix: in `validate`, map each object's nested `logical_id` refs and `*_id` / `plan_revision` bindings to commit
  sequence numbers. Reject or quarantine any reference to an object at the same or a later sequence number.

## Checked and found correct

- Strict ingestion: size checked before decoding, strict UTF-8 then BOM check on the text, a non-recursive depth scan
  that skips strings, `RecursionError` mapped to an error, the duplicate-key pairs hook (escaped keys too), float
  and constant rejection, `-0` and the safe integer range, and the lone-surrogate check after parsing. The encoder
  matches §10.3. The gold vectors cover the §10.3 list, and I checked the control-character vector by hand.
- `same_ref` compares all five fields (P04). The legacy adapter keeps the native value and excluded fields (P03,
  P28). The embedded-digest and producer-excluded-field checks work (N05).
- Disposition: an evidence item whose blob is missing is quarantined (missing counts as not ok). Quarantine spreads
  along `depends_on`. An unknown dependency quarantines the whole record. A mismatch submission quarantines that
  record and gives `partial-invalid`. A06 gives an input-error only.
- Closures: a missing `tools` field is unrecorded, `tools: []` needs no environment observation, a different or
  unobserved executor is treated as different, the closure includes uncited targets and adoption_policy, and
  regrouping packets does not change the closure. Stale positive results become not-examined with no current facet.
  Stale negative findings become open follow-ups and appear under unverified historical defects.
- Flags, met and summary_eligible follow §7.4/§7.5 for all decision-table rows as built. Optional tiers do not
  lower the report tier. The R2 floor and its bases match §4.3. Fidelity "transcribed" caps the tier at R1.
- `decide_summary` needs `report_mode=current`, the latest approved validator and verified continuity. Broken
  continuity makes integrity invalid. Every summary sentence starts with its qualifier. R0 never renders a summary.
- Purity: no file, clock, network or randomness use in `contracts/hep_review.py`.
