# Geant4 architecture: working base

This folder is the starting point for implementing the Geant4 architecture proposal. It lives on the branch
`worktree-geant4-architecture`, rebased on `main` at `9f08796` (0.23.0 plus unreleased changes, contracts 3.5.0).

| File | Content |
|---|---|
| `proposal.md` | The final proposal, Traditional Chinese original: three phases, every review finding and its resolution; section 13 is the second deep check against `9f08796` |
| `proposal.en.md` | English translation of `proposal.md`, same sections, tables and numbers. Edit both together; if they disagree, the Chinese original wins until the English is corrected |
| `j15_design_estimates.py` | Design estimates for the J15 minimal spectrometer (geometry, acceptance, resolution, statistics). Standard library; scipy optional. Not a benchmark reference |
| `prototype/phase1-core.patch` | A reference prototype of phase 1 items 4.1, 4.2, 4.3 and 4.6 (contracts table, scope by observable kind, configuration emission, enum fix) with tests. Applies to `9f08796` with `git apply`. It follows the proposal text **before** the second deep check, so it lacks `target_slabs`, the `longitudinal-profile` target-hash match, the missing-dimension rule, `shower-maximum`, the `dependencies.py` re-derivation and C1 gating of the isolation rule; it gates at 3.6.0. Not reviewed for merge |

## Language split (user decision, 2026-10-22)

The compute core is C++; Python is only the interface and judgement layer. They exchange JSON/CSV through separate
executables (no Python bindings).

- C++: `layered_sim` (links Geant4) and the new Geant4-free `simcore` under `adapters/geant4/assets/simcore/`
  (`simspec` spec conversion, `simstat` observables and statistics, `simreco` digitization and reconstruction), C++17
  standard library plus the existing `MiniJson.hh`.
- Detailed per-event simulation information goes to ROOT files (user decision, 2026-10-22; proposal 5.9), written
  by `layered_sim` through `G4AnalysisManager` (the g4tools code shipped with Geant4; no ROOT installation). Flat
  ntuples keyed by `event_id`; the per-event CSV stays as the summary table. Python and `simcore` never read ROOT:
  the new Geant4-linked `simroot` converts to CSV (`dump`) or gives a content hash (`hash`). ROOT files are not
  committed; run records keep the file sha256 and the `content_sha256`.
- Python: the adapter CLIs that build and run the executables and write records; hep-detector's rules, independent
  reference formulas, gate and benchmark decisions and labels; the contracts.
- One production implementation per quantity; the other language only in tests, as an oracle (proposal principle 11).

## Before starting any work

1. Check that `main` has not moved past `9f08796`. If it has, read the new CHANGELOG entries and re-run the checks
   in `proposal.md` section 13 (defect locations D1–D10, `CONTRACTS_VERSION`, `GRADES`, advisory numbers,
   quick-load bytes, description length, journey list) before changing code. Update section 13 (both languages).
2. Contract versions are written C1 (the next unused minor at merge time) and C2 (the one after). Fix the numbers
   only when the change is merged.
3. Work only on this branch, inside the worktree. Do not push to `main` or open a pull request without the
   maintainer's approval.
4. Follow `docs/maintenance.md`: the sci-fix process for phase 1 (one ledger entry per defect with a structured
   `changelog`; S2 for D1–D4, S1 for D5, S3 for D6; `sci-fix:` commits; parent records; one advisory per severity
   that passes `tools/scifix_advisories.py check`), the adapter-change steps for phases 2 and 3, and the release
   steps (VALIDATION entry, CHANGELOG, release manifest).

## Order of work

**Phase 1 (contracts C1, sci-fix) comes first.** It fixes the existing `validated-in-scope` defects and does not
depend on the new architecture. Start from `prototype/phase1-core.patch` and bring it to the current text:

1. `contracts/validate.py`: the benchmark table (name to grade and supported kinds; `longitudinal-profile` →
   `shower-maximum`); `_study_upgrade` reads grades from it; `_scope_inside` compares `observable.kind`, treats a
   missing declared dimension as outside, and for `longitudinal-profile` also requires a matching
   `target_geometry_sha256`; the isolation rule; gate `strict or _at_least(version, C1)`.
   `check_geant4_study.py` imports the function and drops `scope_within()`; `label` writes
   `declared_scope.observable_kind`.
2. `geant4_benchmarks.py`: `configuration`, `target_geometry_sha256`, `configuration_basis` from the named
   `run_record` and the declared `target_slabs`; `contracts/dependencies.py` re-derives and compares them.
3. Negative controls by the shift in the observable; J14's claims restricted to one sign until the live re-record.
4. `check_geant4_study.py`: the intersection-union gate, `incomplete` (exit 3) for unresolved, the two-stage factor
   F_0.90(15,15) = 1.97, seeds `H(study_id, role, point_id, k)` in [1, 2^31) with hand-built manifests, sub-run
   MPVs from chunk CSVs, `evidence_overlap`, `trace.tag()` on the new shared functions.
5. Schemas: `shower-containment`, `longitudinal-profile`, `shower-maximum`, `validation_plan.scope.observable_kind`;
   `simulation` as an optional property of `ext_computational_run.json` (needs hep-computing's agreement).
6. D10: separate the J14 replay fixtures of `test_geant4_upgrade` and `test_simulated_dataset`; check with
   `python3 -m unittest discover -s tests/contracts -t .`.
7. Protocol section 4 (stopping rule declared in advance); regenerate J14 by offline replay for 4.1–4.3, then a live
   re-record on E2 (Geant4 11.4.3 build) for 4.4 and 4.5; ledger, advisories, VALIDATION entry GEANT4-CORRECTNESS.

Phase 1 stays in Python on purpose (a minimal sci-fix). Phase 2 then ports the statistics to `simstat` (proposal
5.8), keeping phase 1's Python estimators in `tests/` as oracles, and adds a required CI job that builds `simcore`.
Phase 2 also adds the per-event ROOT files and `simroot` (proposal 5.9). Phase 3 adds `simreco` (proposal 6.5); hep-detector gets no new script.

Phases 2 and 3 follow sections 5 and 6 of the proposal.

## Open decisions for the maintainer

- Phase 1 as a minor (C1, proposed).
- Whether a statistical comparison is acceptable if bit-identical output cannot be reached on the same host (phase 2).
- How to confirm the G5 statement that no Geant4 example code was copied.
- hep-computing's agreement to the optional `simulation` property and the C2 "derived simulation" marker.
- A new required CI job for `simcore` (needs a C++17 compiler).
- Where ROOT files are stored and for how long (not in the repository).

## Independent review

The text added on 2026-10-22 has not been independently reviewed. The plugin's `review.py`
(`skills/hep-authoring/references/independent-review.md`) can review `proposal.en.md` on the maintainer's machine:
it needs fork subagents switched off and a host restart, and the document must exist nowhere else on the host. Its
record is advisory, not a human review record (O04/O14).
