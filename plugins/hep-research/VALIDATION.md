# VALIDATION — hep-research (partial, through M1)

Environment for all entries below: Claude Code cloud container (Linux 6.18 x86_64), Python 3.11.15, `.venv-hep` with numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0; Claude Code CLI 2.1.287. Date 2026-10-02.
Aggregate command: `python3 tools/run_all_checks.py --out <dir>`; latest run `tasks/hep-research/check-runs/check-run-2026-10-02T134449Z.json`: 6 pass / 0 fail / 0 skip, 47 unit tests pass.
Software checks establish contract consistency only: not physical validity, proof, statistical coverage, or authorization to unblind.

| AC | Result so far | Evidence | Remaining |
|---|---|---|---|
| AC01 | partial | Inventory covers 100% of 942 files in the seven skills; draft migration map; legacy skills untouched (`git diff 3e995a4 -- <seven skill folders>` empty) | Record-level traceability in M2, M6 |
| AC02 | partial | Seven SKILL.md with uses, exclusions, owned artifacts, handoffs; host validator `--strict` passes; no profile adds a skill | Discovery at G5 |
| AC03 | pass (M1 scope) | `check_layering.py` 0 violations | Re-check after M2 migration |
| AC04 | partial | ~2,005 always-on tokens (host estimate), SKILL.md 4.4–6.0 KiB | Real traces M5 |
| AC06 | pass | Registry negatives: duplicate ID, incompatible version, missing resource, template violation, escaping path (incl. symlink), cycle, missing dependency, unbacked capability, bad namespace, registry mismatch (`RegistryTests`) | — |
| AC07 | partial | 0/1/many × 0/1/many configs, local profile, conflict diagnostics, overrides need provenance (`ProjectConfigTests`) | Composition in M4 |
| AC13 | partial | 16 valid / 18 invalid artifact fixtures (`ArtifactFixtureTests`) | Legacy AMS converter M2 |
| AC29 | partial | Layering directions, no-hard-coded-profile rule, steward check enforced; T23 15 tests | Re-run M5 |
| AC30 | partial | J1–J12 traced (`docs/researcher-journeys.md`) | Executions M2–M5 |
| AC31 | partial | Vocabularies extensible by namespaced profile terms; non-collider normalization validates (T26); conventions gate T25 | Published-data comparison run M4 |
| others | not started | — | per task Section 10 |
