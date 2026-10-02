# Decisions Log — hep-research plugin

Evidence labels per task Section 2.2.

| ID | Date | Decision | Status | Rationale |
|---|---|---|---|---|
| D1 | 2026-10-02 | Primary host: Claude Code plugin system | Default `[Proposal]`, confirm at G0 | Task Section 5 |
| D2 | 2026-10-02 | Non-AMS example: illustrative `synthetic-collider` | Default `[Proposal]`, confirm at G0 | Task Section 5 |
| D3 | 2026-10-02 | Theory benchmark: `qed-benchmark` (tree-level e+e- -> mu+mu-) | Default `[Proposal]`, confirm at G0 | Task Section 5 |
| D4 | 2026-10-02 | Plugin at `plugins/hep-research/`; dev marketplace at repo root | Default `[Proposal]`, confirm at G0 | Task Section 5 |
| D5 | 2026-10-02 | Python >= 3.10 + numpy, scipy, matplotlib, sympy | Default `[Proposal]`, confirm at G0; install blocked on network approval | Task Section 5 |
| D6–D10 | — | As in task Section 5 | Fixed / M1 | — |
| M0-01 | 2026-10-02 | Dev tooling that is not part of the plugin (`build_inventory.py`) lives in `tasks/hep-research/scripts/` | Decided | Keeps the distributable root clean (D8) |
| M0-02 | 2026-10-02 | Migration map is file-level and rule-derived in M0 (`section_or_symbol` = whole file); section/symbol splits are refined in M1/M2 | Decided | Step 6 asks for "the first" map; per-section ownership is M1 work |
| M0-03 | 2026-10-02 | `ams-analysis/tests/grading/` (390 files) and `hep-analysis/evals/` (81 files) are `retain-outside` | Decided | Grading rubrics/model transcripts never enter the plugin (2.1) |
| M0-04 | 2026-10-02 | `docs/detector-principles/` (5 files, not in the 4.1 map) mapped to `detector-response` as `merge` candidates | Decided, refine in M1 | Overlaps `hep-analysis/references/49-50` |
| M0-05 | 2026-10-02 | `lint_task.py` fails on this task file only on section structure (numbered headings vs. template headings). Adapted, not force-fit: the task file is not restructured | Decided | Step 9 says adapt rather than force-fit |
| M0-06 | 2026-10-02 | Root `.gitignore` ignores `docs/*`; plugin docs live under `plugins/hep-research/docs/`, which is unaffected | Recorded | — |
