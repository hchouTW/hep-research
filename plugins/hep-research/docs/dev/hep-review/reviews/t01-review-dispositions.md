# Dispositions: independent T01 review

Report: `reviews/t01-review.md`, SHA-256 `5820722fe2b86f0d0a8feed944f4662a95a6452da5fe56b3caae43e23b855228`
(submitted by file transfer; the reviewer's declared digest matched the bytes read: digest-bound). Inputs frozen at
commit `5e4ef528`; their SHA-256 values are in STATE.md.

**Independence actually achieved**: non-author (the reviewer wrote none of the code; declared), fresh context
(observed: a new subagent dispatched with the Agent tool, given only files, spec sections and the case list, not the
author's assessment), same model as the author, shared filesystem (it could read anything in the worktree; advisory
only). No model diversity, no runtime isolation.

Every adopted fix has a regression test written first and observed failing before the fix
(`tests/contracts/test_hep_review_review_fixes.py`: 23 failures and 3 errors before, 26 passing after).

| Id | Severity | Disposition | What was done |
|---|---|---|---|
| F1 | blocker | **adopted** | `_tier_of` iterates `sorted(extra)`; a test projects in four subprocesses with `PYTHONHASHSEED` 1-4 and requires one digest. No other set is iterated into layer 1 (checked) |
| F2 | major | **adopted** | `_downgrades`: a 1:1 rename through `obligation_map` gets the full field-by-field check (criterion/assumptions need an `equivalent_or_stronger` judgment on the old or new id); a split or merge is checked against the union of its required targets (methods, evidence, independence) and each target (decision_required, adoption policy, shared tolerances); whether new criteria cover the old one stays a scope-judgment planning gap (spec 8.2.3) |
| F3 | major | **adopted** | An answer counts only from a submission, verification or adjudication record whose assignment is qualified (basis observed or declared, holding the policy's qualifications). The adoption policy now applies to positive results and discharges: `verification_required` needs a current `answer_assessment` from a qualified non-author verifier, `second_method_required` needs two completed methods; until then the outcome is `undetermined` (pending). Schema: judgment kind `answer_assessment`, assignment `qualifications` |
| F4 | major | **adopted** | Discharge `reason_category` is an enum (`condition-absent`, `out-of-scope-by-intent`, `superseded-by-other-obligation`) in schema and kernel; anything else is quarantined (`discharge.invalid_reason`); basis must be observed/declared from a qualified reviewer or verifier (`discharge.basis`) |
| F5 | major | **adopted** | Judgments count only from qualified, non-author judges in submission/verification/adjudication records; an author's assessment never refutes or disputes |
| F6 | major | **partly adopted** | The binding is now a committed object (`record_kind: claim-binding`, schema `hep_review_claim_binding.json`); `claim_binding` is no longer an accepted bundle key. The trusted checkpoint must be stated by the plan (`evaluation_checkpoint`) and the case fingerprint is the plan's `capability_fingerprint` with no fallback. *Not adopted*: an injected, attested checkpoint input to layer 1, because layer 1 must be a function of the bundle alone; the plan is the committed control record written under the user's authority, and layer 2 still re-checks the claim's current state |
| F7 | major | **partly adopted** | Kernel: integer fields (`seq`, `revision`, `plan_revision`, `intent_revision`) use `type(x) is int`; a bool `plan_revision` quarantines the record; the current validator's rules now include plan admission (`rule_check_plan`), so a non-compliant head plan enters the version-inconsistency list (open). Rules take `(object, lookup)`. Schemas are applied at commit by the store (I/O side, `store._admit`; test `test_schemas_are_applied_at_commit`). *Not adopted*: schema validation inside the kernel, because the schema module reads files and the kernel must do no I/O; the kernel keeps its own Python checks of every field it binds on |
| F8 | minor | **adopted** | Integer tokens longer than 16 digits are `json.int_range` before `int()` |
| F9 | minor | **adopted** | The summary template must keep `"{tier_qualifier}: " + NO_DEFECT` as one unit; title and template text may not contain correct/passed/pass/verified/proven |
| F10 | minor | **adopted** | A locator digest must equal the manifest snapshot digest (`binding.locator_digest`); the located material joins the closure |
| F11 | minor | **adopted** | The advisory sentence is in the disclosure whenever the achieved tier is R2+ and the third floor condition is advisory; target-vs-achieved reasons come only from required obligations below the target |
| F12 | minor | **adopted** | A mechanical conflict not resolved by adjudication of every opposing finding is an open reason (`unverified_conflict`) and never listed as uncovered optional |
| F13 | minor | **adopted** | N12 split into "free text alone is not a conflict" and "a recorded suspicion without a judgment stays open (D17 flags)"; D17 fixture's suspicion is between two answers of two records; D25 rebuilt in its admissible form (an optional old obligation carrying a violated finding left out of the map; `check_plan` returns no errors); a historical check against an older and a newer rule set is tested |
| F14 | minor | **partly adopted** | `project()` recomputes `validate(bundle)` and refuses a validated input whose disposition differs. The two-step public API of spec 17.3 (`validate`, `project(validated_bundle, ...)`) is kept rather than changed to `project(bundle)` |
| F15 | minor | **adopted** | Creation order: an assignment committed before its plan revision quarantines its records; a plan naming a later manifest/intent, or any metadata ref to a later object, is an `order.forward_reference` diagnostic and makes record integrity `partial-invalid` |

No finding was rejected. The blocker (F1) is fixed; per the task file (§7 step 6, §4.2) a blocker still goes to the
user with this disposition before the run continues past T02.
