# Decision record G-ENFORCE (v6.3 analysis-check programme)

Status: **decided 2026-10-16: every rule stays in shadow mode** (see Decision). Written 2026-10-16 after M3 for the chain and ratio suites (D09
shadow review and refusal matrix, D10 advisory report check). Labels: **Confirmed**, **Inferred**, **Unresolved**.

## Analysis question

May any new rule leave shadow mode and become an enforcing condition for some purpose? The brief allows that only
when all six conditions below hold.

## Conditions

| Condition | State | Evidence |
| --- | --- | --- |
| The rule's cases pass | **met** for chain and ratio | 56 of 80 V parts pass, including every M1, M2a, ratio, D11b and D09/D10 part (`contracts/rules/registry.json`) |
| Legacy differences are explained | **met** | `shadow-review.md`: zero unclassified differences over eight cases; legacy capture of 132 runs unchanged |
| Monotonicity holds | **met** for a fixed subject | V24 (masking keeps every obligation, coverage never rises), V67 (byte-identical regeneration), V50 and V68 (new subject or suite version lists the scope delta) |
| Reader and gate matrices are complete | **not met** | `refusal-matrix.md`: two old readers do not refuse a new format (`dependencies.py` accepts a check context; `recipe_semantics.py --upstream` reads capability-gated keys). The custodian gate has not adopted the requirement (O17) |
| Supported positive cases pass without exceptions | **met** | the reduced chain case and the ratio case are complete and consistent with no exception |
| A review record exists (a non-author reviewer preferred) | **not met** | only author self-review and one automated code review; O04 (reviewers) and O14 (reviewer roles) are open |

## Recommendation (Inferred)

**Keep every rule in shadow mode.** Enable nothing for any purpose yet. To reach G-ENFORCE for the chain and ratio
suites:

1. Make the two non-refusing readers refuse new formats explicitly (or review and document their behaviour), and
   re-measure the matrix.
2. Name the reviewers (O04) and the roles that may accept reports (O14), and have a non-author review the rules,
   the coverage contract (its stages and member lists are proposals, O09) and the custodian requirement.
3. Have the custodian adopt `custodian-gate-requirement.md` (O17) and decide whether pre-execution reports are
   acceptable for any purpose.

The open slices are unchanged: the model part of M2b (O03) and M2c run lineage (no concrete need yet).

Two M3 cases are not run, for stated reasons (**Confirmed**):
- **V32** (a non-lock alias used at run time) is post-execution: it needs a result binding (M2c). With the chain and
  ratio suites only, it does not apply.
- **V30** (local profiles with missing ownership metadata) needs `custody_domain` metadata, which no reader in the
  checkout has (`grep custody_domain` finds nothing). The companion stays at transition stage 1 (O11).

## Owner

Programme owner: **Requires Confirmation**. Implementer: Claude Code session, 2026-10-16 (self-reviewed, which C15
limits to public and synthetic diagnostics).

## Decision

**Keep every rule in shadow mode**, 2026-10-16: the maintainer's instruction in the session was to follow the
recommendation. The implementer works on step 1 (non-refusing readers). Steps 2 and 3 (reviewers, custodian adoption)
are the maintainer's and custodian's.

**Step 1 outcome (2026-10-16):**
- `recipe_semantics.py` now refuses unknown upstream capabilities.
- `dependencies.py`'s acceptance of a file without inputs is documented, intended behaviour. That row stays a blocker
  until a non-author reviewer accepts the rationale (`refusal-matrix.md`).

The reader-matrix condition therefore waits on step 2, like the review condition.
