# Dispositions: independent G1 review (T02 + T03)

Report: `reviews/g1-review.md`, SHA-256 `3f28ff7beff8b935178e31be7f2e800773ba6a83f45144204df803ecb860943b`
(file transfer; the declared digest matched the bytes read: digest-bound). Inputs frozen at `96f70b01` (SHA-256 of
each file in STATE.md).

**Independence actually achieved**: non-author (declared: the reviewer wrote none of the code), fresh context
(observed: a new Agent-tool subagent given only file paths, spec sections and the case list, not the author's
assessment), same model as the author, shared filesystem (it could read anything here: advisory only). It did not see
the T01 review report (not named in its prompt; not enforced).

Regression tests first: `tests/skills/hep_review/test_g1_review_fixes.py` (21 tests) failed before the fixes
(19 failures, 8 errors including subtests) and pass after.

| Id | Severity | Disposition | What was done |
|---|---|---|---|
| B1 | blocker | **adopted** | `head_continuity` is broken (`saved-value-not-on-chain`) when any digest this session wrote is no longer on the anchor segment, and (`head-rolled-back`) when the head is behind the session's last commit; the reviewer's rollback probe is the test |
| B2 | blocker | **adopted** | `fork` only when continuity is broken and only from the last trusted head (the latest own commit still on the chain, or the anchor); the genesis records `broken_case`; `migrate` refuses a transform that drops any record, assignment or supplied material; the report discloses a fork (source, excluded commits, broken case) or a migration |
| B3 | blocker | **adopted** | The store binds a host profile and refuses an assignment whose condition bases exceed it (`assignment.basis_exceeds_host`: observed no-other-evaluations without filesystem isolation, observed fresh context without an Agent-tool invocation id, observed authorship) or that names another host profile (`assignment.host_profile`). `make_assignment` needs the dispatch invocation id for an observed fresh context and records it with the host-profile digest; new CLI command `assign` |
| B4 | blocker | **adopted** | The parser moved to `submissions.py` (a deterministic function of committed objects and raw bytes); the store re-derives every submission record from its stored raw bytes at admission and refuses any difference (`record.not_derived_from_raw`). Record types without a raw-derivation path (verification, response, adjudication) are refused at commit until one exists (`record.type_not_derivable`; T04). CLI `ingest` derives and commits in one call |
| M1 | major | **adopted** | `non_author_condition`: declared only when every target material has a non-empty author list with a declared or observed basis; otherwise unknown |
| M2 | major | **adopted** | Every nested value is type-checked; wrong types become limitations, never tracebacks; a string `missing_inputs` is not split |
| M3 | major | **adopted** | `check_location` judges the resolved path of the nearest existing ancestor (symlinks into synced or network folders are refused). *Not adopted*: an `st_dev` cross-check against mount entries (the resolved-path match covers the reported case) |
| M4 | major | **adopted** | Commands `assign`, `packets`, `supply` added; `ingest` commits; the reference table rewritten to match `--help`, with a test that runs `--help` for every documented command |
| m1 | minor | **adopted** | The packet form has a `locator` (material id + lines or JSON Pointer) and no bare `not-applicable`; finding evidence kept as `evidence_text` |
| m2 | minor | **adopted** | `report` reads persistence from the host profile; when not observed it discloses that and asks for the checkpoint and an export |
| m3 | minor | **adopted** | `verify_export` binds the top-level context and segment to every commit header and `segment_origin` to the genesis header; the checkpoint's context is compared |
| m4 | minor | **adopted** | New segment ids take the highest existing number + 1 |
| m5 | minor | **partly adopted** | The root's last component is opened with `O_NOFOLLOW` (a drops folder replaced by a symlink is refused). *Not adopted*: recording the root's device and inode at assignment time (deferred to T04 with the live dispatch path) |
| m6 | minor | **adopted** | New committed object `supply` (schema `hep_review_supply.json`) bound to an assignment; the projection makes no-other-evaluations-seen unmet when it contains another evaluation; CLI `supply` |
| m7 | minor | **adopted** | An independent confirmation completes separation without new evidence; the P30 test now uses a pure confirmation |
| m8 | minor | **adopted** | `add_obligation` requires the intent's authority; a mismatched submission keeps the declared digest on the record; SKILL.md states the refused-store branch and the export-before-ending rule |

No finding was rejected. Four blockers were reported; per the task file (§7 step 6, §4.2) they go to the user with
this disposition before G1 is declared.
