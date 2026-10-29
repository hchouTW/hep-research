# G1 gate report: hep-review record prototype (spec v9 §18.3)

**Status: prepared; G1 is declared only after the user confirms the dispositions of the G1 review blockers (task file §7.6, §4.2).**

Date: 2026-10-29. Branch `hep-review-v9-impl` in the worktree `~/hep-research/.claude/worktrees/hep-review-v9`, base
`42f5bad1` (hep-research 0.43.0). Nothing was pushed, merged or released.

## 1. Claim

**Experimental.** hep-review can produce R0, R1 and R2 review **records** and two-layer reports from them on the measured
host (Claude Code CLI, macOS). **No claim of scientific review capability is made.** The T0S spike (go) is a
prerequisite and does not count toward G1; no G2 pilot has been designed into results or scored. R3 is not reachable on
this host (no enforced runtime restrictions).

## 2. Scope achieved

| Task | State | Owned cases (spec §19.5) | Evidence |
|---|---|---|---|
| T00 preflight | done | N01 not-applicable-with-basis; N02, N04, N40 pass | `discovery.md` §7, `baseline.md` |
| T0S spike | done, go | (prerequisite; no cases) | `spike/protocol.md` (committed before the first dispatch), `spike/observations.md`, `host-profile.md` |
| T01 kernel | done | 62 / 62 pass | `tests/contracts/test_hep_review_{json,decision_table,kernel,review_fixes}.py` |
| T02 materials, store, continuity, export | done | 30 / 30 pass | `tests/skills/hep_review/test_{materials,store,continuity_export}.py` |
| T03 skill, registration, host adapter, pilot design | done | 15 / 15 pass | `tests/skills/hep_review/test_{coordinator,cli,pilot_generator,g1_review_fixes}.py` |

The decision-table generator recomputes all 30 rows of spec §19.1 three ways (the hand table, an Appendix-A rule model
and the real projection) and they agree. G1 used engineering fixtures only; the cases involving live reviewers are
for G2/G3 (spec §19).

## 3. Case table (owned by T00-T03; 111 cases)

All pass except N01 (not-applicable-with-basis: the worktree was created, so its failure path, a hard stop, was not
exercised). No case is fail, not-run or blocked. Per-case mapping to test names: the state file `cases` block and the
docstrings of the test modules (each names its cases).

Not run, with reasons:
- the live routing run for the new skill description (paid model calls; needs approval; static routing checks pass);
- `claude plugin validate` / `codex plugin load` host checks (`--no-cli` in every aggregate run);
- H5 store persistence and H6 checkpoint round trip (need the next session).

## 4. Independent reviews and dispositions

| Review | Inputs | Findings | Dispositions |
|---|---|---|---|
| T01 kernel | commit 5e4ef528 | 1 blocker, 6 major, 8 minor | 12 adopted, 3 partly; fixed with tests first; user accepted 2026-10-29 |
| G1 (T02 + T03) | commit 96f70b01 | 4 blocker, 4 major, 8 minor | 14 adopted, 2 partly (M3 st_dev cross-check, m5 inode record deferred); fixed with tests first (`reviews/g1-review-dispositions.md`) |

Independence achieved in both: non-author (declared), fresh context (observed), same model, shared filesystem (the
"no other evaluations seen" condition advisory only). No model diversity, no runtime isolation.

## 5. Host profile summary (measured 2026-10-29)

Fresh-context subagents observed; sibling drop files and other sessions' transcripts readable by reviewers (so "no
other evaluations seen" is advisory); transcripts writable by reviewers (host-transcript fidelity never qualifies); real
parallel dispatch; reviewers write files and compute SHA-256 (16/16 digest-bound in the spike); no enforced runtime
restrictions; filesystem shared. Store persistence and checkpoint round trip pending the next session.

## 6. Regression status

Clean baseline at 42f5bad1: 31 checks pass, 0 fail, 2 host-CLI skips. Branch at b491ff9e (after both review fix rounds): 31 pass, 0 fail, 2 host-CLI skips; unittest 6214 run, 0 failures, 0 errors, 168 skipped, 491 modules. No regression against the clean baseline.

## 7. Known limitations

- Only submission records can be committed: verification, response and adjudication records have no raw-derivation
  path yet and are refused at commit (the kernel handles them; the I/O path is T04 work).
- Schema 0.x; protocol hep-review/0; all data labelled experimental.
- The plugin description in `.claude-plugin/plugin.json` still says "seven core skills" (already stale before this
  work); not changed here.
- Spike instances were author-written; three were wrong as constructed and the reviewers caught them. The pilot
  generator therefore checks every instance with a deterministic oracle before writing it.
- The reviewers in both independent reviews were the same model as the author.

## 8. What G2 needs

The user gate U1 (who holds gold and nonces: user off-host, user-approved deterministic oracles, or stop at G1); then
T04: freeze the EvaluationProtocol (`pilot/protocol-draft.md`), commit salted commitments, run the 48 scheduled trials
on the full R2 path with fresh-context reviewers, calibrate the grader, report the three denominators, evaluate the
engineering and scientific gates separately, and freeze schema 1.0.0 only on a pass. Also: the live routing run for the
skill description (approval for paid calls), and H5/H6 in the next session.
