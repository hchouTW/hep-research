# Geant4 architecture: working base

This folder is the starting point for implementing the Geant4 architecture proposal. It lives on the branch
`worktree-geant4-architecture`, created as an isolated git worktree from `main` at `c4f7954`
(tag `hep-research--v0.21.0`, contracts 3.2.0).

| File | Content |
|---|---|
| `proposal.md` | The final proposal, Traditional Chinese original: three phases, every review finding and its resolution, re-checked against 0.21.0 in section 12 |
| `proposal.en.md` | English translation of `proposal.md`, same sections, tables and numbers. Edit both together; if they disagree, the Chinese original wins until the English is corrected |
| `j15_design_estimates.py` | Design estimates for the J15 minimal spectrometer (geometry, acceptance, resolution, statistics). Standard library; scipy optional. Not a benchmark reference |

## Before starting any work

1. Check that `main` has not moved past `c4f7954`. If it has, read the new CHANGELOG entries and re-run the checks
   in `proposal.md` section 12 (defect locations D1-D8, contract version, `GRADES`, quick-load bytes, journey list)
   before changing code. Update section 12 when anything differs.
2. Work only on this branch, inside the worktree. Do not push or open a pull request without the maintainer's approval.
3. Follow `docs/maintenance.md`: the sci-fix process for phase 1 (S2, `sci-fix:` commits, parent record, C2 oracle
   evidence, `docs/evidence/sci-fixes.json`, advisory), the adapter-change steps for phases 2 and 3, and the release
   steps (VALIDATION entry, CHANGELOG, release manifest).

## Order of work

**Phase 1 (contracts 3.3.0, sci-fix) comes first.** It fixes the existing `validated-in-scope` defects and does not
depend on the new architecture.

1. `contracts/validate.py`: a benchmark table (name to grade and supported observable kinds, including
   `longitudinal-profile`); `_study_upgrade` reads grades from it; `_scope_inside` compares `observable.kind`; gate
   `strict or _at_least(version, "3.3.0")`. Remove `scope_within()` from `check_geant4_study.py` and import the
   contracts function.
2. `geant4_benchmarks.py`: emit `kind`, `configuration` (derived from the run geometry and the benchmark target) and
   `target_geometry_sha256`; negative control judged by the realized shift in the observable, both signs; MPV as the
   mean of 16 partition sub-runs with t quantiles.
3. `check_geant4_study.py`: the intersection-union convergence gate (section 4.5), the two-stage factor
   F_0.90(15,15) = 1.97, seeds `H(study_id, role, point_id, k)`, `evidence_overlap`.
4. Study-spec schema: add `shower-containment` and `longitudinal-profile` to the benchmark enum.
5. Protocol section 4: stopping rule, scan grid and handling of unresolved results declared before the first
   evidence run.
6. Re-record J14 on E2 (needs a Geant4 11.4.3 build); sci-fix ledger, advisory SFA-2026-036 (or the next free
   number), VALIDATION entry GEANT4-CORRECTNESS.

Phases 2 and 3 follow `proposal.md` sections 5 and 6.

## Open decisions for the maintainer

- Phase 1 as a minor (3.3.0, proposed) or a patch (3.2.1, would be the first patch-level gate).
- Whether a statistical comparison is acceptable if bit-identical output cannot be reached on the same host (phase 2).
- How to confirm the G5 statement that no Geant4 example code was copied.
