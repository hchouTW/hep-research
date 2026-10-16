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

## Maintainer answers to the open questions (2026-10-16)

The maintainer answered three questions in the session and asked the implementer to decide the rest by its
recommendation. Those are recorded as such (**Inferred**); the maintainer may replace any of them with a new dated
section.

| Item | Answer | By |
| --- | --- | --- |
| Programme owner | **hchouTW (the maintainer)**. This fills the owner line of every earlier record. | maintainer |
| Reviewers (O04) and roles (O14) | **Self-reviewed** for now. No non-author reviewer is named, so C15 limits the work to public and synthetic diagnostics. No role may yet accept a check report as evidence. | maintainer |
| Branches | **Stacked PRs, one per phase**: M0, M1, M2a, M2b-ratio with D11b, M3 with G-ENFORCE step 1. Merged in that order, each after its own CI. | maintainer |
| Custodian (O17) | The requirement stays a proposal. The custodian's gate does not adopt it yet. **No purpose accepts a pre-execution report** (the default). Revisit when a non-author reviewer exists. | recommendation |
| `dependencies.py` | **Keep the documented behaviour** ("consistent but not allowed"), with no change to its output or tests. The refusal-matrix row stays marked as non-refusing; that is a fact about the reader, not a defect. | recommendation |
| Model part (O03) | **Deferred.** It is not built until an analysis uses a model card with this checker; then the implementer proposes the supported pairings from the pyhf-combine adapter for the owner to approve. | recommendation |
| M2c run lineage | **Stays paused.** No analysis cites a campaign result through the batch adapter. | recommendation |
| Companion namespace check | **Pre-release step.** The maintainer runs `contracts/registry.py --local "<companion root>/profile"` before the next hep-research release. A `profile.namespace_collision` blocks that release. | recommendation |
| `crflux:local-interstellar` | **Retire it in the companion** at its next release, since nothing uses it. This is the companion's change, made in its own repository. | recommendation |
| Contracts version | **Bump 2.9.0 → 2.10.0 at the next release**, because the release adds schemas and a capability. No bump on these branches. | recommendation |

**Effect on G-ENFORCE (Confirmed against the conditions table):**
- A review record now exists, though it is a self-review, not the preferred non-author one.
- The reader and gate matrix condition is still **not met**, because the custodian has not adopted the requirement.

**Every rule therefore stays in shadow mode.** The programme is complete for this round. What remains is either
deferred (O03, M2c, V30, V32) or depends on a non-author reviewer or the custodian.

## Follow-up (2026-10-16)

- **Correction to the table above:** `crflux:local-interstellar` is declared by `experiment:ams-02`, which is part of
  this plugin, not of the companion. It is retired here (`crflux-review.md`, Decision), and the companion needs no
  change.
- **Companion namespace check:** run against main `c1ab70b`. It reported `ok` with no findings, so there is no
  `profile.namespace_collision`. Rerun it before the release if either repository changes its namespaces.
- **Contracts 2.10.0:** bumped on branch `contracts-2.10.0`, ahead of the release.

## Decision change (2026-10-16): synthetic completion of the remaining slices

This section replaces "deferred" for the model part and "paused" for M2c. The G-M2a condition is "model or run has a
concrete need". It was read as needing a real analysis, but the brief's own hosts for both slices are synthetic:
CASE-MODEL is built from public synthetic files, and the M2c campaign cases are fake-scheduler and local runs.

**Reasons (Inferred):**
1. Without M2c no post-execution report exists, and no purpose accepts a pre-execution one. The D10 report check can
   therefore never accept a report, so an enforcement decision now would judge a gate that cannot pass anything.
2. A non-author reviewer should review the whole set of suites once, rather than slice by slice.

**Decided by the owner (hchouTW):** the implementer's recommendation, steps 1–3.

| Step | Content | Gate |
| --- | --- | --- |
| 1 | The model part of M2b: the `model-card/v1` suite, implementing exactly the O03 pairings; CASE-MODEL; the three O03 gap tests | usual per-WP gate |
| 2 | V30 (D12b): `custody_domain` inventory of local profiles, stage 1 only (missing means unverified, never public; existing refusals unchanged) | usual per-WP gate |
| 3 | A proposal record for M2c: the `allowed_outputs` matching rule, and O15 | stop for the owner's decision |

Everything stays in shadow mode and synthetic only. There is no schema change to `attestation.json` or
`permit.json`, and no change to `core/partition/`.
